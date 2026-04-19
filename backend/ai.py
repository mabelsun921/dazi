import os
import requests
from dotenv import load_dotenv

load_dotenv()

# AI API configuration
AI_API_KEY = os.getenv('AI_API_KEY', '')
AI_API_URL = os.getenv('AI_API_URL', 'https://api.example.com/chat')

# Prompt templates for AI matching
MATCH_SCORE_PROMPT = """
You are a professional matchmaker AI. Your task is to calculate a compatibility score between two users based on their profiles.

User A Profile:
Gender: {gender_a}
MBTI: {mbti_a}
Occupation: {occupation_a}
Personality: {personality_a}
Location: {location_a}

User B Profile:
Gender: {gender_b}
MBTI: {mbti_b}
Occupation: {occupation_b}
Personality: {personality_b}
Location: {location_b}

Please calculate a compatibility score between 0 and 100, where 100 is a perfect match.
Consider the following factors:
1. MBTI compatibility
2. Personality similarity
3. Common interests (inferred from occupation and personality)
4. Location proximity

Return only the score as a number, no other text.
"""

MATCH_REPORT_PROMPT = """
You are a professional matchmaker AI. Your task is to generate a natural language report explaining why two users would be a good match.

User A Profile:
Gender: {gender_a}
MBTI: {mbti_a}
Occupation: {occupation_a}
Personality: {personality_a}
Location: {location_a}

User B Profile:
Gender: {gender_b}
MBTI: {mbti_b}
Occupation: {occupation_b}
Personality: {personality_b}
Location: {location_b}

Compatibility Score: {score}

Please generate a concise, friendly report (2-3 sentences) explaining the key reasons why these two users would be compatible.
Focus on their shared traits, complementary characteristics, and potential common interests.
"""

ACTIVITY_SCORE_PROMPT = """
You are a professional activity matcher AI. Your task is to calculate how well a user's profile matches a specific activity.

User Profile:
Gender: {gender}
MBTI: {mbti}
Occupation: {occupation}
Personality: {personality}
Location: {location}

Activity:
Title: {title}
Content: {content}
Category: {category}
Location: {activity_location}

Please calculate a match score between 0 and 100, where 100 is a perfect match.
Consider the following factors:
1. Interest alignment (based on personality and occupation)
2. Location proximity
3. Activity category relevance to the user's profile

Return only the score as a number, no other text.
"""

def get_ai_response(prompt):
    """
    Get response from AI API
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {AI_API_KEY}'
    }
    data = {
        'prompt': prompt,
        'temperature': 0.7,
        'max_tokens': 100
    }
    
    try:
        response = requests.post(AI_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('response', '')
    except Exception as e:
        print(f"AI API error: {e}")
        # Return a default score in case of API failure
        return "50"

def calculate_match_score(profile_a, profile_b):
    """
    Calculate compatibility score between two profiles
    """
    prompt = MATCH_SCORE_PROMPT.format(
        gender_a=profile_a.get('gender', ''),
        mbti_a=profile_a.get('mbti', ''),
        occupation_a=profile_a.get('occupation', ''),
        personality_a=profile_a.get('personality', ''),
        location_a=f"{profile_a.get('location', {}).get('city', '')}-{profile_a.get('location', {}).get('district', '')}",
        gender_b=profile_b.get('gender', ''),
        mbti_b=profile_b.get('mbti', ''),
        occupation_b=profile_b.get('occupation', ''),
        personality_b=profile_b.get('personality', ''),
        location_b=f"{profile_b.get('location', {}).get('city', '')}-{profile_b.get('location', {}).get('district', '')}"
    )
    
    response = get_ai_response(prompt)
    try:
        score = float(response.strip())
        return min(max(score, 0), 100)  # Ensure score is between 0-100
    except:
        return 50  # Default score if parsing fails

def generate_match_report(profile_a, profile_b, score):
    """
    Generate match report between two profiles
    """
    prompt = MATCH_REPORT_PROMPT.format(
        gender_a=profile_a.get('gender', ''),
        mbti_a=profile_a.get('mbti', ''),
        occupation_a=profile_a.get('occupation', ''),
        personality_a=profile_a.get('personality', ''),
        location_a=f"{profile_a.get('location', {}).get('city', '')}-{profile_a.get('location', {}).get('district', '')}",
        gender_b=profile_b.get('gender', ''),
        mbti_b=profile_b.get('mbti', ''),
        occupation_b=profile_b.get('occupation', ''),
        personality_b=profile_b.get('personality', ''),
        location_b=f"{profile_b.get('location', {}).get('city', '')}-{profile_b.get('location', {}).get('district', '')}",
        score=score
    )
    
    return get_ai_response(prompt)

def calculate_activity_score(profile, activity):
    """
    Calculate match score between user profile and activity
    """
    prompt = ACTIVITY_SCORE_PROMPT.format(
        gender=profile.get('gender', ''),
        mbti=profile.get('mbti', ''),
        occupation=profile.get('occupation', ''),
        personality=profile.get('personality', ''),
        location=f"{profile.get('location', {}).get('city', '')}-{profile.get('location', {}).get('district', '')}",
        title=activity.get('title', ''),
        content=activity.get('content', ''),
        category=activity.get('category', ''),
        activity_location=f"{activity.get('location', {}).get('city', '')}-{activity.get('location', {}).get('district', '')}"
    )
    
    response = get_ai_response(prompt)
    try:
        score = float(response.strip())
        return min(max(score, 0), 100)  # Ensure score is between 0-100
    except:
        return 50  # Default score if parsing fails
