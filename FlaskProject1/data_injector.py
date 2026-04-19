# -*- coding: utf-8 -*-
import json
import time
from pymongo import MongoClient, errors
import random
import sys
import re

# --- MongoDB 配置 (必须与 backend_app.py 一致) ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "DapPeerMatchDB"
PROFILES_COLLECTION = "profiles"
USERS_COLLECTION = "users"

# --- 预设常量 (必须与前端 App.jsx 一致) ---
CITIES = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '不限地域']
AGE_OPTIONS = ['不限', '18-24岁', '25-30岁', '30-35岁', '35岁以上']
EDUCATION_OPTIONS = ['不限', '本科及以下', '硕士', '博士']
ZODIAC_SIGNS = ['不限', '白羊座', '金牛座', '双子座', '巨蟹座', '狮子座', '处女座', '天秤座', '天蝎座', '射手座',
                '摩羯座', '水瓶座', '双鱼座']
MBTI_TYPES = ['不限', 'ISTJ', 'ISFJ', 'INFJ', 'INTJ', 'ISTP', 'ISFP', 'INFP', 'INTP', 'ESTP', 'ESFP', 'ENFP', 'ENTP',
              'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ']
GENDER_OPTIONS = ['男', '女']  # 排除'不限'选项，实际用户资料只有男/女
INTERESTS = ['阅读', '徒步', '摄影', '健身', '音乐', '电影', '美食', '编程', '写作', '游戏', '旅行']

# 🚨 修复缺失的常量 🚨
OPEN_QUESTIONS_POOL = [
    "你最近在学习或尝试的新事物是什么？",
    "你最喜欢的城市是哪，为什么？",
    "你如何处理生活中的压力和情绪低谷？",
    "周末你最可能在做什么？请描述一下你的理想周末。",
    "你最难忘的一次经历是什么？",
    "你认为一段健康的伙伴关系最重要的因素是什么？",
    "你最喜欢吃什么？最擅长或最想学做什么菜？",
    "你有什么特别的、鲜为人知的爱好或技能？",
    "你对未来的学习或职业生涯有什么短期目标？",
]


# --- 虚拟数据生成函数 ---

def generate_profile(i):
    """生成一条随机的、结构完整的用户资料"""
    userId = f"user_{i:03d}_{random.randint(100, 999)}"
    email = f"user{i}@test.com"
    displayName = f"搭子_{i}"

    # 随机选择两个开放性问题
    selected_questions = random.sample(OPEN_QUESTIONS_POOL, 2)
    open_answers = {}

    # 生成回答
    q_data = {
        "你最喜欢的城市是哪，为什么？": "我喜欢杭州，因为它将现代科技和西湖美景完美融合。",
        "你如何处理生活中的压力和情绪低谷？": "我会通过长跑和听纯音乐来释放和调整情绪。",
        "周末你最可能在做什么？请描述一下你的理想周末。": "理想周末是周六去户外徒步，周日在家看书或编程。",
        "你对未来的学习或职业生涯有什么短期目标？": "短期目标是学习Go语言并完成一个开源项目。",
        "你最喜欢吃什么？最擅长或最想学做什么菜？": "我喜欢川菜，最想学做正宗的麻婆豆腐。"
    }

    for q in selected_questions:
        open_answers[q] = q_data.get(q, "这个问题对我来说很重要，但我还没有完美的答案。")

    # 随机生成爱好
    num_hobbies = random.randint(2, 5)
    hobbies = random.sample(INTERESTS, num_hobbies)

    # 随机生成搭子类型 (自由文本)
    buddy_type_pool = ["找学习搭子", "找健身搭子", "找编程伙伴", "找电影搭子", "找旅行伴侣"]
    primary_intent = random.choice(buddy_type_pool) + (" " + random.choice(CITIES))

    # 生成自述和期望
    UserBioSummary = f"我叫{displayName}，是一名{random.choice(EDUCATION_OPTIONS)}，坐标{random.choice(CITIES)}。我是一个{random.choice(MBTI_TYPES)}型人格。平时喜欢{', '.join(hobbies[:2])}。我正在努力{random.choice(['考证', '提升专业技能', '寻找新的投资方向'])}。"

    partnerExpectations = f"我希望我的搭子能有{random.choice(['积极乐观的性格', '严谨的自律精神', '开放的心态'])}。最好能和我一起{random.choice(hobbies)}，并在{primary_intent}方面有共同的目标。"

    return {
        "userId": userId,
        "email": email,
        "displayName": displayName,
        "timestamp": time.time() * 1000,  # 毫秒时间戳
        "UserBioSummary": UserBioSummary,
        "partnerExpectations": partnerExpectations,
        "basicInfo": {
            "primaryIntent": primary_intent,
            "gender": random.choice(GENDER_OPTIONS),
            "region": random.choice(CITIES),
            "displayName": displayName,
        },
        "optionalInfo": {
            "age": random.choice(AGE_OPTIONS),
            "education": random.choice(EDUCATION_OPTIONS),
            "zodiac": random.choice(ZODIAC_SIGNS),
            "mbti": random.choice(MBTI_TYPES),
            "hobbies": hobbies,
        },
        "openAnswers": open_answers,
        "selectedQuestions": selected_questions,
    }


def inject_data(num_profiles=50):
    """连接 MongoDB 并注入数据"""
    try:
        # 连接本地 MongoDB (必须在另一个终端中启动 mongod)
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[DB_NAME]

        profiles_collection = db[PROFILES_COLLECTION]
        users_collection = db[USERS_COLLECTION]

        # 清空旧数据 (可选，但推荐)
        profiles_collection.delete_many({})
        users_collection.delete_many({})

        profiles_to_insert = []
        users_to_insert = []

        for i in range(1, num_profiles + 1):
            profile = generate_profile(i)
            profiles_to_insert.append(profile)

            # 简化用户认证信息 (实际不会在这里创建)
            user_auth = {
                'userId': profile['userId'],
                'email': profile['email'],
                'passwordHash': "injected_test_hash_" + str(i),
                'createdAt': time.time()
            }
            users_to_insert.append(user_auth)

        # 批量插入
        profiles_collection.insert_many(profiles_to_insert)
        users_collection.insert_many(users_to_insert)

        print(f"\n--- 数据注入成功！已插入 {num_profiles} 条资料到 profiles 和 users 集合。---")
        client.close()

    except errors.ConnectionFailure:
        print("\n!!! 错误: 无法连接到本地 MongoDB 服务器。请确保在另一个终端运行: mongod --dbpath ~/mongodb_data/db")
        sys.exit(1)
    except Exception as e:
        print(f"\n!!! 注入过程中发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    inject_data(num_profiles=50)