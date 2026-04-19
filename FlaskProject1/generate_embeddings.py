# generate_embeddings.py

import json
import os
from pymongo import MongoClient, errors
import requests
import time

# --- 配置 (请确保与 backend_app.py 中的配置一致) ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "DapPeerMatchDB"
# 🚨 替换为您的真实密钥
GEMINI_API_KEY = "AIzaSyDNM9hHmhUQk5Gf-UBfH962QgxIfWOdKm0"
EMBEDDING_MODEL = "text-embedding-004"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"


# --- 配置结束 ---

def call_gemini_embedding_api(text_to_embed):
    """调用 Embedding API"""
    url = f"{GEMINI_API_BASE_URL}{EMBEDDING_MODEL}:embedContent?key={GEMINI_API_KEY}"
    payload = {
        "content": {
            "parts": [{"text": text_to_embed}]
        }
    }

    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    result = response.json()
    return result['embedding']['values']


def generate_and_store_embeddings():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        profiles_collection = db['profiles']

        print("--- MongoDB 连接成功。开始处理用户资料... ---")

        # 查找所有没有 'embedding_vector' 字段的用户
        profiles_cursor = profiles_collection.find({'embedding_vector': {'$exists': False}})

        count = 0
        for profile in profiles_cursor:
            user_id = profile['userId']

            # 拼接用于生成 Embedding 的文本
            bio = profile.get('UserBioSummary', '')
            expectations = profile.get('partnerExpectations', '')
            hobbies = ', '.join(profile.get('optionalInfo', {}).get('hobbies', []))

            text_to_embed = f"Bio: {bio}. Expectations: {expectations}. Hobbies: {hobbies}"

            if len(text_to_embed) < 50:
                print(f"跳过用户 {user_id}：资料太少。")
                continue

            try:
                # 1. 调用 API 生成向量
                embedding_vector = call_gemini_embedding_api(text_to_embed)

                # 2. 存储向量回 MongoDB
                profiles_collection.update_one(
                    {'_id': profile['_id']},
                    {'$set': {'embedding_vector': embedding_vector}}
                )
                print(f"✅ 成功生成并存储 {user_id} 的 Embedding。")
                count += 1

                # 休息一下，避免触发 API 速率限制
                time.sleep(0.5)

            except Exception as api_e:
                print(f"❌ API 调用失败，跳过 {user_id}：{api_e}")
                time.sleep(1)  # 失败时多等会儿

        print(f"\n--- 批量 Embedding 任务完成。共处理 {count} 个新用户。 ---")

    except errors.ConnectionFailure:
        print(f"!!! 致命错误: 无法连接到 MongoDB。请确保 mongod 服务正在运行。")
    except Exception as e:
        print(f"!!! 发生未知错误: {e}")


if __name__ == '__main__':
    generate_and_store_embeddings()