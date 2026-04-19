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

# --- Configuration ---
# 🚨 Placeholder: Please replace this with your real API Key
# IMPORTANT: It is strongly recommended to set this as an environment variable
# e.g., GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_FALLBACK_KEY_HERE")
GEMINI_API_KEY = "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0"  # Using your provided key
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
EMBEDDING_MODEL = "text-embedding-004"
GENERATIVE_MODEL = "gemini-1.5-flash"  # Use standard model name
GEMINI_API_URL = f"{GEMINI_API_BASE_URL}{GENERATIVE_MODEL}:generateContent"

# --- MongoDB Configuration ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "DapPeerMatchDB"
db_client = None

app = Flask(__name__)
CORS(app)


# --- Database Initialization and Connection ---
def get_db_client():
    global db_client
    if db_client is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Try to connect to the database
            client.admin.command('ping')
            db_client = client
            app.logger.info("--- Database Status: MongoDB Connection Successful ---")
        except errors.ConnectionFailure as e:
            app.logger.error(f"!!! FATAL ERROR: Cannot connect to MongoDB: {e}")
            return None
        except Exception as e:
            app.logger.error(f"!!! FATAL ERROR: Database initialization failed: {e}")
            return None
    return db_client


def get_db():
    client = get_db_client()
    return client[DB_NAME] if client else None


# --- MongoDB Helper Functions (CRUD) ---

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
        # 1. Concatenate text for Embedding
        bio = profile_data.get('UserBioSummary', '')
        expectations = profile_data.get('partnerExpectations', '')
        hobbies = ', '.join(profile_data.get('optionalInfo', {}).get('hobbies', []))
        text_to_embed = f"Bio: {bio}. Expectations: {expectations}. Hobbies: {hobbies}"

        embedding_vector = None
        if len(text_to_embed) > 50:  # Only embed if there is substantial text
            try:
                app.logger.info(f"DEBUG: Generating new embedding for user {profile_data['userId']}")
                embedding_vector = call_gemini_embedding_api(text_to_embed)
                profile_data['embedding_vector'] = embedding_vector
            except ConnectionError as e:
                app.logger.error(f"Error: Embedding API connection failed during profile save. Details: {e}")
            except Exception as e:
                app.logger.error(f"Error: Unknown error generating embedding during profile save. Details: {e}")
                pass  # Don't block profile save if embedding fails

        # 2. Execute profile save/update
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
            del profile['embedding_vector']  # Don't send vectors to client
        profile['_id'] = str(profile['_id'])
        profiles_list.append(profile)
    return profiles_list


# --- Helper Functions (LLM/Jieba/Base64/Embedding) ---
def calculate_keyword_overlap(summary_a, summary_b):
    # (Keyword overlap calculation logic remains unchanged)
    # This is fine, as it calculates overlap regardless of language.
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
    """Calculates cosine similarity between two vectors in Python."""
    if not vec_a or not vec_b:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def call_gemini_api(payload):
    """
    Calls the Gemini API (Generative Model) to send a request.
    """
    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0":  # Check for placeholder
        app.logger.error("!!! FATAL ERROR: Gemini API Key is not configured or is still the placeholder !!!")
        raise ConnectionError("Gemini API Key is not configured.")

    headers = {'Content-Type': 'application/json'}
    params = {'key': GEMINI_API_KEY}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, data=json.dumps(payload), timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Gemini API Request failed: {e}")
        raise ConnectionError(f"API call failed: {e}")


def call_gemini_embedding_api(text_to_embed):
    """Calls the Gemini Embedding API to get vector representation of text."""

    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0":  # Check for placeholder
        app.logger.error("!!! FATAL ERROR: Gemini API Key is not configured or is still the placeholder !!!")
        raise ConnectionError("Gemini API Key is not configured.")

    url = f"{GEMINI_API_BASE_URL}{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"

    payload = {"content": {"parts": [{"text": text_to_embed}]}}

    try:
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 400:
            app.logger.error(f"Embedding API 400 Error Details (Input: '{text_to_embed[:50]}...'): {response.text}")

        response.raise_for_status()

        result = response.json()
        embedding = result['embedding']['values']
        return embedding

    except requests.RequestException as e:
        app.logger.error(f"Embedding API call failed: {e}")
        raise ConnectionError(f"Embedding API call failed: {e}")


def format_profile(user):
    """Formats the user profile into an English string for the LLM."""
    basic_info, optional_info = user.get('basicInfo', {}), user.get('optionalInfo', {})

    basic_str = f"Partner Type: {basic_info.get('primaryIntent', 'Not specified')}, Region: {basic_info.get('region', 'Not specified')}, Gender: {basic_info.get('gender', 'Not specified')}"

    optional_str = f"Age: {optional_info.get('age', 'Not specified')}, Education: {optional_info.get('education', 'Not specified')}, Zodiac: {optional_info.get('zodiac', 'Not specified')}, MBTI: {optional_info.get('mbti', 'Not specified')}, Hobbies: {', '.join(optional_info.get('hobbies', []))}"

    open_answers = user.get('openAnswers', {})
    open_str = ', '.join([f"{q}: {a}" for q, a in open_answers.items() if a])
    if open_str:
        open_str = f"Open-ended Answers: {open_str}"

    partner_expectations = user.get('partnerExpectations', 'No specific requirements')
    bio_summary = user.get('UserBioSummary', 'No detailed bio')

    return f"[Basic Info] {basic_str}\n[Optional Info] {optional_str}\n[Open Answers] {open_str}\n[Partner Expectations] {partner_expectations}\n[Detailed Bio] {bio_summary}"


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
# --- NEW API: Resonance History and Likes ---
# ----------------------------------------------------

@app.route('/resonance_history/toggle_like', methods=['POST'])
def toggle_like():
    db = get_db()
    if db is None: return jsonify({"error": "Database connection failed"}), 500

    data = request.get_json()
    user_id = data.get('user_id')  # The user initiating the like
    target_user_id = data.get('target_user_id')  # The user being liked
    match_content = data.get('match_content', '')  # Resonance content snippet (for unique ID)
    target_display_name = data.get('target_display_name', 'Unknown Partner')

    if not all([user_id, target_user_id, match_content]):
        return jsonify({"message": "Missing required parameters"}), 400

    # Find the display name of the user who liked
    user_profile = get_user_profile(user_id)
    if not user_profile:
        user_display_name = f"User_{user_id[:4]}"
    else:
        user_display_name = user_profile.get('displayName') or user_profile.get('basicInfo', {}).get(
            'displayName') or f"User_{user_id[:4]}"

    # Use content snippet as part of the unique key to prevent duplicates
    query = {
        'user_id': user_id,
        'target_user_id': target_user_id,
        'match_content_snippet': match_content
    }

    existing_record = db.resonance_history.find_one(query)

    if existing_record:
        # Unlike (Delete)
        db.resonance_history.delete_one(query)
        app.logger.info(f"Resonance Like: {user_id} unliked {target_user_id}")
        return jsonify({"success": True, "action": "unliked"}), 200
    else:
        # Like (Insert)
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
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    user_id = request.headers.get('X-User-Id')
    if not user_id: return jsonify({"message": "Missing User-Id header"}), 400

    # Find users I have liked (user_id is the one who liked)
    history = list(db.resonance_history.find({'user_id': user_id}).sort('timestamp', -1))

    # Format timestamp and convert ObjectId
    result_list = []
    for item in history:
        item['_id'] = str(item['_id'])
        item['date'] = datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M')
        result_list.append(item)

    return jsonify(result_list), 200


@app.route('/resonance_history/get_liked_me', methods=['GET'])
def get_liked_me():
    db = get_db()
    if db is None: return jsonify({"error": "Database connection failed"}), 500
    user_id = request.headers.get('X-User-Id')
    if not user_id: return jsonify({"message": "Missing User-Id header"}), 400

    # Find users who liked me (target_user_id is me)
    history = list(db.resonance_history.find({'target_user_id': user_id}).sort('timestamp', -1))

    # Format timestamp and convert ObjectId
    result_list = []
    for item in history:
        item['_id'] = str(item['_id'])
        item['date'] = datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M')
        result_list.append(item)

    return jsonify(result_list), 200


# ----------------------------------------------------
# --- Existing API Routes ---
# ----------------------------------------------------

@app.route('/auth', methods=['POST'])
def handle_auth():
    db = get_db()
    if db is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    data = request.get_json()
    action, email, password, userId = data.get('action'), data.get('email'), data.get('password'), data.get('userId')
    if not all([action, email, password, userId]): return jsonify(
        {"message": "Missing required authentication information"}), 400

    # WARNING: Storing plain text b64 password is insecure. Use a proper hashing library like werkzeug.security.
    password_hash = base64.b64encode(password.encode()).decode()

    if action == 'register':
        if get_user_auth(email): return jsonify({"error": "This email is already registered"}), 409
        if not save_user_auth(userId, email, password_hash): return jsonify(
            {"error": "Failed to save authentication info"}), 500
        initial_profile = json.loads(data.get('initialProfile', '{}'))
        if initial_profile and not save_user_profile(initial_profile): return jsonify(
            {"error": "Failed to save initial profile"}), 500
        return jsonify({"success": True, "userId": userId, "profile": initial_profile}), 201

    elif action == 'login':
        user_auth = get_user_auth(email)
        if user_auth and user_auth['passwordHash'] == password_hash:
            profile = get_user_profile(user_auth['userId'])
            return jsonify({"success": True, "userId": user_auth['userId'], "profile": profile}), 200
        else:
            return jsonify({"error": "Incorrect email or password"}), 401

    return jsonify({"message": "Unsupported action type"}), 400


@app.route('/profile', methods=['GET', 'POST'])
def profile_management():
    db = get_db()
    if db is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    userId = request.headers.get('X-User-Id')
    if not userId: return jsonify({"message": "Missing User-Id header"}), 400

    if request.method == 'GET':
        profile = get_user_profile(userId)
        if profile is None: return jsonify({"message": "User profile not found"}), 404
        return jsonify(profile), 200

    elif request.method == 'POST':
        profile_data = request.get_json()
        if not profile_data or profile_data.get('userId') != userId: return jsonify(
            {"message": "Invalid data format or mismatched user ID"}), 400
        if save_user_profile(profile_data):
            return jsonify({"message": "Profile saved successfully"}), 200
        else:
            return jsonify({"message": "Profile save failed. Check database write permissions."}), 500

    return jsonify({"message": "Unsupported request method"}), 405


@app.route('/profiles', methods=['GET'])
def get_profiles():
    if get_db() is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    current_userId = request.headers.get('X-User-Id')
    if not current_userId: return jsonify({"message": "Missing User-Id header"}), 400
    profiles_list = get_all_profiles(current_userId)
    return jsonify(profiles_list), 200


@app.route('/generate_guidance', methods=['POST'])
def generate_guidance():
    if get_db() is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0": return jsonify(
        {"message": "Gemini API Key is not configured. Cannot generate hint."}), 500

    data = request.get_json()
    buddy_type = data.get('buddyType', 'General')

    system_instruction = f"""
    You are a professional partner matching consultant. Your task is to provide a brief, professional, and highly targeted guidance text based on the specific partner type the user is looking for. 
    The guidance text must be a **single, fluent paragraph** of no more than 150 words.
    The response must be in English.
    """
    user_query = f"Please generate a professional guidance text based on the partner type the user is looking for: '{buddy_type}'."

    payload = {"contents": [{"parts": [{"text": user_query}]}],
               "systemInstruction": {"parts": [{"text": system_instruction}]}}

    try:
        llm_response = call_gemini_api(payload)
        guidance_text = llm_response['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"guidance": guidance_text}), 200
    except Exception as e:
        app.logger.error(f"Dynamic guidance generation failed: {e}")
        return jsonify({"message": "Dynamic hint generation failed. Please try again later."}), 500


@app.route('/batch_score', methods=['POST'])
def batch_score():
    db = get_db()
    if db is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0": return jsonify(
        {"message": "Gemini API Key is not configured. Cannot generate scores."}), 500

    data = request.get_json()
    user_a, users_b, match_mode = data.get('userA', {}), data.get('usersB', []), data.get('matchMode', 'similarity')
    if not user_a or not users_b: return jsonify({"message": "Missing user data for batch scoring"}), 400

    all_profiles_prompt = ""
    user_a_profile = format_profile(user_a)  # This now returns English
    profiles_map = {}
    for user_b in users_b:
        profile_b = format_profile(user_b)  # This now returns English
        all_profiles_prompt += f"\n--- User B ({user_b['userId']}) ---\n{profile_b}"
        profiles_map[user_b['userId']] = user_b

    system_instruction_batch = f"""
    You are a top-tier partner matching expert. Your task is to quickly evaluate the match between the initiating user (User A) and a provided batch list of users (Users B).
    - **Mode:** {match_mode} match. If 'complementary', focus on complementary potential.
    - **Output:** Must strictly return a JSON array, containing each user's ID, a matchScore (0-100), and a matchLevel ("Excellent", "Good", "Fair", or "Poor").
    - **Language:** All output must be in English.
    - **Skip Detailed Rationale:** Only return userId, matchScore, and matchLevel.
    """
    user_query = f"""
    Initiating User (User A) Profile:\n{user_a_profile}\n\n
    Please evaluate the match between User A and the following {len(users_b)} users. For each User B, provide their userId, a subjective matchScore (0-100), and a matchLevel.

    {all_profiles_prompt}

    Please strictly follow your system instruction and output the final JSON array result.
    """

    # This schema matches the English frontend
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

        # Add objective scores
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
        return jsonify({"message": f"Batch pre-scoring failed: {e}"}), 500


@app.route('/match', methods=['POST'])
def match_users():
    if get_db() is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0": return jsonify(
        {"message": "Gemini API Key is not configured."}), 500

    data = request.get_json()
    user_a, user_b, match_mode = data.get('userA', {}), data.get('userB', {}), data.get('matchMode', 'similarity')

    summary_a, summary_b = user_a.get('UserBioSummary', ''), user_b.get('UserBioSummary', '')
    objective_overlap_score = calculate_keyword_overlap(summary_a, summary_b)

    profile_a, profile_b = format_profile(user_a), format_profile(user_b)  # These are now English

    if match_mode == 'complementary':
        system_instruction = f"""
        You are a top-tier partner matching expert focused on **complementarity**. Your core task is to evaluate two user profiles, focusing on their complementary potential in **personality, skills, habits, and life attitudes**.
        - **Focus:** Complementarity should account for 70% of the total score. The objective overlap score ({objective_overlap_score}%) is only a secondary reference.
        - **Scoring:** Provide a match score from 0 to 100.
        - **Analysis:** Explain in detail (in English) how they can complement each other and broaden their horizons, and specifically list 'complementaryPoints'.
        - **Language:** All output fields in the JSON must be in English.
        """
    else:  # Default to similarity
        system_instruction = f"""
        You are a top-tier partner matching expert focused on **similarity**. Your core task is to evaluate two user profiles, focusing on the overlap in their **intent, interests, habits, and values**.
        - **Focus:** Similarity should account for 70% of the total score. The objective overlap score ({objective_overlap_score}%) is an important reference.
        - **Scoring:** Provide a match score from 0 to 100.
        - **Analysis:** Explain in detail (in English) what they have in common and specifically list 'overlapPoints'.
        - **Language:** All output fields in the JSON must be in English.
        """

    user_query = f"""
    Please evaluate the match between the following two users, providing a score and detailed rationale. The objective keyword overlap for this match is: {objective_overlap_score}%.\n\n
    ### User A Profile (Initiator)\n{profile_a}\n\n
    ### User B Profile (Candidate)\n{profile_b}\n\n
    Please strictly follow your system instruction and output the final JSON result in English.
    """

    # This schema matches the English frontend
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
        return jsonify({"message": f"LLM match processing failed. Check API or return format: {e}"}), 500


@app.route('/resonance_match', methods=['POST'])
def resonance_match():
    db = get_db()
    if db is None: return jsonify({"error": "Database connection failed. Please check MongoDB service!"}), 500
    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0": return jsonify(
        {"message": "Gemini API Key is not configured."}), 500

    data = request.get_json()
    user_a = data.get('userA', {})
    user_a_content = data.get('content', '')

    if not user_a or not user_a_content: return jsonify({"message": "Missing user data or resonance content"}), 400

    user_a_profile_str = format_profile(user_a)  # Now in English
    profiles_to_analyze = []
    TOP_K_LIMIT = 5

    # ----------------------------------------------------
    # --- Stage 1: Efficient Pre-screening (Python In-Memory Vector Search) ---
    # ----------------------------------------------------

    if not is_base64_image(user_a_content):
        try:
            app.logger.info("Stage 1: Starting query embedding generation...")
            query_vector = call_gemini_embedding_api(user_a_content)
            app.logger.info("Stage 1: Calculating cosine similarity for all users in Python memory...")
            profiles_with_vectors = list(
                db.profiles.find({"userId": {"$ne": user_a['userId']}, "embedding_vector": {"$exists": True}}))

            scored_profiles = []
            for profile in profiles_with_vectors:
                similarity_score = calculate_cosine_similarity(profile.get('embedding_vector'), query_vector)
                profile['_id'] = str(profile['_id'])
                profile['similarity_score'] = similarity_score
                scored_profiles.append(profile)

            scored_profiles.sort(key=lambda p: p['similarity_score'], reverse=True)
            profiles_to_analyze = scored_profiles[:TOP_K_LIMIT]
            app.logger.info(f"Stage 1 Complete: Selected {len(profiles_to_analyze)} candidates for deep analysis.")

        except ConnectionError as e:
            app.logger.error(f"Embedding API connection failed, cannot perform semantic search. Error: {e}")
            profiles_to_analyze = get_all_profiles(user_a['userId'])[:TOP_K_LIMIT]
        except Exception as e:
            app.logger.error(f"Python vector calculation or DB error, falling back to Top 5 strategy. Error: {e}")
            profiles_to_analyze = get_all_profiles(user_a['userId'])[:TOP_K_LIMIT]

    else:
        app.logger.info(
            "Stage 1: Image input detected, skipping embedding pre-screening. Using Top 5 default strategy.")
        profiles_to_analyze = get_all_profiles(user_a['userId'])[:TOP_K_LIMIT]

    if not profiles_to_analyze: return jsonify({"message": "No other users are available to match at this time"}), 500

    # ----------------------------------------------------
    # --- Stage 2: Deep Analysis ---
    # ----------------------------------------------------

    full_user_content_parts = []
    full_user_content_parts.append({"text": f"Initiating User (User A) Profile:\n{user_a_profile_str}\n\n"})

    # Process content (Image/Text)
    if is_base64_image(user_a_content):
        try:
            image_part = convert_base64_to_part(user_a_content)
            full_user_content_parts.append(image_part)
            full_user_content_parts.append(
                {
                    "text": "User A provided this image. Please analyze its **emotional tone, aesthetic style, and life attitude**.\n\n"})
        except ValueError as e:
            app.logger.error(f"Base64 image conversion error: {e}")
            return jsonify({"message": "Invalid image format"}), 400
    else:
        full_user_content_parts.append(
            {
                "text": f"User A provided this resonance text: '{user_a_content}'. Please analyze its **emotional tone, viewpoint, and expression style**.\n\n"})

    # Add all candidate User B profiles
    for i, profile_b in enumerate(profiles_to_analyze):
        temp_profile = profile_b.copy()
        temp_profile.pop('similarity_score', None)  # Clean up helper fields
        temp_profile.pop('embedding_vector', None)

        profile_b_str = format_profile(temp_profile)  # Now in English
        full_user_content_parts.append(
            {"text": f"### Candidate User B ({i + 1}) ID: {profile_b['userId']} ###\n{profile_b_str}\n\n"})

    final_instruction_text = f"""
    Based on User A's content and all candidate User B profiles, select the one with the highest resonance and generate a resonance analysis report JSON in English.
    """

    # This schema matches the English frontend
    resonance_schema = {"type": "OBJECT", "properties": {"matchedUserId": {"type": "STRING"},
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
                        "required": ["matchedUserId", "resonanceScore", "targetDisplayName", "resonanceRationale"]}

    payload = {
        "contents": [
            {
                "parts": full_user_content_parts + [{"text": final_instruction_text}]
            }
        ],
        "systemInstruction": {
            "parts": [{
                "text": f"""
                You are a top-tier, multi-modal resonance matching expert. Your core tasks are:
                1. Deeply interpret the underlying style, emotion, and values of the initiating User A's input (image or text).
                2. Evaluate the **degree of resonance** between User A's content and the {len(profiles_to_analyze)} candidate users (Users B).
                3. Select the **one user** with the **highest resonance score** (must be above 60). If all users score below 60, return the highest-scoring user.
                4. Generate a detailed "Resonance Analysis Report" for the selected user. All text in the report must be in English.

                The output must strictly adhere to the provided JSON Schema.
                """
            }]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": resonance_schema
        }
    }

    try:
        app.logger.info("Stage 2: Calling Gemini API for deep resonance analysis...")
        llm_response = call_gemini_api(payload)
        json_str = llm_response['candidates'][0]['content']['parts'][0]['text']
        resonance_data = json.loads(json_str)

        matched_user_id = resonance_data.get('matchedUserId')

        # We need the full profile to send back, not the formatted string
        matched_profile = get_user_profile(matched_user_id)
        if matched_profile and 'embedding_vector' in matched_profile:
            del matched_profile['embedding_vector']  # Clean vector before sending

        if matched_profile:
            return jsonify({**resonance_data, "matchedProfile": matched_profile, "userAContent": user_a_content}), 200
        else:
            app.logger.warning(f"LLM matched an unknown ID: {matched_user_id}.")
            return jsonify({
                               "message": f"Resonance analysis successful, but LLM matched an unknown user ID: {matched_user_id}"}), 500

    except Exception as e:
        app.logger.error(f"Stage 2 deep analysis failed: {e}")
        return jsonify({"message": f"Resonance match failed: API call failed: {e}"}), 500


@app.route('/', methods=['GET'])
def index():
    return jsonify(
        {"message": "Flask backend service is running. Access via /match or /resonance_match endpoints."}), 200


if __name__ == '__main__':
    # Initialize database connection (on startup)
    get_db_client()

    if GEMINI_API_KEY == "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0":
        print("\n!!! WARNING: Please replace the placeholder GEMINI_API_KEY in the code !!!\n")

    print("------------------------------------------------------------------")
    print(" Flask Backend Started Successfully! System enabled with Embedding Pre-screening (Python Memory Mode)")
    print("------------------------------------------------------------------")
    app.run(debug=True, port=5001)