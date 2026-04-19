# -*- coding: utf-8 -*-
import os
import json
import requests
import re
import base64
import time
import hashlib
import bcrypt
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, errors
from bson.objectid import ObjectId
from datetime import datetime

# --- 配置 ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyDrZEGpHGOuTi3Cc_0GPuuinpnK-ekAuxo')
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
EMBEDDING_MODEL = "text-embedding-004"
GENERATIVE_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = f"{GEMINI_API_BASE_URL}{GENERATIVE_MODEL}:generateContent"

# --- MongoDB 配置 ---
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = "buddy_matcher"
db_client = None

app = Flask(__name__)
CORS(app)

# --- 数据库初始化和连接 ---
def get_db_client():
    global db_client
    if db_client is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # 尝试连接数据库
            client.admin.command('ping')
            db_client = client
            app.logger.info("--- 数据库状态：MongoDB 连接成功 ---")
        except errors.ConnectionFailure as e:
            app.logger.error(f"!!! 致命错误: 无法连接到 MongoDB: {e}")
            return None
        except Exception as e:
            app.logger.error(f"!!! 致命错误: 数据库初始化失败: {e}")
            return None
    return db_client


def get_db():
    client = get_db_client()
    return client[DB_NAME] if client else None


# --- MongoDB 辅助函数 (CRUD) ---

def save_user_auth(user_id, email, password_hash):
    db = get_db()
    if db is None: return False
    try:
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'email': email, 'password': password_hash, 'created_at': datetime.now()}},
            upsert=True
        )
        app.logger.info(f"DEBUG: save_user_auth successful.")
        return result.acknowledged and (
                result.upserted_id is not None or result.modified_count > 0 or result.matched_count > 0)
    except Exception as e:
        app.logger.error(f"Error saving user auth: {e}")
        return False


def get_user_auth(email):
    db = get_db()
    if db is None: return None
    return db.users.find_one({'email': email})


def save_user_profile(profile_data):
    db = get_db()
    if db is None: return False

    if '_id' in profile_data:
        del profile_data['_id']

    try:
        # 1. 拼接 Embedding 文本
        personality = profile_data.get('personality', '')
        location = f"{profile_data.get('location', {}).get('city', '')}-{profile_data.get('location', {}).get('district', '')}"
        hobbies = ', '.join(profile_data.get('ai_tags', []))
        text_to_embed = f"Personality: {personality}. Location: {location}. Hobbies: {hobbies}"

        embedding_vector = None
        if len(text_to_embed) > 50:
            try:
                app.logger.info(f"DEBUG: Generating new embedding for user {profile_data['user_id']}")
                embedding_vector = call_gemini_embedding_api(text_to_embed)
                profile_data['embedding_vector'] = embedding_vector
            except ConnectionError as e:
                app.logger.error(f"Error: Embedding API connection failed during profile save. Details: {e}")
            except Exception as e:
                app.logger.error(f"Error: Unknown error generating embedding during profile save. Details: {e}")
                pass

        # 2. 执行资料保存/更新
        result = db.profiles.update_one(
            {'user_id': ObjectId(profile_data['user_id'])},
            {'$set': profile_data},
            upsert=True
        )

        app.logger.info(f"DEBUG: save_user_profile successful. Vector generated? {'Y' if embedding_vector else 'N'}")
        return result.acknowledged and (
                result.upserted_id is not None or result.modified_count > 0 or result.matched_count > 0)
    except Exception as e:
        app.logger.error(f"Error saving user profile: {e}")
        return False


def get_user_profile(user_id):
    db = get_db()
    if db is None: return None
    profile = db.profiles.find_one({'user_id': ObjectId(user_id)})
    if profile:
        profile['_id'] = str(profile['_id'])
        profile['user_id'] = str(profile['user_id'])
        if 'embedding_vector' in profile:
            del profile['embedding_vector']
    return profile


def get_all_profiles(current_user_id):
    db = get_db()
    if db is None: return []
    try:
        if current_user_id:
            profiles_cursor = db.profiles.find({'user_id': {'$ne': ObjectId(current_user_id)}})
        else:
            profiles_cursor = db.profiles.find()
        profiles_list = []
        for profile in profiles_cursor:
            if 'embedding_vector' in profile:
                del profile['embedding_vector']
            profile['_id'] = str(profile['_id'])
            profile['user_id'] = str(profile['user_id'])
            profiles_list.append(profile)
        return profiles_list
    except Exception as e:
        app.logger.error(f"Error getting all profiles: {e}")
        return []

# --- 短期找搭子诉求管理函数 ---
def save_buddy_request(request_data):
    db = get_db()
    if db is None: return False

    if '_id' in request_data:
        del request_data['_id']

    try:
        # 执行诉求保存/更新
        result = db.buddy_requests.update_one(
            {'user_id': ObjectId(request_data['user_id']), 'request_id': request_data.get('request_id')},
            {'$set': request_data},
            upsert=True
        )

        app.logger.info(f"DEBUG: save_buddy_request successful.")
        return result.acknowledged and (
                result.upserted_id is not None or result.modified_count > 0 or result.matched_count > 0)
    except Exception as e:
        app.logger.error(f"Error saving buddy request: {e}")
        return False


def get_buddy_requests(user_id):
    db = get_db()
    if db is None: return []
    requests_cursor = db.buddy_requests.find({'user_id': ObjectId(user_id)})
    requests_list = []
    for request in requests_cursor:
        request['_id'] = str(request['_id'])
        request['user_id'] = str(request['user_id'])
        requests_list.append(request)
    return requests_list


def get_all_buddy_requests():
    db = get_db()
    if db is None: return []
    requests_cursor = db.buddy_requests.find({})
    requests_list = []
    for request in requests_cursor:
        request['_id'] = str(request['_id'])
        request['user_id'] = str(request['user_id'])
        requests_list.append(request)
    return requests_list


# --- 辅助函数 (LLM/Jieba/Base64/Embedding) ---
def calculate_simple_similarity(text_a, text_b):
    # 简单的文本相似度计算，基于共同词的比例
    def get_words(text):
        # 移除特殊字符，分割成单词
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
        words = text.lower().split()
        # 过滤空字符串
        return set([w for w in words if w])

    set_a = get_words(text_a)
    set_b = get_words(text_b)
    if not set_a or not set_b: return 0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    jaccard_similarity = intersection / union
    return round(jaccard_similarity * 100)


def calculate_cosine_similarity(vec_a, vec_b):
    """在 Python 中计算两个向量的余弦相似度"""

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def call_gemini_api(payload):
    """
    调用 Gemini API (生成式模型) 发送请求。
    """
    if GEMINI_API_KEY == "geminikey":  # 检查占位符
        app.logger.error("!!! 致命错误: Gemini API Key 未配置或仍是占位符 !!!")
        raise ConnectionError("Gemini API Key 未配置。")

    headers = {'Content-Type': 'application/json'}
    params = {'key': GEMINI_API_KEY}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Gemini API Request failed: {e}")
        raise ConnectionError(f"API 调用失败: {e}")


def call_gemini_embedding_api(text_to_embed):
    """调用 Gemini Embedding API 获取文本的向量表示"""

    if GEMINI_API_KEY == "geminikey":  # 检查占位符
        app.logger.error("!!! 致命错误: Gemini API Key 未配置或仍是占位符 !!!")
        raise ConnectionError("Gemini API Key 未配置。")

    url = f"{GEMINI_API_BASE_URL}{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"

    payload = {"content": {"parts": [{"text": text_to_embed}]}}

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 400:
            app.logger.error(f"Embedding API 400 错误详情 (Input: '{text_to_embed[:50]}...'): {response.text}")

        response.raise_for_status()

        result = response.json()
        embedding = result['embedding']['values']
        return embedding

    except requests.RequestException as e:
        app.logger.error(f"Embedding API 调用失败: {e}")
        raise ConnectionError(f"Embedding API 调用失败: {e}")


def format_profile(user):
    # 格式化用户资料用于LLM分析
    gender = user.get('gender', '未填写')
    mbti = user.get('mbti', '未填写')
    occupation = user.get('occupation', '未填写')
    personality = user.get('personality', '未填写')
    location = f"{user.get('location', {}).get('city', '')}-{user.get('location', {}).get('district', '')}"
    ai_tags = ', '.join(user.get('ai_tags', []))
    reputation = user.get('reputation', 5.0)
    
    return f"性别: {gender}, MBTI: {mbti}, 职业: {occupation}, 性格: {personality}, 地点: {location}, 标签: {ai_tags}, 信誉分: {reputation}"

def format_buddy_request(request):
    # 格式化短期找搭子诉求用于LLM分析
    title = request.get('title', '未填写')
    content = request.get('content', '未填写')
    category = request.get('category', '未填写')
    location = f"{request.get('location', {}).get('city', '')}-{request.get('location', {}).get('district', '')}"
    requirements = request.get('requirements', {})
    
    requirements_str = ', '.join([f"{k}: {v}" for k, v in requirements.items()])
    if not requirements_str:
        requirements_str = '无特殊要求'
    
    return f"标题: {title}, 内容: {content}, 分类: {category}, 地点: {location}, 要求: {requirements_str}"


# --- 辅助函数 ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed):
    return hashlib.sha256(password.encode()).hexdigest() == hashed

# API endpoints
@app.route('/')
def index():
    return jsonify({'message': 'Buddy Matcher API'})



# Get user profile
@app.route('/api/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        profile = get_user_profile(user_id)
        if not profile:
            return jsonify({'error': 'Profile not found'}), 404
        
        return jsonify(profile), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all profiles
@app.route('/api/profile/all', methods=['GET'])
def get_all_profiles_api():
    try:
        # Get current user ID from request (if available)
        current_user_id = request.args.get('current_user_id', '')
        profiles = get_all_profiles(current_user_id)
        return jsonify(profiles), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update user profile
@app.route('/api/profile/<user_id>', methods=['PUT'])
def update_profile(user_id):
    try:
        data = request.json
        profile = get_user_profile(user_id)
        if not profile:
            return jsonify({'error': 'Profile not found'}), 404
        
        update_data = {
            'gender': data.get('gender', profile.get('gender', '')),
            'age': data.get('age', profile.get('age', 0)),
            'mbti': data.get('mbti', profile.get('mbti', '')),
            'occupation': data.get('occupation', profile.get('occupation', '')),
            'hobbies': data.get('hobbies', profile.get('hobbies', [])),
            'personality': data.get('personality', profile.get('personality', '')),
            'location': data.get('location', profile.get('location', {'city': '', 'district': ''})),
            'privacy_settings': data.get('privacy_settings', profile.get('privacy_settings', {'age_visible': True, 'occupation_visible': True})),
            'ai_tags': data.get('ai_tags', profile.get('ai_tags', [])),
            'updated_at': datetime.now()
        }
        
        # Add user_id to update_data
        update_data['user_id'] = ObjectId(user_id)
        
        if save_user_profile(update_data):
            return jsonify({'message': 'Profile updated successfully'}), 200
        else:
            return jsonify({'error': 'Profile update failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Create activity
@app.route('/api/activities', methods=['POST'])
def create_activity():
    data = request.json
    user_id = data.get('user_id')
    title = data.get('title')
    content = data.get('content')
    category = data.get('category')
    time = data.get('time')
    location = data.get('location')
    budget = data.get('budget', 0)  # 预算
    people_range = data.get('people_range', {})  # 人数范围
    requirements = data.get('requirements', '')  # 希望对方能：的备注信息
    need_confirmation = data.get('need_confirmation', False)  # 是否需要发起者通过确认才能参与
    deposit = data.get('deposit', 0)  # 活动押金（虚拟币）
    tags = data.get('tags', [])  # 活动标签
    
    if not user_id or not title or not content:
        return jsonify({'error': 'User ID, title, and content are required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        activity_id = db.activities.insert_one({
            'user_id': ObjectId(user_id),
            'title': title,
            'content': content,
            'category': category,
            'time': datetime.fromisoformat(time) if time else datetime.now(),
            'location': location,
            'budget': budget,  # 预算
            'people_range': people_range,  # 人数范围
            'requirements': requirements,  # 希望对方能：的备注信息
            'need_confirmation': need_confirmation,  # 是否需要发起者通过确认才能参与
            'deposit': deposit,  # 活动押金（虚拟币）
            'tags': tags,  # 活动标签
            'status': 'ongoing',
            'participants': [ObjectId(user_id)],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }).inserted_id
        
        return jsonify({'message': 'Activity created successfully', 'activity_id': str(activity_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get activities
@app.route('/api/activities', methods=['GET'])
def get_activities():
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        user_id = request.args.get('user_id')
        query = {'status': 'ongoing'}
        if user_id:
            query = {'user_id': ObjectId(user_id)}
        
        activities = db.activities.find(query)
        result = []
        for activity in activities:
            activity['_id'] = str(activity['_id'])
            activity['user_id'] = str(activity['user_id'])
            activity['participants'] = [str(p) for p in activity['participants']]
            if 'requirements' not in activity:
                activity['requirements'] = ''
            if 'tags' not in activity:
                activity['tags'] = []
            if 'budget' not in activity:
                activity['budget'] = 0
            if 'people_range' not in activity:
                activity['people_range'] = {}
            if 'need_confirmation' not in activity:
                activity['need_confirmation'] = False
            if 'deposit' not in activity:
                activity['deposit'] = 0
            result.append(activity)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get activity by ID
@app.route('/api/activities/<activity_id>', methods=['GET'])
def get_activity(activity_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        activity = db.activities.find_one({'_id': ObjectId(activity_id)})
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404
        
        activity['_id'] = str(activity['_id'])
        activity['user_id'] = str(activity['user_id'])
        activity['participants'] = [str(p) for p in activity['participants']]
        # 确保返回所有必要字段
        if 'requirements' not in activity:
            activity['requirements'] = ''
        if 'tags' not in activity:
            activity['tags'] = []
        if 'budget' not in activity:
            activity['budget'] = 0
        if 'people_range' not in activity:
            activity['people_range'] = {}
        if 'need_confirmation' not in activity:
            activity['need_confirmation'] = False
        if 'deposit' not in activity:
            activity['deposit'] = 0
        return jsonify(activity), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Apply to join activity
@app.route('/api/activities/<activity_id>/apply', methods=['POST'])
def apply_activity(activity_id):
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Check if activity exists
        activity = db.activities.find_one({'_id': ObjectId(activity_id)})
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404
        
        # Check if user is already a participant
        if ObjectId(user_id) in activity.get('participants', []):
            return jsonify({'error': 'User is already a participant'}), 400
        
        # Check if application exists
        existing_application = db.activity_applications.find_one({
            'activity_id': ObjectId(activity_id),
            'user_id': ObjectId(user_id)
        })
        if existing_application:
            return jsonify({'error': 'Application already exists'}), 400
        
        # Create application
        application_id = db.activity_applications.insert_one({
            'activity_id': ObjectId(activity_id),
            'user_id': ObjectId(user_id),
            'status': 'pending',
            'created_at': datetime.now()
        }).inserted_id
        
        return jsonify({'message': 'Application submitted successfully', 'application_id': str(application_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get activity applications
@app.route('/api/activities/<activity_id>/applications', methods=['GET'])
def get_activity_applications(activity_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        applications = db.activity_applications.find({'activity_id': ObjectId(activity_id)})
        result = []
        for app in applications:
            app['_id'] = str(app['_id'])
            app['activity_id'] = str(app['activity_id'])
            app['user_id'] = str(app['user_id'])
            result.append(app)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update application status
@app.route('/api/applications/<application_id>', methods=['PUT'])
def update_application(application_id):
    data = request.json
    status = data.get('status')  # 'approved' or 'rejected'
    
    if not status or status not in ['approved', 'rejected']:
        return jsonify({'error': 'Valid status is required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get application
        application = db.activity_applications.find_one({'_id': ObjectId(application_id)})
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        # Update application status
        db.activity_applications.update_one(
            {'_id': ObjectId(application_id)},
            {'$set': {'status': status, 'updated_at': datetime.now()}}
        )
        
        # If approved, add user to activity participants
        if status == 'approved':
            db.activities.update_one(
                {'_id': application['activity_id']},
                {'$addToSet': {'participants': application['user_id']}}
            )
        
        return jsonify({'message': 'Application status updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Search activities
@app.route('/api/activities/search', methods=['POST'])
def search_activities():
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get all ongoing activities
        activities = db.activities.find({'status': 'ongoing'})
        activity_list = []
        for activity in activities:
            activity['_id'] = str(activity['_id'])
            activity['user_id'] = str(activity['user_id'])
            activity['participants'] = [str(p) for p in activity.get('participants', [])]
            if 'requirements' not in activity:
                activity['requirements'] = ''
            if 'tags' not in activity:
                activity['tags'] = []
            activity_list.append(activity)
        
        if not activity_list:
            return jsonify([]), 200
        
        # Build search keywords from query
        query_lower = query.lower()
        query_keywords = [k.strip() for k in query.split() if k.strip()]
        
        # Score each activity based on keyword matching
        scored_activities = []
        for activity in activity_list:
            score = 0
            matched_fields = []
            
            # Title matching
            title = activity.get('title', '').lower()
            if any(kw in title for kw in query_keywords):
                score += 30
                matched_fields.append('title')
            
            # Content matching
            content = activity.get('content', '').lower()
            for kw in query_keywords:
                if kw in content:
                    score += 20
                    if 'content' not in matched_fields:
                        matched_fields.append('content')
            
            # Tags matching
            tags = activity.get('tags', [])
            for kw in query_keywords:
                for tag in tags:
                    if kw.lower() in str(tag).lower():
                        score += 25
                        if 'tags' not in matched_fields:
                            matched_fields.append('tags')
                        break
            
            # Category matching
            category = activity.get('category', '').lower()
            if any(kw in category for kw in query_keywords):
                score += 15
                matched_fields.append('category')
            
            # Location matching
            location = activity.get('location', {})
            location_str = f"{location.get('city', '')} {location.get('district', '')}".lower()
            for kw in query_keywords:
                if kw in location_str:
                    score += 10
                    if 'location' not in matched_fields:
                        matched_fields.append('location')
                    break
            
            # Requirements matching
            requirements = activity.get('requirements', '').lower()
            if any(kw in requirements for kw in query_keywords):
                score += 10
                matched_fields.append('requirements')
            
            if score > 0:
                activity['search_score'] = score
                activity['matched_fields'] = matched_fields
                scored_activities.append(activity)
        
        # Sort by score
        scored_activities.sort(key=lambda x: x.get('search_score', 0), reverse=True)
        
        # Return top results
        return jsonify(scored_activities[:20]), 200
        
    except Exception as e:
        app.logger.error(f"Search error: {e}")
        return jsonify({'error': str(e)}), 500

# Recommend activities
@app.route('/api/activities/recommend', methods=['POST'])
def recommend_activities():
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get user profile
        user_profile = get_user_profile(user_id)
        if not user_profile:
            return jsonify({'error': 'User profile not found'}), 404
        
        # Get all ongoing activities
        activities = db.activities.find({'status': 'ongoing', 'user_id': {'$ne': ObjectId(user_id)}})
        activity_list = []
        for activity in activities:
            activity['_id'] = str(activity['_id'])
            activity['user_id'] = str(activity['user_id'])
            activity['participants'] = [str(p) for p in activity['participants']]
            if 'requirements' not in activity:
                activity['requirements'] = ''
            if 'tags' not in activity:
                activity['tags'] = []
            activity_list.append(activity)
        
        # Use AI to score and recommend activities
        recommended_activities = []
        for activity in activity_list:
            # Calculate activity score
            score_response = get_activity_score_internal(user_profile, activity)
            if score_response['score'] >= 70:  # Only recommend activities with score >= 70
                activity['match_score'] = score_response['score']
                activity['match_reason'] = score_response['reason']
                recommended_activities.append(activity)
        
        # Sort by match score
        recommended_activities.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return jsonify(recommended_activities), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_activity_score_internal(profile, activity):
    """Internal function to calculate activity score"""
    # Format profile and activity for LLM
    profile_str = format_profile(profile)
    activity_str = f"标题: {activity.get('title', '')}, 内容: {activity.get('content', '')}, 分类: {activity.get('category', '')}, 地点: {activity.get('location', {}).get('city', '')}-{activity.get('location', {}).get('district', '')}, 要求: {activity.get('requirements', '')}, 标签: {', '.join(activity.get('tags', []))}"
    
    # Prepare LLM prompt
    system_instruction = "你是一个专业的活动匹配AI。你的任务是评估用户与活动的匹配度，给出0-100分的评分，并提供详细理由。考虑因素包括：兴趣匹配度、地点便利性、时间合适度、用户与发起者的匹配度、活动标签匹配度等。"
    
    user_query = f"请评估以下用户与活动的匹配度，并给出评分和详细理由。\n\n### 用户资料\n{profile_str}\n\n### 活动信息\n{activity_str}\n\n请输出JSON格式，包含score和reason字段。"
    
    response_schema = {"type": "OBJECT",
                       "properties": {"score": {"type": "INTEGER"},
                                      "reason": {"type": "STRING"}},
                       "required": ["score", "reason"]}
    
    payload = {"contents": [{"parts": [{"text": user_query}]}],
               "systemInstruction": {"parts": [{"text": system_instruction}]},
               "generationConfig": {"responseMimeType": "application/json", "responseSchema": response_schema}}
    
    try:
        llm_response = call_gemini_api(payload)
        json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
        activity_data = json.loads(json_str)
        return activity_data
    except Exception as e:
        app.logger.error(f"LLM activity score processing failed: {e}")
        return {'score': 0, 'reason': '无法计算匹配度'}

# AI match score endpoint
@app.route('/api/match/score', methods=['POST'])
def get_match_score():
    data = request.json
    profile_a = data.get('profile_a')
    profile_b = data.get('profile_b')
    match_mode = data.get('match_mode', 'similarity')
    
    if not profile_a or not profile_b:
        return jsonify({'error': 'Both profiles are required'}), 400
    
    # Calculate objective overlap score
    summary_a = profile_a.get('personality', '')
    summary_b = profile_b.get('personality', '')
    objective_overlap_score = calculate_simple_similarity(summary_a, summary_b)
    
    # Format profiles for LLM
    profile_a_str = format_profile(profile_a)
    profile_b_str = format_profile(profile_b)
    
    # Prepare LLM prompt
    if match_mode == 'complementary':
        system_instruction = f"""你是一个顶级的、专注于**互补性**的伙伴匹配系统专家。你的核心任务是评估两个用户的资料，重点判断他们在**性格、技能、作息、生活态度**上的互补潜力。- **评估重心：** 互补性应占总评分的 70% 权重。重叠度分数 ({objective_overlap_score}%) 仅作为次要参考。- **评分标准：** 给出 0 到 100 分的匹配得分。- **重点分析：** 详细解释他们如何能够互相弥补不足、拓宽视野，并重点列出'互补潜力点'。"""
    else:
        system_instruction = f"""你是一个顶级的、专注于**相似性**的伙伴匹配系统专家。你的核心任务是评估两个用户的资料，重点判断他们在**意图、兴趣、习惯、价值观**上的重叠程度。- **评估重心：** 相似性应占总评分的 70% 权重。客观重叠度分数 ({objective_overlap_score}%) 是重要参考。- **评分标准：** 给出 0 到 100 分的匹配得分。- **重点分析：** 详细解释他们有哪些共同之处、共同话题，并重点列出'重叠契合点'。"""
    
    user_query = f"""请评估以下两位用户的匹配度，并给出评分和详细理由。本次匹配的客观关键词重叠度是：{objective_overlap_score}%。\n\n### 用户 A 资料 (发起匹配者)\n{profile_a_str}\n\n### 用户 B 资料 (待匹配用户)\n{profile_b_str}\n\n请严格根据你的系统指令，输出最终的 JSON 结果。"""
    
    response_schema = {"type": "OBJECT",
                       "properties": {"matchScore": {"type": "INTEGER"}, "matchLevel": {"type": "STRING"},
                                      "detailedRationale": {"type": "OBJECT", "properties": {
                                          "overlapPoints": {"type": "ARRAY", "items": {"type": "STRING"}},
                                          "complementaryPoints": {"type": "ARRAY", "items": {"type": "STRING"}},
                                          "mismatchPoints": {"type": "ARRAY", "items": {"type": "STRING"}},
                                          "summary": {"type": "STRING"}},
                                                            "required": ["overlapPoints", "complementaryPoints",
                                                                         "mismatchPoints", "summary"]}},
                       "required": ["matchScore", "matchLevel", "detailedRationale"]}
    
    payload = {"contents": [{"parts": [{"text": user_query}]}],
               "systemInstruction": {"parts": [{"text": system_instruction}]},
               "generationConfig": {"responseMimeType": "application/json", "responseSchema": response_schema}}
    
    try:
        llm_response = call_gemini_api(payload)
        json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
        app.logger.info(f"LLM raw response: {json_str[:500]}")
        match_data = json.loads(json_str)
        app.logger.info(f"Parsed match data: {match_data}")
        return jsonify({**match_data, "objectiveOverlapScore": objective_overlap_score, "matchMode": match_mode}), 200
    except Exception as e:
        app.logger.error(f"LLM match processing failed: {e}")
        return jsonify({'error': f'LLM match processing failed: {e}'}), 500

# AI activity score endpoint (使用本地规则计算，不调用大模型)
@app.route('/api/activity/score', methods=['POST'])
def get_activity_score():
    data = request.json
    profile = data.get('profile')
    activity = data.get('activity')
    
    if not profile or not activity:
        return jsonify({'error': 'Both profile and activity are required'}), 400
    
    score = 50
    reasons = []
    
    profile_tags = [t.lower() for t in profile.get('ai_tags', [])]
    activity_tags = [t.lower() for t in activity.get('tags', [])]
    
    if profile_tags and activity_tags:
        matching_tags = set(profile_tags) & set(activity_tags)
        if matching_tags:
            score += len(matching_tags) * 10
            reasons.append(f"标签匹配: {', '.join(matching_tags)}")
    
    profile_city = profile.get('location', {}).get('city', '').lower()
    activity_city = activity.get('location', {}).get('city', '').lower()
    
    if profile_city and activity_city and profile_city == activity_city:
        score += 20
        reasons.append("同城匹配")
    elif profile_city and activity_city:
        score -= 10
        reasons.append("异地活动")
    
    activity_category = activity.get('category', '').lower()
    if '运动' in activity_category or '户外' in activity_category:
        if any(t in profile_tags for t in ['运动', '户外', '健身', '跑步', '爬山']):
            score += 15
            reasons.append("运动兴趣匹配")
    elif '学习' in activity_category or '读书' in activity_category:
        if any(t in profile_tags for t in ['学习', '读书', '编程', '语言']):
            score += 15
            reasons.append("学习兴趣匹配")
    elif '美食' in activity_category:
        if '美食' in profile_tags:
            score += 15
            reasons.append("美食兴趣匹配")
    
    reputation = profile.get('reputation', 5.0)
    if reputation >= 4.5:
        score += 10
        reasons.append("高信誉用户")
    
    score = max(0, min(100, score))
    
    reason = "，".join(reasons) if reasons else "基于基本资料匹配"
    if not profile_tags:
        reason = "请完善个人资料以获得更准确的匹配评分"
    
    return jsonify({"score": score, "reason": reason}), 200

# Like/Pass action endpoint
@app.route('/api/actions', methods=['POST'])
def create_action():
    data = request.json
    from_uid = data.get('from_uid')
    to_uid = data.get('to_uid')
    action = data.get('action')  # 'like' or 'pass'
    
    if not from_uid or not to_uid or not action:
        return jsonify({'error': 'From UID, to UID, and action are required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Check if action already exists
        existing_action = db.actions.find_one({'from_uid': ObjectId(from_uid), 'to_uid': ObjectId(to_uid)})
        if existing_action:
            return jsonify({'error': 'Action already exists'}), 400
        
        action_id = db.actions.insert_one({
            'from_uid': ObjectId(from_uid),
            'to_uid': ObjectId(to_uid),
            'action': action,
            'created_at': datetime.now()
        }).inserted_id
        
        # Check for mutual like
        mutual_like = db.actions.find_one({'from_uid': ObjectId(to_uid), 'to_uid': ObjectId(from_uid), 'action': 'like'})
        
        return jsonify({
            'message': 'Action created successfully',
            'action_id': str(action_id),
            'mutual_match': mutual_like is not None
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create review endpoint
@app.route('/api/reviews', methods=['POST'])
def create_review():
    data = request.json
    from_uid = data.get('from_uid')
    to_uid = data.get('to_uid')
    activity_id = data.get('activity_id')
    rating = data.get('rating')
    comment = data.get('comment')
    
    if not from_uid or not to_uid or not activity_id or not rating:
        return jsonify({'error': 'From UID, to UID, activity ID, and rating are required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        review_id = db.reviews.insert_one({
            'from_uid': ObjectId(from_uid),
            'to_uid': ObjectId(to_uid),
            'activity_id': ObjectId(activity_id),
            'rating': rating,
            'comment': comment,
            'created_at': datetime.now()
        }).inserted_id
        
        # Update reputation score
        user_reviews = db.reviews.find({'to_uid': ObjectId(to_uid)})
        total_rating = 0
        review_count = 0
        for review in user_reviews:
            total_rating += review.get('rating', 0)
            review_count += 1
        
        if review_count > 0:
            new_reputation = total_rating / review_count
            db.profiles.update_one({'user_id': ObjectId(to_uid)}, {'$set': {'reputation': new_reputation}})
        
        return jsonify({'message': 'Review created successfully', 'review_id': str(review_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user reviews endpoint
@app.route('/api/reviews/<user_id>', methods=['GET'])
def get_user_reviews(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        user_reviews = db.reviews.find({'to_uid': ObjectId(user_id)}).sort('created_at', -1).limit(5)
        result = []
        for review in user_reviews:
            review['_id'] = str(review['_id'])
            review['from_uid'] = str(review['from_uid'])
            review['to_uid'] = str(review['to_uid'])
            review['activity_id'] = str(review['activity_id'])
            result.append(review)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# AI hint endpoint for activity creation
@app.route('/api/activity/ai_hint', methods=['POST'])
def get_activity_ai_hint():
    data = request.json
    activity_description = data.get('activity_description')
    
    if not activity_description:
        return jsonify({'error': 'Activity description is required'}), 400
    
    # 尝试使用本地规则生成_hint（作为备用）
    def generate_local_hint(desc):
        desc_lower = desc.lower()
        
        # 根据关键词判断分类
        category = '社交'
        if any(kw in desc_lower for kw in ['篮球', '足球', '羽毛球', '乒乓球', '跑步', '爬山', '健身', '运动', '游泳', '网球']):
            category = '运动'
        elif any(kw in desc_lower for kw in ['学习', '读书', '课程', '培训', '讲座']):
            category = '学习'
        elif any(kw in desc_lower for kw in ['电影', '唱歌', '游戏', '剧本杀', '桌游', '娱乐']):
            category = '娱乐'
        elif any(kw in desc_lower for kw in ['旅游', '旅行', '去', '玩']):
            category = '旅行'
        elif any(kw in desc_lower for kw in ['美食', '吃饭', '聚餐', '探店']):
            category = '美食'
        elif any(kw in desc_lower for kw in ['艺术', '画', '展览', '摄影']):
            category = '艺术'
        
        # 生成标题
        title = f"{category}活动"
        if '周末' in desc:
            title = f"周末{category}"
        if '晚上' in desc:
            title = f"晚间{category}"
        
        # 生成标签
        tags = [category]
        if '户外' in desc_lower:
            tags.append('户外')
        if '室内' in desc_lower:
            tags.append('室内')
        if '新手' in desc_lower or '小白' in desc_lower:
            tags.append('新手友好')
        
        # 生成人数
        people_count = {'min': 3, 'max': 10}
        
        # 生成简介
        description = desc
        
        # 生成要求
        requirements = '性格好，易相处'
        
        return {
            'title': title,
            'category': category,
            'duration': '2-3小时',
            'location_type': '室内' if '室内' in desc_lower else '户外',
            'people_count': people_count,
            'tags': tags,
            'description': description,
            'requirements': requirements
        }
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        api_key = "AIzaSyDrZEGpHGOuTi3Cc_0GPuuinpnK-ekAuxo"
        
        headers = {'Content-Type': 'application/json'}
        params = {'key': api_key}
        
        system_instruction = "你是一个专业的活动策划助手。你的任务是根据用户提供的活动描述，生成活动的相关维度信息，帮助用户快速创建活动。"
        user_query = f"请根据以下活动描述，生成活动的相关维度信息：\n{activity_description}\n\n请生成以下信息：\n1. 活动标题（简洁明了）\n2. 活动分类（例如：运动、学习、娱乐、社交等）\n3. 活动所需时间（建议时长）\n4. 活动地点类型（例如：室内、户外、线上等）\n5. 活动所需人数（建议范围）\n6. 活动标签（3-5个相关标签，用逗号分隔）\n7. 活动简介（基于用户描述的简洁总结）\n8. 建议的参与者要求（例如：技能水平、装备要求等）\n\n请以JSON格式返回，包含以下字段：title, category, duration, location_type, people_count, tags, description, requirements"
        
        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]}
        }
        
        response = requests.post(url, headers=headers, params=params, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        llm_response = response.json()
        
        if 'candidates' in llm_response and len(llm_response['candidates']) > 0:
            candidate = llm_response['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content'] and len(candidate['content']['parts']) > 0:
                text = candidate['content']['parts'][0]['text']
                if text.startswith('```json') and text.endswith('```'):
                    text = text[7:-3].strip()
                try:
                    hint_data = json.loads(text)
                    return jsonify(hint_data), 200
                except json.JSONDecodeError:
                    app.logger.error(f"AI hint response is not JSON: {text}")
        
        # 如果API调用失败，使用本地规则生成
        app.logger.warning(f"Using local hint generation due to API issue")
        return jsonify(generate_local_hint(activity_description)), 200
        
    except Exception as e:
        app.logger.error(f"AI hint generation failed: {e}")
        # API失败时使用本地规则生成
        return jsonify(generate_local_hint(activity_description)), 200

# Create buddy request endpoint
@app.route('/api/buddy_requests', methods=['POST'])
def create_buddy_request():
    data = request.json
    user_id = data.get('user_id')
    title = data.get('title')
    content = data.get('content')
    category = data.get('category')
    time = data.get('time')
    location = data.get('location')
    requirements = data.get('requirements', {})
    
    if not user_id or not title or not content:
        return jsonify({'error': 'User ID, title, and content are required'}), 400
    
    try:
        request_data = {
            'user_id': user_id,
            'request_id': str(ObjectId()),
            'title': title,
            'content': content,
            'category': category,
            'time': datetime.fromisoformat(time) if time else datetime.now(),
            'location': location,
            'requirements': requirements,
            'status': 'active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        if save_buddy_request(request_data):
            return jsonify({'message': 'Buddy request created successfully', 'request_id': request_data['request_id']}), 201
        else:
            return jsonify({'error': 'Buddy request creation failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user buddy requests endpoint
@app.route('/api/buddy_requests/<user_id>', methods=['GET'])
def get_user_buddy_requests(user_id):
    try:
        requests = get_buddy_requests(user_id)
        return jsonify(requests), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all buddy requests endpoint
@app.route('/api/buddy_requests', methods=['GET'])
def get_buddy_requests_list():
    try:
        requests = get_all_buddy_requests()
        return jsonify(requests), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update buddy request endpoint
@app.route('/api/buddy_requests/<request_id>', methods=['PUT'])
def update_buddy_request(request_id):
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        # Get existing request
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        existing_request = db.buddy_requests.find_one({'request_id': request_id, 'user_id': ObjectId(user_id)})
        if not existing_request:
            return jsonify({'error': 'Buddy request not found'}), 404
        
        # Update request
        update_data = {
            'title': data.get('title', existing_request.get('title')),
            'content': data.get('content', existing_request.get('content')),
            'category': data.get('category', existing_request.get('category')),
            'time': data.get('time', existing_request.get('time')),
            'location': data.get('location', existing_request.get('location')),
            'requirements': data.get('requirements', existing_request.get('requirements')),
            'status': data.get('status', existing_request.get('status')),
            'updated_at': datetime.now()
        }
        
        # Add user_id and request_id to update_data
        update_data['user_id'] = existing_request['user_id']
        update_data['request_id'] = request_id
        
        if save_buddy_request(update_data):
            return jsonify({'message': 'Buddy request updated successfully'}), 200
        else:
            return jsonify({'error': 'Buddy request update failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Delete buddy request endpoint
@app.route('/api/buddy_requests/<request_id>', methods=['DELETE'])
def delete_buddy_request(request_id):
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        result = db.buddy_requests.delete_one({'request_id': request_id, 'user_id': ObjectId(user_id)})
        if result.deleted_count > 0:
            return jsonify({'message': 'Buddy request deleted successfully'}), 200
        else:
            return jsonify({'error': 'Buddy request not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Batch score endpoint
@app.route('/api/batch_score', methods=['POST'])
def batch_score():
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    data = request.json
    user_a = data.get('userA', {})
    users_b = data.get('usersB', [])
    match_mode = data.get('matchMode', 'similarity')
    
    if not user_a or not users_b:
        return jsonify({'error': 'User A and Users B are required'}), 400
    
    all_profiles_prompt = ""
    user_a_profile = format_profile(user_a)
    profiles_map = {}
    for user_b in users_b:
        profile_b = format_profile(user_b)
        all_profiles_prompt += f"\n--- 用户 B ({user_b['user_id']}) ---\n{profile_b}"
        profiles_map[user_b['user_id']] = user_b
    
    system_instruction_batch = f"""
    你是一个顶级的伙伴匹配专家。你的任务是快速评估发起匹配的用户 (User A) 与提供的批量用户列表 (Users B) 的匹配度。
    - **模式：** {match_mode} 匹配。如果是 'complementary'，请注重互补潜力。
    - **输出：** 必须严格返回一个 JSON 数组，包含每个用户的匹配得分和等级。
    - **跳过详细理由：** 只返回分数和等级。
    """
    
    user_query = f"""
    发起匹配者 (User A) 资料:
{user_a_profile}

    请评估 User A 与以下 {len(users_b)} 位用户的匹配度。对于每一位用户 B，请给出其 user_id，并给出主观评分和等级。

    {all_profiles_prompt}

    请严格根据你的系统指令，输出最终的 JSON 结果。
    """
    
    response_schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"userId": {"type": "STRING"},
                                                                                   "matchScore": {"type": "INTEGER"},
                                                                                   "matchLevel": {"type": "STRING"}},
                                                  "required": ["userId", "matchScore", "matchLevel"]}}
    
    payload = {"contents": [{"parts": [{"text": user_query}]}],
               "systemInstruction": {"parts": [{"text": system_instruction_batch}]},
               "generationConfig": {"responseMimeType": "application/json", "responseSchema": response_schema}}
    
    try:
        llm_response = call_gemini_api(payload)
        json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
        batch_results = json.loads(json_str)

        final_results_with_objective = []
        for result in batch_results:
            user_b_id = result.get('userId')
            if user_b_id in profiles_map:
                user_b_summary = profiles_map[user_b_id].get('personality', '')
                user_a_summary = user_a.get('personality', '')
                objective_overlap_score = calculate_simple_similarity(user_a_summary, user_b_summary)
                result['objectiveOverlapScore'] = objective_overlap_score
                final_results_with_objective.append(result)
            else:
                result['objectiveOverlapScore'] = 0
                final_results_with_objective.append(result)
        return jsonify(final_results_with_objective), 200
    except Exception as e:
        app.logger.error(f"Batch scoring failed: {e}")
        return jsonify({"error": f"Batch scoring failed: {e}"}), 500

# Buddy request match endpoint
@app.route('/api/buddy_request/match', methods=['POST'])
def match_buddy_requests():
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    data = request.json
    user_profile = data.get('user_profile')
    buddy_requests = data.get('buddy_requests', [])
    
    if not user_profile or not buddy_requests:
        return jsonify({'error': 'User profile and buddy requests are required'}), 400
    
    all_requests_prompt = ""
    user_profile_str = format_profile(user_profile)
    requests_map = {}
    for request in buddy_requests:
        request_str = format_buddy_request(request)
        all_requests_prompt += f"\n--- 诉求 ({request.get('request_id', 'unknown')}) ---\n{request_str}"
        requests_map[request.get('request_id', 'unknown')] = request
    
    system_instruction = """
    你是一个顶级的伙伴匹配专家。你的任务是评估用户与多个短期找搭子诉求的匹配度。
    - **评估标准：** 考虑用户的长期信息（性格、兴趣、地点等）与短期诉求的匹配程度。
    - **输出：** 必须严格返回一个 JSON 数组，包含每个诉求的匹配得分和等级。
    - **跳过详细理由：** 只返回分数和等级。
    """
    
    user_query = f"""
    用户资料:
{user_profile_str}

    请评估该用户与以下 {len(buddy_requests)} 个短期找搭子诉求的匹配度。对于每个诉求，请给出其 request_id，并给出主观评分和等级。

    {all_requests_prompt}

    请严格根据你的系统指令，输出最终的 JSON 结果。
    """
    
    response_schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"requestId": {"type": "STRING"},
                                                                                   "matchScore": {"type": "INTEGER"},
                                                                                   "matchLevel": {"type": "STRING"}},
                                                  "required": ["requestId", "matchScore", "matchLevel"]}}
    
    payload = {"contents": [{"parts": [{"text": user_query}]}],
               "systemInstruction": {"parts": [{"text": system_instruction}]},
               "generationConfig": {"responseMimeType": "application/json", "responseSchema": response_schema}}
    
    try:
        llm_response = call_gemini_api(payload)
        json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
        match_results = json.loads(json_str)
        return jsonify(match_results), 200
    except Exception as e:
        app.logger.error(f"Buddy request matching failed: {e}")
        return jsonify({"error": f"Buddy request matching failed: {e}"}), 500

# --- 认证模块 API ---#

# Register user
@app.route('/api/auth/register', methods=['POST'])
def register():
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        existing_user = db.users.find_one({'email': email})
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_id = ObjectId()
        user = {
            '_id': user_id,
            'name': name,
            'email': email,
            'password': hashed_password.decode('utf-8'),
            'created_at': datetime.now()
        }
        
        # Create profile
        profile = {
            'user_id': user_id,
            'name': name,
            'gender': '',
            'age': 0,
            'mbti': '',
            'occupation': '',
            'hobbies': [],
            'location': { 'city': '', 'district': '' },
            'personality': '',
            'privacy_settings': { 'age_visible': True, 'occupation_visible': True },
            'reputation': 5.0,
            'ai_tags': [],
            'created_at': datetime.now()
        }
        
        db.users.insert_one(user)
        db.profiles.insert_one(profile)
        
        return jsonify({
            'user_id': str(user_id),
            'name': name,
            'email': email
        }), 201
    except Exception as e:
        app.logger.error(f"Error registering user: {e}")
        return jsonify({'error': str(e)}), 500

# Login user
@app.route('/api/auth/login', methods=['POST'])
def login():
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find user
        user = db.users.find_one({'email': email})
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check password
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Get profile
        profile = db.profiles.find_one({'user_id': user['_id']})
        profile_data = {
            'user_id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'gender': profile.get('gender', ''),
            'age': profile.get('age', 0),
            'mbti': profile.get('mbti', ''),
            'occupation': profile.get('occupation', ''),
            'hobbies': profile.get('hobbies', []),
            'location': profile.get('location', { 'city': '', 'district': '' }),
            'personality': profile.get('personality', ''),
            'privacy_settings': profile.get('privacy_settings', { 'age_visible': True, 'occupation_visible': True }),
            'reputation': profile.get('reputation', 5.0),
            'ai_tags': profile.get('ai_tags', [])
        }
        
        return jsonify(profile_data), 200
    except Exception as e:
        app.logger.error(f"Error logging in: {e}")
        return jsonify({'error': str(e)}), 500

# --- 消息列表模块 API ---#

# Create or get conversation
@app.route('/api/conversations', methods=['POST'])
def create_or_get_conversation():
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        user1_id = data.get('user1_id')
        user2_id = data.get('user2_id')
        
        if not user1_id or not user2_id:
            return jsonify({'error': 'Both user IDs are required'}), 400
        
        # Check if conversation already exists
        existing_conv = db.conversations.find_one({
            'participants': {'$all': [ObjectId(user1_id), ObjectId(user2_id)]}
        })
        
        if existing_conv:
            return jsonify({
                'conversation_id': str(existing_conv['_id']),
                'exists': True
            }), 200
        
        # Create new conversation
        conversation = {
            'participants': [ObjectId(user1_id), ObjectId(user2_id)],
            'last_message': '',
            'last_message_at': datetime.now(),
            'created_at': datetime.now()
        }
        
        conv_id = db.conversations.insert_one(conversation).inserted_id
        
        return jsonify({
            'conversation_id': str(conv_id),
            'exists': False
        }), 201
    except Exception as e:
        app.logger.error(f'Error creating conversation: {e}')
        return jsonify({'error': str(e)}), 500

# Get user conversations
@app.route('/api/conversations/<user_id>', methods=['GET'])
def get_user_conversations(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get all conversations where the user is a participant
        conversations = db.conversations.find({'participants': ObjectId(user_id)})
        result = []
        for conv in conversations:
            # Get the other participant
            other_participant_id = None
            for participant in conv['participants']:
                if participant != ObjectId(user_id):
                    other_participant_id = participant
                    break
            
            if other_participant_id:
                # Get other participant's profile
                other_profile = db.profiles.find_one({'user_id': other_participant_id})
                other_user_name = other_profile.get('name', '用户' + str(other_participant_id)[-4:]) if other_profile else '未知用户'
                
                # Get last message
                last_message = db.messages.find({'conversation_id': conv['_id']}).sort('created_at', -1).limit(1)
                last_message_data = None
                for msg in last_message:
                    last_message_data = {
                        'content': msg.get('content', ''),
                        'created_at': msg.get('created_at', datetime.now())
                    }
                
                result.append({
                    'conversation_id': str(conv['_id']),
                    'other_user_id': str(other_participant_id),
                    'other_user_name': other_user_name,
                    'last_message': last_message_data,
                    'created_at': conv.get('created_at', datetime.now())
                })
        
        # Sort by last message time
        result.sort(key=lambda x: x['last_message']['created_at'] if x['last_message'] else x['created_at'], reverse=True)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get conversation messages
@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        messages = db.messages.find({'conversation_id': ObjectId(conversation_id)}).sort('created_at', 1)
        result = []
        for msg in messages:
            result.append({
                '_id': str(msg['_id']),
                'sender_id': str(msg['sender_id']),
                'content': msg.get('content', ''),
                'created_at': msg.get('created_at', datetime.now())
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Send message
@app.route('/api/messages', methods=['POST'])
def send_message():
    data = request.json
    sender_id = data.get('sender_id')
    conversation_id = data.get('conversation_id')
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not sender_id or not content:
        return jsonify({'error': 'Sender ID and content are required'}), 400
    
    if not conversation_id and not receiver_id:
        return jsonify({'error': 'Conversation ID or receiver ID is required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # If no conversation_id, find or create conversation
        if not conversation_id:
            conversation = db.conversations.find_one({
                'participants': {'$all': [ObjectId(sender_id), ObjectId(receiver_id)]}
            })
            
            if not conversation:
                conversation_id = db.conversations.insert_one({
                    'participants': [ObjectId(sender_id), ObjectId(receiver_id)],
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                }).inserted_id
            else:
                conversation_id = conversation['_id']
        else:
            conversation_id = ObjectId(conversation_id)
        
        # Update conversation updated_at
        db.conversations.update_one(
            {'_id': conversation_id},
            {'$set': {'updated_at': datetime.now()}}
        )
        
        # Create message
        message_id = db.messages.insert_one({
            'conversation_id': conversation_id,
            'sender_id': ObjectId(sender_id),
            'content': content,
            'created_at': datetime.now()
        }).inserted_id
        
        return jsonify({
            'message': 'Message sent successfully',
            'message_id': str(message_id),
            'conversation_id': str(conversation_id)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user detailed information
@app.route('/api/user/<user_id>/details', methods=['GET'])
def get_user_details(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get user profile
        profile = get_user_profile(user_id)
        if not profile:
            return jsonify({'error': 'User profile not found'}), 404
        
        # Get user's activities (regardless of status, for showing in profile)
        all_activities = db.activities.find({'user_id': ObjectId(user_id)}).sort('created_at', -1)
        
        ongoing_activities_list = []
        past_activities_list = []
        now = datetime.now()
        
        for activity in all_activities:
            activity['_id'] = str(activity['_id'])
            activity['user_id'] = str(activity['user_id'])
            activity['participants'] = [str(p) for p in activity.get('participants', [])]
            
            # Check if activity is past or ongoing based on time
            activity_time = activity.get('time')
            if activity_time and activity_time < now:
                past_activities_list.append(activity)
            else:
                ongoing_activities_list.append(activity)
        
        # Get user's reviews
        reviews = db.reviews.find({'to_uid': ObjectId(user_id)}).sort('created_at', -1).limit(5)
        reviews_list = []
        for review in reviews:
            review['_id'] = str(review['_id'])
            review['from_uid'] = str(review['from_uid'])
            review['to_uid'] = str(review['to_uid'])
            review['activity_id'] = str(review['activity_id'])
            reviews_list.append(review)
        
        return jsonify({
            'profile': profile,
            'ongoing_activities': ongoing_activities_list,
            'past_activities': past_activities_list,
            'reviews': reviews_list
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 个人中心模块 API ---#

# Get all applications for user's activities (as activity host)
@app.route('/api/user/<user_id>/host-applications', methods=['GET'])
def get_user_host_applications(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get all activities created by this user
        user_activities = db.activities.find({'user_id': ObjectId(user_id)})
        activity_ids = [a['_id'] for a in user_activities]
        
        # Get all applications for these activities
        applications = db.activity_applications.find({'activity_id': {'$in': activity_ids}})
        
        result = []
        for app in applications:
            # Get activity details
            activity = db.activities.find_one({'_id': app['activity_id']})
            if not activity:
                continue
            
            # Get applicant profile
            applicant_profile = db.profiles.find_one({'user_id': app['user_id']})
            applicant_name = applicant_profile.get('name', 'Unknown') if applicant_profile else 'Unknown'
            
            result.append({
                '_id': str(app['_id']),
                'activity_id': str(app['activity_id']),
                'activity_title': activity.get('title', 'Unknown'),
                'applicant_id': str(app['user_id']),
                'applicant_name': applicant_name,
                'status': app.get('status', 'pending'),
                'created_at': app.get('created_at', datetime.now()).isoformat() if hasattr(app.get('created_at', datetime.now()), 'isoformat') else str(app.get('created_at', datetime.now()))
            })
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update activity
@app.route('/api/activities/<activity_id>', methods=['PUT'])
def update_activity(activity_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.json
        user_id = data.get('user_id')
        
        # Check if activity exists and belongs to user
        activity = db.activities.find_one({'_id': ObjectId(activity_id)})
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404
        
        if str(activity['user_id']) != user_id:
            return jsonify({'error': 'Not authorized to update this activity'}), 403
        
        update_data = {
            'title': data.get('title', activity.get('title')),
            'content': data.get('content', activity.get('content')),
            'category': data.get('category', activity.get('category')),
            'location': data.get('location', activity.get('location')),
            'budget': data.get('budget', activity.get('budget', 0)),
            'people_range': data.get('people_range', activity.get('people_range', {})),
            'requirements': data.get('requirements', activity.get('requirements', '')),
            'need_confirmation': data.get('need_confirmation', activity.get('need_confirmation', False)),
            'deposit': data.get('deposit', activity.get('deposit', 0)),
            'tags': data.get('tags', activity.get('tags', [])),
            'time': data.get('time', activity.get('time')),
            'updated_at': datetime.now()
        }
        
        db.activities.update_one(
            {'_id': ObjectId(activity_id)},
            {'$set': update_data}
        )
        
        return jsonify({'message': 'Activity updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Delete/Cancel activity
@app.route('/api/activities/<activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        user_id = request.args.get('user_id')
        
        # Check if activity exists and belongs to user
        activity = db.activities.find_one({'_id': ObjectId(activity_id)})
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404
        
        if str(activity['user_id']) != user_id:
            return jsonify({'error': 'Not authorized to delete this activity'}), 403
        
        # Delete the activity
        db.activities.delete_one({'_id': ObjectId(activity_id)})
        
        # Delete related applications
        db.activity_applications.delete_many({'activity_id': ObjectId(activity_id)})
        
        return jsonify({'message': 'Activity deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user's applied activities
@app.route('/api/user/<user_id>/applied-activities', methods=['GET'])
def get_user_applied_activities(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get activity applications where user is the applicant
        applications = db.activity_applications.find({'applicant_id': ObjectId(user_id), 'status': 'approved'})
        applied_activity_ids = []
        for app in applications:
            applied_activity_ids.append(app['activity_id'])
        
        # Get activities
        activities = db.activities.find({'_id': {'$in': applied_activity_ids}})
        activities_list = []
        for activity in activities:
            activity['_id'] = str(activity['_id'])
            activity['user_id'] = str(activity['user_id'])
            activity['participants'] = [str(p) for p in activity.get('participants', [])]
            activities_list.append(activity)
        
        return jsonify(activities_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user's reviews (as reviewer)
@app.route('/api/user/<user_id>/reviews-given', methods=['GET'])
def get_user_reviews_given(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        reviews = db.reviews.find({'from_uid': ObjectId(user_id)}).sort('created_at', -1)
        reviews_list = []
        for review in reviews:
            # Get activity title
            activity = db.activities.find_one({'_id': review['activity_id']})
            activity_title = activity.get('title', 'Unknown Activity') if activity else 'Unknown Activity'
            
            # Get recipient's profile
            recipient_profile = db.profiles.find_one({'user_id': review['to_uid']})
            recipient_name = recipient_profile.get('name', 'User') if recipient_profile else 'User'
            
            reviews_list.append({
                '_id': str(review['_id']),
                'to_uid': str(review['to_uid']),
                'to_name': recipient_name,
                'activity_id': str(review['activity_id']),
                'activity_title': activity_title,
                'rating': review['rating'],
                'comment': review.get('comment', ''),
                'created_at': review.get('created_at', datetime.now())
            })
        
        return jsonify(reviews_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get user's statistics
@app.route('/api/user/<user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Count activities created (not relying on status)
        activities_created = db.activities.count_documents({'user_id': ObjectId(user_id)})
        
        # Count activities joined (as participant)
        activities_as_participant = db.activities.count_documents({
            'participants': ObjectId(user_id),
            'user_id': {'$ne': ObjectId(user_id)}
        })
        
        # Count reviews received
        reviews_received = db.reviews.count_documents({'to_uid': ObjectId(user_id)})
        
        # Calculate average rating
        reviews = db.reviews.find({'to_uid': ObjectId(user_id)})
        total_rating = 0
        review_count = 0
        for review in reviews:
            total_rating += review.get('rating', 0)
            review_count += 1
        average_rating = total_rating / review_count if review_count > 0 else 0
        
        # Count matches
        likes_given = db.actions.count_documents({'from_uid': ObjectId(user_id), 'action': 'like'})
        likes_received = db.actions.count_documents({'to_uid': ObjectId(user_id), 'action': 'like'})
        
        return jsonify({
            'activities_created': activities_created,
            'activities_joined': activities_as_participant,
            'reviews_received': reviews_received,
            'average_rating': round(average_rating, 1),
            'likes_given': likes_given,
            'likes_received': likes_received
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- AI 活动助手 API ---#

@app.route('/api/agent/chat', methods=['POST'])
def agent_chat():
    data = request.json
    user_message = data.get('message', '')
    requirements = data.get('requirements', {})
    conversation_history = data.get('conversation_history', [])
    current_user_id = data.get('user_id', '')
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get all ongoing activities
        activities = list(db.activities.find({'status': 'ongoing'}))
        activity_list = []
        for activity in activities:
            activity['_id'] = str(activity['_id'])
            activity['user_id'] = str(activity['user_id'])
            activity['participants'] = [str(p) for p in activity.get('participants', [])]
            if 'requirements' not in activity:
                activity['requirements'] = ''
            if 'tags' not in activity:
                activity['tags'] = []
            for key, value in activity.items():
                if isinstance(value, datetime):
                    activity[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            activity_list.append(activity)
        
        # Check for travel/trip intent
        travel_keywords = ['旅游', '旅行', '去', '玩', '行程', '攻略', '台北', '台湾', '日本', '韩国', 
                         '泰国', '新加坡', '欧洲', '美国', '自由行', '度假', '出境', '出境游',
                         '周边游', '长途', '短途', '几天', '几天几夜', '几天几晚']
        is_travel_intent = any(kw in user_message for kw in travel_keywords)
        
        # Build conversation context
        context = []
        for msg in conversation_history:
            context.append(f"{msg['role']}: {msg['content']}")
        
        # System prompt for the agent - Simplified for activity recommendation
        system_instruction = f"""你是一个活动推荐助手。你的任务是根据用户需求推荐活动，如果没有合适的活动则帮助用户创建。

## 你的工作流程：

### 第一步：理解用户需求
用户可能会说：
- "推荐一些活动" / "帮我找点活动"
- "我想打篮球" / "想唱歌"
- "周末无聊，想找人玩"
- "创建一个活动"

### 第二步：提取关键信息
- activity_type: 活动类型（运动/娱乐/学习/社交/美食/旅行/艺术/游戏）
- location: 期望地点（城市/区域）
- budget: 预算范围
- time: 时间（今天/周末/具体日期）
- people: 人数

### 第三步：搜索匹配活动
先从活动数据库中搜索匹配的活动，如果有匹配的则推荐给用户。

### 第四步：没有匹配时帮助创建
如果用户说"创建一个活动"或者搜索后没有合适的活动，主动询问创建活动所需的信息（标题、内容、时间、地点等），然后帮用户发布。

## 活动数据库（共{len(activity_list)}个活动）：
{json.dumps(activity_list[:50], ensure_ascii=False)[:3000]}

## 返回格式（必须返回JSON）：
1. 推荐活动时：
{{
    "response": "根据您的xxx需求，我为您找到以下活动：",
    "requirements": {{"activity_type": "运动", "location": "北京"}},
    "recommendations": [活动列表，最多3个],
    "suggestions": ["查看详情", "换一个类型", "创建一个新活动"],
    "mode": "recommend"
}}

2. 收集创建信息时：
{{
    "response": "好的，请告诉我您想创建什么活动？比如：活动标题、时间、地点、内容...",
    "requirements": {{}},
    "recommendations": [],
    "suggestions": ["推荐一些活动", "创建一个羽毛球活动", "帮我找个聚会"],
    "mode": "create"
}}

3. 确认发布时：
{{
    "response": "好的，正在为您发布活动...",
    "action": "publish",
    "activity_data": {{"title": "标题", "content": "内容", "category": "分类", "time": "时间", "location": {{"city": "城市", "district": "区域"}}, "budget": 预算, "tags": ["标签"]}},
    "mode": "publish"
}}

4. 普通对话：
{{
    "response": "您的回复",
    "requirements": {{}},
    "recommendations": [],
    "suggestions": ["推荐活动", "创建活动"],
    "mode": "qa"
}}

请根据用户输入返回正确的JSON格式。不要返回除JSON以外的内容。"""
        
        user_query = f"""用户说：{user_message}

请根据用户需求返回正确的JSON响应。"""

        payload = {
            "contents": [{"parts": [{"text": user_query}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.7
            }
        }
        
        try:
            llm_response = call_gemini_api(payload)
            json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
            
            # Try to parse the response
            try:
                result = json.loads(json_str)
                
                # Handle publish action
                if result.get('action') == 'publish' or result.get('mode') == 'publish':
                    activity_data = result.get('activity_data', {})
                    if activity_data and current_user_id:
                        try:
                            # Create the activity
                            new_activity = {
                                'user_id': ObjectId(current_user_id),
                                'title': activity_data.get('title', ''),
                                'content': activity_data.get('content', ''),
                                'category': activity_data.get('category', '旅行'),
                                'time': datetime.now(),
                                'location': activity_data.get('location', {}),
                                'budget': activity_data.get('budget', 0),
                                'people_range': activity_data.get('people_range', {'min': 1, 'max': 10}),
                                'requirements': activity_data.get('requirements', ''),
                                'status': 'ongoing',
                                'tags': activity_data.get('tags', []),
                                'participants': [],
                                'created_at': datetime.now()
                            }
                            db.activities.insert_one(new_activity)
                            result['published'] = True
                            result['response'] = "🎉 行程已成功发布！可以在活动广场查看和管理。"
                        except Exception as pe:
                            result['published'] = False
                            result['response'] = f"发布失败: {str(pe)}"
                
                return jsonify(result), 200
            except json.JSONDecodeError:
                # If not JSON, return as text response
                return jsonify({
                    'response': json_str,
                    'requirements': requirements,
                    'suggestions': [
                        '您想去哪里旅行？',
                        '您的预算是多少？',
                        '计划玩几天？'
                    ],
                    'mode': 'qa'
                }), 200
                
        except Exception as e:
            app.logger.error(f"LLM error: {e}")
            # Fallback to simple recommend
            result = simple_recommend(user_message, requirements, activity_list, is_travel_intent)
            return jsonify(result), 200
            # Fallback: simple keyword matching
            result = simple_recommend(user_message, requirements, activity_list, is_travel_intent)
            return jsonify(result), 200
            
    except Exception as e:
        app.logger.error(f"Agent error: {e}")
        return jsonify({'error': str(e)}), 500


def simple_recommend(user_message, requirements, activity_list, is_travel_intent=False):
    """Simple fallback recommendation without LLM"""
    msg_lower = user_message.lower()
    
    # Extract requirements from message
    new_requirements = dict(requirements)
    
    # Check if user is asking a question vs wants recommendation
    question_patterns = ['怎么', '如何', '为什么', '是什么', '?', '？', '能不能', '可以帮', '帮我', '推荐', '找']
    is_question = any(p in msg_lower for p in question_patterns)
    wants_recommendation = any(p in msg_lower for p in ['推荐', '找', '参加', '活动', '玩'])
    
    # Travel-specific extraction
    travel_keywords = ['旅游', '旅行', '去', '玩', '行程', '几天', '台北', '台湾', '日本', '韩国', '泰国', '新加坡']
    is_travel = is_travel_intent or any(kw in msg_lower for kw in travel_keywords)
    
    # Destination extraction
    destinations = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆', '天津', '苏州', '长沙',
                   '台北', '台湾', '日本', '韩国', '泰国', '新加坡', '欧洲', '美国', '澳洲', '马尔代夫', '巴厘岛', '普吉岛']
    for dest in destinations:
        if dest in user_message:
            new_requirements['destination'] = dest
    
    # Duration extraction
    duration_patterns = [
        ('一天', 1), ('两天', 2), ('三天', 3), ('四天', 4), ('五天', 5), ('六天', 6), ('七天', 7),
        ('一天一夜', 1), ('两天一夜', 2), ('三天两夜', 3), ('四天三夜', 4), ('五天四夜', 5),
        ('一天一晚', 1), ('两天一晚', 2), ('三天两晚', 3), ('四天三晚', 4), ('五天四晚', 5),
        ('1天', 1), ('2天', 2), ('3天', 3), ('4天', 4), ('5天', 5), ('6天', 6), ('7天', 7),
    ]
    for pattern, days in duration_patterns:
        if pattern in msg_lower:
            new_requirements['duration'] = days
    
    # Travelers extraction
    travelers_keywords = {
        '一个人': 1, '独自': 1, 'solo': 1,
        '两个人': 2, '情侣': 2, '夫妻': 2, '两人': 2,
        '三个人': 3, '三人': 3,
        '四个人': 4, '四人': 4,
        '朋友': 5, '同事': 5, '一家人': 4, '家人': 4, '亲子': 3
    }
    for key, count in travelers_keywords.items():
        if key in msg_lower:
            new_requirements['travelers'] = count
    
    # Location keywords
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆', '天津', '苏州', '长沙']
    for city in cities:
        if city in user_message:
            new_requirements['city'] = city
    
    # Budget keywords
    budgets = {
        '50': 50, '100': 100, '200': 200, '300': 300, '500': 500, '1000': 1000,
        '五十': 50, '一百': 100, '两百': 200, '三百': 300, '五百': 500, '一千': 1000,
        '以内': 9999, '以下': 9999, '左右': 500
    }
    for key, val in budgets.items():
        if key in msg_lower:
            new_requirements['budget'] = val
    
    # Activity type keywords
    activity_types = {
        '运动': ['篮球', '足球', '羽毛球', '网球', '游泳', '跑步', '健身', '瑜伽', '乒乓球', '滑雪', '登山'],
        '娱乐': ['桌游', '密室', 'KTV', '电影', '唱歌', '游戏', '剧本杀', '狼人杀', '棋牌'],
        '社交': ['聚会', '交友', '认识', '社交', '搭子', '组队'],
        '学习': ['读书', '学习', '讲座', '培训', '交流', '分享'],
        '文艺': ['绘画', '手工', '摄影', '音乐', '展览', '戏剧', '舞蹈'],
        '户外': ['徒步', '露营', '骑行', '郊游', '踏青'],
        '美食': ['美食', '吃饭', '聚餐', '下午茶', '咖啡']
    }
    for atype, keywords in activity_types.items():
        for kw in keywords:
            if kw in msg_lower:
                new_requirements['activity_type'] = atype
    
    # Time keywords - more comprehensive
    time_keywords = {
        'weekend': ['周末', '周六', '周日', '周六日', '节假日', '假期'],
        'weekday': ['工作日', '周一', '周二', '周三', '周四', '周五'],
        'morning': ['上午', '早上', '早晨', '早'],
        'afternoon': ['下午', '午后'],
        'evening': ['晚上', '傍晚', '夜']
    }
    
    user_time = []
    for time_type, keywords in time_keywords.items():
        if any(kw in msg_lower for kw in keywords):
            user_time.append(time_type)
    if user_time:
        new_requirements['time'] = user_time
    
    # If user is just asking a question, don't recommend activities
    if is_question and not wants_recommendation:
        responses = {
            '运动': '运动类活动可以帮助您保持健康，释放压力！您想参加什么类型的运动呢？',
            '娱乐': '娱乐活动可以放松身心！桌游、KTV、密室逃脱都是不错的选择~',
            '社交': '社交活动可以帮助您认识新朋友！您想通过什么方式认识新朋友呢？',
            '学习': '学习类活动可以提升自己！读书会、讲座、培训都是很好的选择。',
            '文艺': '文艺活动可以培养情趣！绘画、音乐、展览都很不错~',
            '户外': '户外活动可以亲近自然！徒步、露营、骑行都很有趣。'
        }
        
        atype = new_requirements.get('activity_type', '')
        response = responses.get(atype, "没问题！请告诉我更多您的需求，比如：\n1. 您在哪个城市？\n2. 您的预算是多少？\n3. 想参加什么类型的活动？\n4. 周末还是工作日？")
        
        return {
            'response': response,
            'requirements': new_requirements,
            'recommendations': [],
            'suggestions': ['推荐一些活动', '周末活动', '北京的运动']
        }
    
    # Score activities
    scored = []
    for activity in activity_list:
        score = 0
        matched_fields = []
        
        activity_time = str(activity.get('time', '')).lower()
        
        # Location match (30 points)
        if new_requirements.get('city'):
            if activity.get('location', {}).get('city') == new_requirements['city']:
                score += 30
                matched_fields.append('location')
        
        # Budget match (20 points)
        if new_requirements.get('budget'):
            activity_budget = activity.get('budget', 0)
            if activity_budget > 0 and activity_budget <= new_requirements['budget']:
                score += 20
                matched_fields.append('budget')
        
        # Activity type match (25 points)
        if new_requirements.get('activity_type'):
            category = activity.get('category', '').lower()
            tags = ' '.join(activity.get('tags', [])).lower()
            content = activity.get('content', '').lower()
            
            if (new_requirements['activity_type'] in category or 
                new_requirements['activity_type'] in tags or
                new_requirements['activity_type'] in content):
                score += 25
                matched_fields.append('type')
        
        # Time match (25 points) - more strict
        if new_requirements.get('time'):
            user_times = new_requirements['time']
            
            # Weekend preference
            if 'weekend' in user_times:
                if any(t in activity_time for t in ['六', '日', '天', '周末', '假日']):
                    score += 25
                    matched_fields.append('time')
                elif not any(t in activity_time for t in ['一', '二', '三', '四', '五']):
                    # No specific weekday mentioned, could be flexible
                    score += 10
            # Weekday preference
            elif 'weekday' in user_times:
                if any(t in activity_time for t in ['一', '二', '三', '四', '五', '工作日']):
                    score += 25
                    matched_fields.append('time')
        
        if score > 0:
            activity['search_score'] = score
            activity['match_score'] = min(score, 100)
            scored.append(activity)
    
    scored.sort(key=lambda x: x.get('search_score', 0), reverse=True)
    recommendations = scored[:5]
    
    # Generate response
    if not new_requirements:
        response = "好的！请告诉我：\n1. 您在哪个城市？\n2. 您的预算是多少？\n3. 想参加什么类型的活动？\n4. 周末还是工作日？"
        suggestions = ['北京', '上海', '周末活动']
    elif recommendations:
        response = f"根据您的需求，为您找到 {len(recommendations)} 个推荐活动！"
        suggestions = ['看看其他活动', '修改预算', '换个城市']
    else:
        # Try to find any activities if none matched
        all_activities = activity_list[:5]
        if all_activities:
            response = "没有找到完全匹配的活动，看看这些热门活动？"
            recommendations = all_activities
        else:
            response = "目前没有找到合适的活动，您可以换个条件试试~"
        suggestions = ['提高预算', '换个活动类型', '查看所有活动']
    
    return {
        'response': response,
        'requirements': new_requirements,
        'recommendations': recommendations,
        'suggestions': suggestions
    }


if __name__ == '__main__':
    # 初始化数据库连接 (在启动时完成)
    get_db_client()

    if GEMINI_API_KEY == "geminikey":
        print("\n!!! 警告: 请务必在代码中替换 GEMINI_API_KEY !!!\n")

    print("------------------------------------------------------------------")
    print(" Flask 后端启动成功！系统已启用 Embeddings 预筛选 (Python 内存模式)")
    print("------------------------------------------------------------------")
    app.run(debug=True, port=5005)
