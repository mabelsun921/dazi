# -*- coding: utf-8 -*-
import os
import json
import requests
import jieba
import re
import base64
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, errors
from bson.objectid import ObjectId

# --- 配置 ---
# 🚨 替换点：请务必将此占位符替换为您的真实 API Key
GEMINI_API_KEY = "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
EMBEDDING_MODEL = "text-embedding-004"
GENERATIVE_MODEL = "gemini-2.5-flash-preview-09-2025"
GEMINI_API_URL = f"{GEMINI_API_BASE_URL}{GENERATIVE_MODEL}:generateContent"

# --- MongoDB 配置 ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "DapPeerMatchDB"
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

def save_user_auth(userId, email, password_hash):
    db = get_db()
    if db is None: return False
    try:
        result = db.users.update_one(
            {'userId': userId},
            {'$set': {'email': email, 'passwordHash': password_hash, 'createdAt': time.time()}},
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
        bio = profile_data.get('UserBioSummary', '')
        expectations = profile_data.get('partnerExpectations', '')
        hobbies = ', '.join(profile_data.get('optionalInfo', {}).get('hobbies', []))
        text_to_embed = f"Bio: {bio}. Expectations: {expectations}. Hobbies: {hobbies}"

        embedding_vector = None
        if len(text_to_embed) > 50:
            try:
                app.logger.info(f"DEBUG: Generating new embedding for user {profile_data['userId']}")
                embedding_vector = call_gemini_embedding_api(text_to_embed)
                profile_data['embedding_vector'] = embedding_vector
            except ConnectionError as e:
                app.logger.error(f"Error: Embedding API connection failed during profile save. Details: {e}")
            except Exception as e:
                app.logger.error(f"Error: Unknown error generating embedding during profile save. Details: {e}")
                pass

        # 2. 执行资料保存/更新
        result = db.profiles.update_one(
            {'userId': profile_data['userId']},
            {'$set': profile_data},
            upsert=True
        )

        app.logger.info(f"DEBUG: save_user_profile successful. Vector generated? {'Y' if embedding_vector else 'N'}")
        return result.acknowledged and (
                result.upserted_id is not None or result.modified_count > 0 or result.matched_count > 0)
    except Exception as e:
        app.logger.error(f"Error saving user profile: {e}")
        return False


def get_user_profile(userId):
    db = get_db()
    if db is None: return None
    profile = db.profiles.find_one({'userId': userId})
    if profile:
        profile['_id'] = str(profile['_id'])
    return profile


def get_all_profiles(current_userId):
    db = get_db()
    if db is None: return []
    profiles_cursor = db.profiles.find({'userId': {'$ne': current_userId}})
    profiles_list = []
    for profile in profiles_cursor:
        if 'embedding_vector' in profile:
            del profile['embedding_vector']
        profile['_id'] = str(profile['_id'])
        profiles_list.append(profile)
    return profiles_list


# --- 辅助函数 (LLM/Jieba/Base64/Embedding) ---
def calculate_keyword_overlap(summary_a, summary_b):
    # (关键词重叠度计算逻辑不变)
    def clean_and_tokenize(text):
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        words = jieba.lcut(text.lower())
        return set([w for w in words if len(w) > 1])

    set_a = clean_and_tokenize(summary_a)
    set_b = clean_and_tokenize(summary_b)
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
    # (格式化资料逻辑不变)
    basic_info, optional_info = user.get('basicInfo', {}), user.get('optionalInfo', {})
    basic_str = f"搭子类型: {basic_info.get('primaryIntent', '未填写')}, 地域: {basic_info.get('region', '未填写')}, 性别: {basic_info.get('gender', '未填写')}"
    optional_str = f"年龄: {optional_info.get('age', '未填写')}, 学历: {optional_info.get('education', '未填写')}, 星座: {optional_info.get('zodiac', '未填写')}, MBTI: {optional_info.get('mbti', '未填写')}, 爱好: {', '.join(optional_info.get('hobbies', []))}"
    open_answers = user.get('openAnswers', {})
    open_str = ', '.join([f"{q}: {a}" for q, a in open_answers.items() if a])
    if open_str: open_str = f"开放性回答: {open_str}"
    partner_expectations = user.get('partnerExpectations', '无明确要求')
    bio_summary = user.get('UserBioSummary', '无详细自述')
    return f"[基础信息] {basic_str}\n[可选信息] {optional_str}\n[开放回答] {open_str}\n[对搭子期望] {partner_expectations}\n[深度自述] {bio_summary}"


def is_base64_image(data):
    return isinstance(data, str) and (
            data.startswith('data:image/jpeg;base64,') or data.startswith('data:image/png;base64,'))


def convert_base64_to_part(base64_str):
    if base64_str.startswith('data:'):
        mime_type = base64_str.split(';')[0].split(':')[1]
        data = base64_str.split(',')[1]
        return {"inlineData": {"mimeType": mime_type, "data": data}}
    raise ValueError("Invalid Base64 string format.")


# ----------------------------------------------------
# --- 新增 API：共鸣历史记录和点赞 ---
# ----------------------------------------------------

@app.route('/resonance_history/toggle_like', methods=['POST'])
def toggle_like():
    db = get_db()
    if db is None: return jsonify({"error": "数据库连接失败"}), 500

    data = request.get_json()
    user_id = data.get('user_id')  # 发起点赞的人
    target_user_id = data.get('target_user_id')  # 被点赞的人
    match_content = data.get('match_content', '')  # 共鸣内容片段（用于唯一标识）
    target_display_name = data.get('target_display_name', '未知伙伴')

    if not all([user_id, target_user_id, match_content]):
        return jsonify({"message": "缺少必要的参数"}), 400

    # 查找发起点赞者的昵称
    user_profile = get_user_profile(user_id)
    user_display_name = user_profile.get('displayName') or user_profile.get('basicInfo', {}).get(
        'displayName') or f"用户_{user_id[:4]}"

    # 使用内容片段作为唯一标识的一部分，避免重复记录
    query = {
        'user_id': user_id,
        'target_user_id': target_user_id,
        'match_content_snippet': match_content
    }

    existing_record = db.resonance_history.find_one(query)

    if existing_record:
        # 取消点赞 (Delete)
        db.resonance_history.delete_one(query)
        app.logger.info(f"Resonance Like: {user_id} unliked {target_user_id}")
        return jsonify({"success": True, "action": "unliked"}), 200
    else:
        # 点赞 (Insert)
        record = {
            **query,
            'user_display_name': user_display_name,
            'target_display_name': target_display_name,
            'timestamp': time.time()
        }
        db.resonance_history.insert_one(record)
        app.logger.info(f"Resonance Like: {user_id} liked {target_user_id}")
        return jsonify({"success": True, "action": "liked"}), 201


@app.route('/resonance_history/get_liked_by_me', methods=['GET'])
def get_liked_by_me():
    db = get_db()
    if db is None: return jsonify({"error": "数据库连接失败"}), 500
    user_id = request.headers.get('X-User-Id')
    if not user_id: return jsonify({"message": "缺少用户ID头部信息"}), 400

    # 查找我点赞过的人 (user_id 是发起点赞的人)
    history = list(db.resonance_history.find({'user_id': user_id}).sort('timestamp', -1))

    # 格式化时间并转换 ObjectId
    result_list = []
    for item in history:
        item['_id'] = str(item['_id'])
        item['date'] = time.strftime('%Y-%m-%d %H:%M', time.localtime(item['timestamp']))
        result_list.append(item)

    return jsonify(result_list), 200


@app.route('/resonance_history/get_liked_me', methods=['GET'])
def get_liked_me():
    db = get_db()
    if db is None: return jsonify({"error": "数据库连接失败"}), 500
    user_id = request.headers.get('X-User-Id')
    if not user_id: return jsonify({"message": "缺少用户ID头部信息"}), 400

    # 查找点赞过我的人 (target_user_id 是我)
    history = list(db.resonance_history.find({'target_user_id': user_id}).sort('timestamp', -1))

    # 格式化时间并转换 ObjectId
    result_list = []
    for item in history:
        item['_id'] = str(item['_id'])
        item['date'] = time.strftime('%Y-%m-%d %H:%M', time.localtime(item['timestamp']))
        result_list.append(item)

    return jsonify(result_list), 200


# ----------------------------------------------------
# --- 现有 API 路由 (保持不变) ---
# ----------------------------------------------------

@app.route('/auth', methods=['POST'])
def handle_auth():
    db = get_db()
    if db is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    data = request.get_json()
    action, email, password, userId = data.get('action'), data.get('email'), data.get('password'), data.get('userId')
    if not all([action, email, password, userId]): return jsonify({"message": "缺少必要的认证信息"}), 400
    password_hash = base64.b64encode(password.encode()).decode()
    if action == 'register':
        if get_user_auth(email): return jsonify({"error": "该邮箱已被注册"}), 409
        if not save_user_auth(userId, email, password_hash): return jsonify({"error": "认证信息保存失败"}), 500
        initial_profile = json.loads(data.get('initialProfile', '{}'))
        if initial_profile and not save_user_profile(initial_profile): return jsonify(
            {"error": "初始资料保存失败"}), 500
        return jsonify({"success": True, "userId": userId, "profile": initial_profile}), 201
    elif action == 'login':
        user_auth = get_user_auth(email)
        if user_auth and user_auth['passwordHash'] == password_hash:
            profile = get_user_profile(user_auth['userId'])
            return jsonify({"success": True, "userId": user_auth['userId'], "profile": profile}), 200
        else:
            return jsonify({"error": "邮箱或密码错误"}), 401
    return jsonify({"message": "不支持的操作类型"}), 400


@app.route('/profile', methods=['GET', 'POST'])
def profile_management():
    if get_db() is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    userId = request.headers.get('X-User-Id')
    if not userId: return jsonify({"message": "缺少用户ID头部信息"}), 400
    if request.method == 'GET':
        profile = get_user_profile(userId)
        if profile is None: return jsonify({"message": "用户资料未找到"}), 404
        return jsonify(profile), 200
    elif request.method == 'POST':
        profile_data = request.get_json()
        if not profile_data or profile_data.get('userId') != userId: return jsonify(
            {"message": "资料格式错误或用户ID不匹配"}), 400
        if save_user_profile(profile_data):
            return jsonify({"message": "资料保存成功"}), 200
        else:
            return jsonify({"message": "资料保存失败，请检查数据库写入权限"}), 500
    return jsonify({"message": "不支持的请求方法"}), 405


@app.route('/profiles', methods=['GET'])
def get_profiles():
    if get_db() is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    current_userId = request.headers.get('X-User-Id')
    if not current_userId: return jsonify({"message": "缺少用户ID头部信息"}), 400
    profiles_list = get_all_profiles(current_userId)
    return jsonify(profiles_list), 200


@app.route('/generate_guidance', methods=['POST'])
def generate_guidance():
    if get_db() is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    if GEMINI_API_KEY == "geminikey": return jsonify(
        {"message": "Gemini API Key 未配置，无法生成提示！"}), 500
    data = request.get_json()
    buddy_type = data.get('buddyType', '通用')
    system_instruction = f"""你是一位专业的伙伴匹配顾问。你的任务是根据用户想寻找的特定搭子类型，提供一段简短、专业且极具针对性的填写指导文本。指导文本必须是一个**单一的、流畅的段落**，不超过150字。"""
    user_query = f"请根据用户希望寻找的搭子类型：'{buddy_type}'，生成一段专业的填写指导文本。"
    payload = {"contents": [{"parts": [{"text": user_query}]}],
               "systemInstruction": {"parts": [{"text": system_instruction}]}}
    try:
        llm_response = call_gemini_api(payload)
        guidance_text = llm_response['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"guidance": guidance_text}), 200
    except Exception as e:
        app.logger.error(f"Dynamic guidance generation failed: {e}")
        return jsonify({"message": "动态提示生成失败，请稍后重试。"}), 500


@app.route('/batch_score', methods=['POST'])
def batch_score():
    db = get_db()
    if db is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    if GEMINI_API_KEY == "geminikey": return jsonify(
        {"message": "GemINI API Key 未配置，无法生成提示！"}), 500
    data = request.get_json()
    user_a, users_b, match_mode = data.get('userA', {}), data.get('usersB', []), data.get('matchMode', 'similarity')
    if not user_a or not users_b: return jsonify({"message": "缺少用户资料进行批量评分"}), 400

    all_profiles_prompt = ""
    user_a_profile = format_profile(user_a)
    profiles_map = {}
    for user_b in users_b:
        profile_b = format_profile(user_b)
        all_profiles_prompt += f"\n--- 用户 B ({user_b['userId']}) ---\n{profile_b}"
        profiles_map[user_b['userId']] = user_b

    system_instruction_batch = f"""
    你是一个顶级的伙伴匹配专家。你的任务是快速评估发起匹配的用户 (User A) 与提供的批量用户列表 (Users B) 的匹配度。
    - **模式：** {match_mode} 匹配。如果是 'complementary'，请注重互补潜力。
    - **输出：** 必须严格返回一个 JSON 数组，包含每个用户的匹配得分和等级。
    - **跳过详细理由：** 只返回分数和等级。
    """
    user_query = f"""
    发起匹配者 (User A) 资料:\n{user_a_profile}\n\n
    请评估 User A 与以下 {len(users_b)} 位用户的匹配度。对于每一位用户 B，请给出其 userId，并给出主观评分和等级。

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
                user_b_summary = profiles_map[user_b_id].get('UserBioSummary', '')
                user_a_summary = user_a.get('UserBioSummary', '')
                objective_overlap_score = calculate_keyword_overlap(user_a_summary, user_b_summary)
                result['objectiveOverlapScore'] = objective_overlap_score
                final_results_with_objective.append(result)
            else:
                result['objectiveOverlapScore'] = 0
                final_results_with_objective.append(result)
        return jsonify(final_results_with_objective), 200
    except Exception as e:
        app.logger.error(f"Batch scoring failed: {e}")
        return jsonify({"message": f"批量预评分失败: {e}"}), 500


@app.route('/match', methods=['POST'])
def match_users():
    if get_db() is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    if GEMINI_API_KEY == "geminikey": return jsonify(
        {"message": "GemINI API Key 未配置！"}), 500
    data = request.get_json()
    user_a, user_b, match_mode = data.get('userA', {}), data.get('userB', {}), data.get('matchMode', 'similarity')

    summary_a, summary_b = user_a.get('UserBioSummary', ''), user_b.get('UserBioSummary', '')
    objective_overlap_score = calculate_keyword_overlap(summary_a, summary_b)

    profile_a, profile_b = format_profile(user_a), format_profile(user_b)

    if match_mode == 'complementary':
        system_instruction = f"""你是一个顶级的、专注于**互补性**的伙伴匹配系统专家。你的核心任务是评估两个用户的资料，重点判断他们在**性格、技能、作息、生活态度**上的互补潜力。- **评估重心：** 互补性应占总评分的 70% 权重。重叠度分数 ({objective_overlap_score}%) 仅作为次要参考。- **评分标准：** 给出 0 到 100 分的匹配得分。- **重点分析：** 详细解释他们如何能够互相弥补不足、拓宽视野，并重点列出'互补潜力点'。"""
    else:
        system_instruction = f"""你是一个顶级的、专注于**相似性**的伙伴匹配系统专家。你的核心任务是评估两个用户的资料，重点判断他们在**意图、兴趣、习惯、价值观**上的重叠程度。- **评估重心：** 相似性应占总评分的 70% 权重。客观重叠度分数 ({objective_overlap_score}%) 是重要参考。- **评分标准：** 给出 0 到 100 分的匹配得分。- **重点分析：** 详细解释他们有哪些共同之处、共同话题，并重点列出'重叠契合点'。"""

    user_query = f"""请评估以下两位用户的匹配度，并给出评分和详细理由。本次匹配的客观关键词重叠度是：{objective_overlap_score}%。\n\n### 用户 A 资料 (发起匹配者)\n{profile_a}\n\n### 用户 B 资料 (待匹配用户)\n{profile_b}\n\n请严格根据你的系统指令，输出最终的 JSON 结果。"""

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
        match_data = json.loads(json_str)
        return jsonify({**match_data, "objectiveOverlapScore": objective_overlap_score, "matchMode": match_mode}), 200
    except (ConnectionError, IndexError, KeyError, json.JSONDecodeError) as e:
        app.logger.error(f"Processing or API call failed: {e}")
        return jsonify({"message": f"LLM 匹配处理失败，请检查 API 或返回格式: {e}"}), 500


@app.route('/resonance_match', methods=['POST'])
def resonance_match():
    db = get_db()
    if db is None: return jsonify({"error": "数据库连接失败，请检查 MongoDB 服务！"}), 500
    if GEMINI_API_KEY == "geminikey": return jsonify(
        {"message": "Gemini API Key 未配置！"}), 500

    data = request.get_json()
    user_a = data.get('userA', {})
    user_a_content = data.get('content', '')

    if not user_a or not user_a_content: return jsonify({"message": "缺少用户资料或共鸣内容"}), 400

    user_a_profile_str = format_profile(user_a)
    profiles_to_analyze = []
    TOP_K_LIMIT = 5

    # ----------------------------------------------------
    # 阶段一：高效预筛选 (Python 内存向量相似度检索)
    # ----------------------------------------------------

    if not is_base64_image(user_a_content):
        try:
            app.logger.info("阶段一：开始生成查询 Embedding...")
            query_vector = call_gemini_embedding_api(user_a_content)
            app.logger.info("阶段一：在 Python 内存中计算所有用户的余弦相似度...")
            profiles_with_vectors = list(
                db.profiles.find({"userId": {"$ne": user_a['userId']}, "embedding_vector": {"$exists": True}}))

            scored_profiles = []
            for profile in profiles_with_vectors:
                similarity_score = calculate_cosine_similarity(profile['embedding_vector'], query_vector)
                profile['_id'] = str(profile['_id'])
                profile['similarity_score'] = similarity_score
                scored_profiles.append(profile)

            scored_profiles.sort(key=lambda p: p['similarity_score'], reverse=True)
            profiles_to_analyze = scored_profiles[:TOP_K_LIMIT]
            app.logger.info(f"阶段一完成：选中 {len(profiles_to_analyze)} 位候选人进行深度分析。")

        except ConnectionError as e:
            app.logger.error(f"Embedding API 连接失败，无法进行语义搜索。错误: {e}")
            profiles_to_analyze = get_all_profiles(user_a['userId'])[:TOP_K_LIMIT]
        except Exception as e:
            app.logger.error(f"Python 向量计算或数据库操作发生未知错误，回退到 Top 5 策略。错误: {e}")
            profiles_to_analyze = get_all_profiles(user_a['userId'])[:TOP_K_LIMIT]

    else:
        app.logger.info("阶段一：检测到图片输入，跳过 Embedding 预筛选，使用 Top 5 默认策略。")
        profiles_to_analyze = get_all_profiles(user_a['userId'])[:TOP_K_LIMIT]

    if not profiles_to_analyze: return jsonify({"message": "当前没有其他用户可供匹配"}), 500

    # ----------------------------------------------------
    # 阶段二：深度分析
    # ----------------------------------------------------

    # 🚨 Prompt 内容列表
    full_user_content_parts = []
    full_user_content_parts.append({"text": f"发起匹配者 (User A) 资料:\n{user_a_profile_str}\n\n"})

    # 处理内容 (图片/文本)
    if is_base64_image(user_a_content):
        try:
            image_part = convert_base64_to_part(user_a_content)
            full_user_content_parts.append(image_part)
            full_user_content_parts.append(
                {"text": "User A 提供了这张图片。请分析图片的**情感基调、审美风格、生活态度**。\n\n"})
        except ValueError as e:
            app.logger.error(f"Base64 image conversion error: {e}")
            return jsonify({"message": "图片格式错误"}), 400
    else:
        full_user_content_parts.append(
            {"text": f"User A 提供的共鸣文本：'{user_a_content}'。请分析这段话的**情绪基调、思想观点、表达风格**。\n\n"})

    # 添加所有待分析用户 B 的资料
    for i, profile_b in enumerate(profiles_to_analyze):
        temp_profile = profile_b.copy()
        temp_profile.pop('similarity_score', None)
        temp_profile.pop('embedding_vector', None)

        profile_b_str = format_profile(temp_profile)
        full_user_content_parts.append(
            {"text": f"### 候选用户 B ({i + 1}) ID: {profile_b['userId']} ###\n{profile_b_str}\n\n"})

    # 最终指令
    final_instruction_text = f"""
    请根据上述 User A 的内容和所有候选 User B 的资料，选出共鸣度最高的一位，并生成共鸣分析报告 JSON。
    """

    payload = {
        "contents": [
            {
                "parts": full_user_content_parts + [{"text": final_instruction_text}]
            }
        ],
        "systemInstruction": {
            "parts": [{
                "text": f"""
                你是一位顶级的多模态共鸣匹配专家。你的核心任务是：
                1. 深度解读发起匹配者 (User A) 的输入内容 (图片或文本) 的潜在风格、情感和价值观。
                2. 评估 User A 的共鸣内容与提供的 {len(profiles_to_analyze)} 位候选用户 (Users B) 资料之间的**共鸣程度**。
                3. 选择**共鸣度最高**且分数在 60 分以上的一位用户，并针对ta生成一份详细的《共鸣分析报告》。如果所有用户评分都低于 60 分，则返回评分最高但未匹配成功的结果。

                输出必须严格遵守提供的 JSON Schema。
                """
            }]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {"type": "OBJECT", "properties": {"matchedUserId": {"type": "STRING"},
                                                                "resonanceScore": {"type": "INTEGER"},
                                                                "targetDisplayName": {"type": "STRING"},
                                                                "resonanceRationale": {"type": "OBJECT", "properties": {
                                                                    "contentAnalysis": {"type": "STRING"},
                                                                    "matchPoints": {"type": "ARRAY",
                                                                                    "items": {"type": "STRING"}},
                                                                    "styleConsistency": {"type": "STRING"},
                                                                    "summary": {"type": "STRING"}},
                                                                                       "required": ["contentAnalysis",
                                                                                                    "matchPoints",
                                                                                                    "styleConsistency",
                                                                                                    "summary"]}},
                               "required": ["matchedUserId", "resonanceScore", "targetDisplayName",
                                            "resonanceRationale"]}
        }
    }

    try:
        app.logger.info("阶段二：调用 Gemini API 进行深度共鸣分析...")
        llm_response = call_gemini_api(payload)
        json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
        resonance_data = json.loads(json_str)

        matched_user_id = resonance_data.get('matchedUserId')
        all_profiles_list = get_all_profiles(user_a['userId'])
        matched_profile = next((p for p in all_profiles_list if p['userId'] == matched_user_id), None)

        if matched_profile:
            return jsonify({**resonance_data, "matchedProfile": matched_profile, "userAContent": user_a_content}), 200
        else:
            app.logger.warning(f"LLM 匹配到一个未知 ID: {matched_user_id}.")
            return jsonify({"message": f"共鸣分析成功，但LLM匹配到了一个未知用户ID: {matched_user_id}"}), 500

    except Exception as e:
        app.logger.error(f"阶段二深度分析失败: {e}")
        return jsonify({"message": f"共鸣匹配失败: API 调用失败: {e}"}), 500


@app.route('/', methods=['GET'])
def index():
    return jsonify({"message": "Flask后端服务运行中，请通过 /match 或 /resonance_match 接口访问。"}), 200


if __name__ == '__main__':
    # 初始化数据库连接 (在启动时完成)
    get_db_client()

    if GEMINI_API_KEY == "geminikey":
        print("\n!!! 警告: 请务必在代码中替换 GEMINI_API_KEY !!!\n")

    print("------------------------------------------------------------------")
    print(" Flask 后端启动成功！系统已启用 Embeddings 预筛选 (Python 内存模式)")
    print("------------------------------------------------------------------")
    app.run(debug=True, port=5001)