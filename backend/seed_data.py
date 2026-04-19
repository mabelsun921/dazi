"""
数据库种子数据脚本
用于向MongoDB中注入测试用户和活动数据
"""

import os
import sys
import json
from datetime import datetime, timedelta
import random
from pymongo import MongoClient
from bson import ObjectId
import bcrypt

# MongoDB 配置
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = "buddy_matcher"

# 城市和区域数据
CITIES = {
    "北京": ["朝阳区", "海淀区", "东城区", "西城区", "丰台区", "通州区", "大兴区"],
    "上海": ["浦东新区", "黄浦区", "静安区", "徐汇区", "长宁区", "普陀区", "杨浦区"],
    "广州": ["天河区", "越秀区", "海珠区", "荔湾区", "白云区", "番禺区"],
    "深圳": ["南山区", "福田区", "罗湖区", "宝安区", "龙岗区", "龙华区"],
    "成都": ["锦江区", "青羊区", "金牛区", "武侯区", "成华区", "高新区"],
    "杭州": ["西湖区", "上城区", "拱墅区", "余杭区", "滨江区", "萧山区"],
    "武汉": ["江汉区", "武昌区", "洪山区", "青山区", "江岸区", "硚口区"],
    "西安": ["雁塔区", "碑林区", "莲湖区", "新城区", "未央区", "长安区"],
}

# MBTI类型
MBTI_TYPES = [
    "INTJ", "INTP", "ENTJ", "ENTP",
    "INFJ", "INFP", "ENFJ", "ENFP",
    "ISTJ", "ISFJ", "ESTJ", "ESFJ",
    "ISTP", "ISFP", "ESTP", "ESFP"
]

# 职业
OCCUPATIONS = [
    "软件工程师", "产品经理", "设计师", "教师", "医生", "律师",
    "会计", "销售", "市场", "运营", "HR", "金融分析师",
    "摄影师", "作家", "自媒体", "学生", "创业者", "自由职业者"
]

# 爱好
HOBBIES = [
    "篮球", "足球", "羽毛球", "乒乓球", "网球", "游泳", "跑步", "健身", "瑜伽", "登山",
    "读书", "电影", "音乐", "吉他", "钢琴", "绘画", "摄影", "写作", "烹饪", "烘焙",
    "旅游", "徒步", "露营", "滑雪", "冲浪", "潜水", "骑行", "跑步", "桌游", "电竞",
    "咖啡", "品茶", "红酒", "植物", "宠物", "舞蹈", "唱歌", "戏剧", "志愿者"
]

# AI标签
AI_TAGS = [
    "外向", "内向", "理性", "感性", "幽默", "认真", "随和", "独立",
    "创意", "稳重", "活力", "安静", "热情", "靠谱", "乐观", "踏实"
]

# 活动分类
ACTIVITY_CATEGORIES = ["运动", "娱乐", "学习", "社交", "美食", "旅行", "艺术", "游戏"]

# 分类对应的活动类型和标签（统一，且不重叠）
CATEGORY_ACTIVITY_TYPES = {
    "运动": ["篮球", "足球", "羽毛球", "乒乓球", "网球", "游泳", "跑步", "健身", "瑜伽", "登山", "骑行", "滑雪", "冲浪", "潜水"],
    "娱乐": ["电影", "音乐", "KTV", "唱歌", "咖啡", "品茶", "红酒", "舞蹈"],
    "学习": ["读书", "写作", "语言学习", "编程", "吉他", "钢琴", "绘画"],
    "社交": ["社交", "志愿者", "聚会", "交友", "相亲", "拓展人脉"],
    "美食": ["美食", "烹饪", "烘焙", "探店", "料理"],
    "旅行": ["旅游", "徒步", "露营", "滑雪", "冲浪", "潜水", "骑行", "城市探索", "自驾"],
    "艺术": ["摄影", "舞蹈", "戏剧", "插花", "陶艺"],
    "游戏": ["桌游", "电竞", "棋牌", "剧本杀", "密室逃脱", "手游"]
}

# 分类对应的标签（从活动类型中选取更具体的标签）
CATEGORY_TAGS = {
    "运动": ["篮球", "足球", "羽毛球", "乒乓球", "网球", "游泳", "跑步", "健身", "瑜伽", "登山", "骑行", "滑雪", "冲浪", "潜水"],
    "娱乐": ["电影", "音乐", "咖啡", "品茶", "红酒", "桌游", "电竞", "KTV", "唱歌", "舞蹈"],
    "学习": ["读书", "写作", "绘画", "摄影", "吉他", "钢琴", "语言学习", "编程", "烘焙", "烹饪"],
    "社交": ["社交", "志愿者", "聚会", "交友", "相亲", "拓展人脉"],
    "美食": ["美食", "烹饪", "烘焙", "咖啡", "探店", "料理", "品茶", "红酒"],
    "旅行": ["旅游", "徒步", "露营", "滑雪", "冲浪", "潜水", "骑行", "城市探索", "自驾"],
    "艺术": ["绘画", "摄影", "音乐", "吉他", "钢琴", "舞蹈", "戏剧", "写作", "插花", "陶艺"],
    "游戏": ["桌游", "电竞", "棋牌", "剧本杀", "密室逃脱", "游戏", "手游"]
}

# 活动标题模板
ACTIVITY_TITLES = [
    "周末{}局，来一起玩！",
    "{}爱好者聚会",
    "寻找一起{}的伙伴",
    "{}活动，欢迎加入",
    "周三晚{}小组",
    "周末{}交友会",
    "一起{}吧！",
    "{}兴趣小组招人",
    "{}体验活动",
    "每周{}日"
]

# 活动内容模板
ACTIVITY_CONTENTS = [
    "周末有空吗？一起出来{}吧！人数不限，地点可协商。",
    "组织一次{}活动，旨在认识新朋友，拓展社交圈。有兴趣的请报名！",
    "本人{}爱好者，想找几个志同道合的一起玩。要求：性格好，易相处。",
    "周三晚上组织{}活动，现在还差几个人满。有兴趣的私聊我。",
    "新建了一个{}群，欢迎各位感兴趣的朋友加入！每周固定活动。",
    "想找几个人一起{}，时间灵活，地点可以商量。有意向的留言。",
    "周末计划去{}，有没有一起的？可以在路上认识一下！",
    "组织{}活动，氛围轻松，适合新手小白参与，快来加入吧！",
    "有没有喜欢{}的朋友？一起组个局，玩得开心最重要！",
    "本人{}老手，带新手一起玩。有兴趣的私信详聊。"
]

def get_db():
    """获取数据库连接"""
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

def hash_password(password):
    """密码加密"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_seed_users(db, count=15):
    """创建种子用户"""
    print(f"正在创建 {count} 个用户...")
    
    users = []
    profiles = []
    
    # 先清空现有数据
    db.users.delete_many({})
    db.profiles.delete_many({})
    
    for i in range(count):
        # 生成用户ID
        user_id = ObjectId()
        
        # 随机选择城市
        city = random.choice(list(CITIES.keys()))
        district = random.choice(CITIES[city])
        
        # 随机选择爱好 (3-6个)
        user_hobbies = random.sample(HOBBIES, random.randint(3, 6))
        
        # 随机选择AI标签 (2-4个)
        user_ai_tags = random.sample(AI_TAGS, random.randint(2, 4))
        
        # 随机选择MBTI
        user_mbti = random.choice(MBTI_TYPES)
        
        # 随机选择职业
        user_occupation = random.choice(OCCUPATIONS)
        
        # 生成用户
        user = {
            "_id": user_id,
            "name": f"用户{i+1}",
            "email": f"user{i+1}@example.com",
            "password": hash_password("123456"),
            "created_at": datetime.now() - timedelta(days=random.randint(1, 90))
        }
        users.append(user)
        
        # 生成用户资料
        profile = {
            "user_id": user_id,
            "name": f"用户{i+1}",
            "gender": random.choice(["男", "女"]),
            "age": random.randint(20, 45),
            "mbti": user_mbti,
            "occupation": user_occupation,
            "hobbies": user_hobbies,
            "personality": f"大家好，我是{i+1}号用户，{user_mbti}型人格，{user_occupation}，喜欢{user_hobbies[0]}和{user_hobbies[1]}。期待认识新朋友！",
            "location": {
                "city": city,
                "district": district
            },
            "privacy_settings": {
                "age_visible": True,
                "occupation_visible": True
            },
            "reputation": round(random.uniform(3.5, 5.0), 1),
            "ai_tags": user_ai_tags,
            "created_at": datetime.now() - timedelta(days=random.randint(1, 90)),
            "updated_at": datetime.now() - timedelta(days=random.randint(0, 30))
        }
        profiles.append(profile)
    
    # 插入用户
    db.users.insert_many(users)
    print(f"✓ 已插入 {len(users)} 个用户")
    
    # 插入用户资料
    db.profiles.insert_many(profiles)
    print(f"✓ 已插入 {len(profiles)} 个用户资料")
    
    return users, profiles

def create_seed_activities(db, users, count=30):
    """创建种子活动"""
    print(f"正在创建 {count} 个活动...")
    
    # 清空现有活动
    db.activities.delete_many({})
    
    activities = []
    
    for i in range(count):
        # 随机选择发起者
        user = random.choice(users)
        
        # 随机选择城市
        city = random.choice(list(CITIES.keys()))
        district = random.choice(CITIES[city])
        
        # 随机选择分类
        category = random.choice(ACTIVITY_CATEGORIES)
        
        # 根据分类选择对应的活动类型
        activity_type = random.choice(CATEGORY_ACTIVITY_TYPES[category])
        
        # 生成标题
        title_template = random.choice(ACTIVITY_TITLES)
        title = title_template.format(activity_type)
        
        # 生成内容
        content_template = random.choice(ACTIVITY_CONTENTS)
        content = content_template.format(activity_type)
        
        # 根据分类生成对应的标签
        tags = random.sample(CATEGORY_ACTIVITY_TYPES[category], random.randint(2, 4))
        
        # 生成活动时间 (未来1-30天内)
        days_offset = random.randint(1, 30)
        activity_time = datetime.now() + timedelta(days=days_offset, hours=random.randint(9, 20))
        
        # 生成活动
        activity = {
            "user_id": user["_id"],
            "title": title,
            "content": content,
            "category": category,
            "location": {
                "city": city,
                "district": district,
                "address": f"{city}{district}某体育馆/咖啡馆/书店"
            },
            "time": activity_time,
            "requirements": f"性格好，易相处，有{activity_type}经验者优先",
            "tags": tags,
            "max_participants": random.randint(3, 15),
            "status": "ongoing",
            "participants": [user["_id"]],  # 发起者默认参与
            "created_at": datetime.now() - timedelta(days=random.randint(0, 7))
        }
        activities.append(activity)
    
    # 插入活动
    db.activities.insert_many(activities)
    print(f"✓ 已插入 {len(activities)} 个活动")
    
    return activities

def create_seed_applications(db, users, activities):
    """创建一些活动申请"""
    print("正在创建活动申请...")
    
    # 清空现有申请
    db.applications.delete_many({})
    
    applications = []
    
    # 为部分活动创建申请
    for activity in activities[:15]:  # 前15个活动
        # 随机选择1-3个申请者
        num_applicants = random.randint(1, 3)
        potential_applicants = [u for u in users if u["_id"] != activity["user_id"]]
        
        if len(potential_applicants) >= num_applicants:
            applicants = random.sample(potential_applicants, num_applicants)
            
            for applicant in applicants:
                # 随机决定状态
                status = random.choice(["pending", "pending", "approved"])  # 大部分是pending
                
                application = {
                    "activity_id": activity["_id"],
                    "user_id": applicant["_id"],
                    "message": f"你好，我对{activity['title']}很感兴趣，希望能加入！",
                    "status": status,
                    "created_at": datetime.now() - timedelta(days=random.randint(0, 3))
                }
                applications.append(application)
                
                # 如果批准了，加入参与者
                if status == "approved":
                    if "participants" not in activity:
                        activity["participants"] = []
                    if applicant["_id"] not in activity["participants"]:
                        activity["participants"].append(applicant["_id"])
    
    # 插入申请
    if applications:
        db.applications.insert_many(applications)
    
    # 更新活动的参与者
    for activity in activities:
        db.activities.update_one(
            {"_id": activity["_id"]},
            {"$set": {"participants": activity.get("participants", [])}}
        )
    
    print(f"✓ 已插入 {len(applications)} 个活动申请")

def create_seed_reviews(db, users):
    """创建一些用户评价"""
    print("正在创建用户评价...")
    
    # 清空现有评价
    db.reviews.delete_many({})
    
    reviews = []
    
    # 为部分用户创建评价
    for user in users[:10]:  # 为前10个用户创建评价
        # 随机选择3-8个评价者
        num_reviewers = random.randint(3, 8)
        potential_reviewers = [u for u in users if u["_id"] != user["_id"]]
        
        if len(potential_reviewers) >= num_reviewers:
            reviewers = random.sample(potential_reviewers, num_reviewers)
            
            for reviewer in reviewers:
                rating = random.randint(3, 5)
                comments = [
                    "人很好，活动组织得很棒！",
                    "性格开朗，容易相处。",
                    "非常靠谱，推荐！",
                    "体验不错，下次还一起玩。",
                    "氛围很好，期待下次合作。"
                ]
                
                review = {
                    "from_uid": reviewer["_id"],
                    "to_uid": user["_id"],
                    "activity_id": None,  # 可以后续关联到具体活动
                    "rating": rating,
                    "comment": random.choice(comments),
                    "created_at": datetime.now() - timedelta(days=random.randint(1, 30))
                }
                reviews.append(review)
    
    # 插入评价
    if reviews:
        db.reviews.insert_many(reviews)
    
    print(f"✓ 已插入 {len(reviews)} 个用户评价")

def print_summary(db):
    """打印数据统计"""
    print("\n" + "="*50)
    print("📊 数据库统计:")
    print("="*50)
    
    user_count = db.users.count_documents({})
    profile_count = db.profiles.count_documents({})
    activity_count = db.activities.count_documents({})
    application_count = db.applications.count_documents({})
    review_count = db.reviews.count_documents({})
    
    print(f"  👥 用户: {user_count}")
    print(f"  📋 用户资料: {profile_count}")
    print(f"  🎯 活动: {activity_count}")
    print(f"  📝 申请: {application_count}")
    print(f"  ⭐ 评价: {review_count}")
    print("="*50)
    print("\n✅ 种子数据创建完成！")
    print("\n测试账号:")
    for i in range(1, min(6, user_count + 1)):
        print(f"  邮箱: user{i}@example.com, 密码: 123456")

def main():
    """主函数"""
    print("🚀 开始创建种子数据...")
    print("="*50)
    
    try:
        db = get_db()
        
        # 创建用户和资料
        users, profiles = create_seed_users(db, count=15)
        
        # 创建活动
        activities = create_seed_activities(db, users, count=30)
        
        # 创建申请
        create_seed_applications(db, users, activities)
        
        # 创建评价
        create_seed_reviews(db, users)
        
        # 打印统计
        print_summary(db)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
