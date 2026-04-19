# inject_mock_data.py
# 目标：生成20组详细、前后一致的用户数据，并注入到 MongoDB 的 users 和 profiles 集合中。

import os
import json
import time
import base64
from pymongo import MongoClient, errors

# --- 配置 (请确保与 backend_app.py 中的配置一致) ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "DapPeerMatchDB"
# 统一密码 '123456' 的 Base64 编码
PASSWORD_HASH = base64.b64encode("123456".encode()).decode()


# --- 配置结束 ---

# --- 数据库连接函数 (位于顶部，确保可见性) ---
def get_db():
    try:
        # 尝试连接 MongoDB
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # 尝试执行 ping 命令确认连接
        client.admin.command('ping')
        return client[DB_NAME]
    except errors.ConnectionFailure:
        print(f"!!! 致命错误: 无法连接到 MongoDB: {MONGO_URI}")
        return None


# --- 生成用户数据函数 ---
def generate_mock_data():
    """生成20个具有完整且一致资料的用户数据，并执行注入"""

    # 模拟用户列表 (包含 user_id, 昵称, email_suffix 的基础信息)
    mock_users = [
        {"id": "user_yiran_01", "name": "叶依燃", "email_suffix": "yiran"},
        {"id": "user_chen_02", "name": "陈默", "email_suffix": "chenmo"},
        {"id": "user_xiaoyue_03", "name": "林小悦", "email_suffix": "xiaoyue"},
        {"id": "user_feng_04", "name": "高风", "email_suffix": "gaofeng"},
        {"id": "user_zhao_05", "name": "赵晴", "email_suffix": "zhaoqing"},
        {"id": "user_rui_06", "name": "孙睿", "email_suffix": "sunrui"},
        {"id": "user_wen_07", "name": "李文", "email_suffix": "liwen"},
        {"id": "user_hui_08", "name": "张慧", "email_suffix": "zhanghui"},
        {"id": "user_yu_09", "name": "王宇", "email_suffix": "wangyu"},
        {"id": "user_lan_10", "name": "蓝天", "email_suffix": "lantian"},
        {"id": "user_xu_11", "name": "徐来", "email_suffix": "xulai"},
        {"id": "user_ding_12", "name": "丁宁", "email_suffix": "dingning"},
        {"id": "user_hao_13", "name": "刘昊", "email_suffix": "liuhao"},
        {"id": "user_jing_14", "name": "杨静", "email_suffix": "yangjing"},
        {"id": "user_min_15", "name": "周敏", "email_suffix": "zhoumin"},
        {"id": "user_qi_16", "name": "钱琪", "email_suffix": "qianqi"},
        {"id": "user_bo_17", "name": "吴波", "email_suffix": "wubo"},
        {"id": "user_can_18", "name": "何灿", "email_suffix": "hecan"},
        {"id": "user_fei_19", "name": "郑飞", "email_suffix": "zhengfei"},
        {"id": "user_tao_20", "name": "郭涛", "email_suffix": "guotao"},
    ]

    # 将基础信息转换为字典，方便通过 userId 查找
    user_map = {user['id']: user for user in mock_users}

    # --- 详细用户资料列表 (言行一致是重点) ---
    data_templates = [
        {  # 01: 学习型、理性、ISTJ
            "userId": "user_yiran_01", "displayName": "叶依燃", "gender": "女", "region": "上海",
            "primaryIntent": "学习搭子",
            "UserBioSummary": "正在备考注册会计师，生活比较规律和自律。空闲时间会去健身房。我希望我的搭子能给我带来高效的学习氛围，并能分享一些压力管理的技巧。",
            "partnerExpectations": "寻找一位在上海的CPA或金融领域的学习搭子，最好是ISTJ或INTJ，注重效率和规划。",
            "optionalInfo": {"age": "28-35岁", "education": "硕士", "zodiac": "摩羯座", "mbti": "ISTJ",
                             "hobbies": ["健身", "CPA备考", "极简主义"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "深入研究数据分析，希望将其运用到财务建模中。",
                            "你最喜欢的城市是哪，为什么？": "上海，节奏快且专业氛围浓厚，适合事业发展。"},
        },
        {  # 02: 深度交流、内向、INFJ
            "userId": "user_chen_02", "displayName": "陈默", "gender": "男", "region": "北京",
            "primaryIntent": "灵魂搭子",
            "UserBioSummary": "一个典型的INFJ，喜欢在深夜思考人生的意义，对哲学、历史和独立电影充满热情。我不喜欢无效社交，更偏爱深度的一对一交流。",
            "partnerExpectations": "在北京，寻找一位思维敏捷、情感细腻的灵魂搭子，能接受我偶尔的沉默和突如其来的深刻话题。",
            "optionalInfo": {"age": "30-35岁", "education": "博士", "zodiac": "双鱼座", "mbti": "INFJ",
                             "hobbies": ["哲学阅读", "独立电影", "写作"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "尝试用油画表达内心的复杂情感。",
                            "你最喜欢的城市是哪，为什么？": "柏林，历史的厚重感和自由的艺术氛围令人着迷。"},
        },
        {  # 03: 户外运动、ENTP、活泼
            "userId": "user_xiaoyue_03", "displayName": "林小悦", "gender": "女", "region": "广州",
            "primaryIntent": "运动搭子",
            "UserBioSummary": "ENTP 的外向探索者，闲不下来！周末不是在爬白云山，就是在尝试新的攀岩馆。我享受挑战自我和流汗的感觉。",
            "partnerExpectations": "在广州寻找一位体力充沛、充满活力的运动搭子，最好能和我一起挑战重装徒步或水上运动。",
            "optionalInfo": {"age": "18-24岁", "education": "本科及以下", "zodiac": "射手座", "mbti": "ENTP",
                             "hobbies": ["攀岩", "徒步", "探店", "跳舞"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "潜水，想去体验水下的安静世界。",
                            "你最喜欢的城市是哪，为什么？": "里斯本，充满了阳光和坡道，非常适合户外运动。"},
        },
        {  # 04: 科技前沿、INTJ、冷静
            "userId": "user_feng_04", "displayName": "高风", "gender": "男", "region": "深圳",
            "primaryIntent": "技术搭子",
            "UserBioSummary": "资深软件工程师，INTJ。对 AI 和区块链的前沿技术保持狂热，大部分时间都在研究新代码。我说话直接，只对逻辑和效率感兴趣。",
            "partnerExpectations": "寻找能在深圳一起讨论技术、攻克难题的搭子。必须是同领域的技术爱好者，思维要严谨。",
            "optionalInfo": {"age": "25-30岁", "education": "硕士", "zodiac": "天蝎座", "mbti": "INTJ",
                             "hobbies": ["编程", "科幻小说", "无人机"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "量子计算的入门理论。",
                            "你最喜欢的城市是哪，为什么？": "旧金山，那里是科技创新的心脏。"},
        },
        {  # 05: 艺术设计、ISFP、感性
            "userId": "user_zhao_05", "displayName": "赵晴", "gender": "女", "region": "成都",
            "primaryIntent": "艺术搭子",
            "UserBioSummary": "一名独立插画师，ISFP。我的世界充满了色彩和音乐。喜欢一切美的事物，享受慢节奏生活，用画笔记录日常的温暖瞬间。",
            "partnerExpectations": "在成都，希望能遇到一起逛画廊、一起去咖啡馆速写或听小型独立音乐会的艺术搭子。",
            "optionalInfo": {"age": "25-30岁", "education": "本科及以下", "zodiac": "天秤座", "mbti": "ISFP",
                             "hobbies": ["插画", "独立音乐", "摄影"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习陶艺，体验泥土在手中成型的过程。",
                            "你最喜欢的城市是哪，为什么？": "巴黎，空气中弥漫着艺术气息和浪漫。"},
        },
        {  # 06: 旅行美食、ESTP、享乐主义
            "userId": "user_rui_06", "displayName": "孙睿", "gender": "男", "region": "成都",
            "primaryIntent": "旅游搭子",
            "UserBioSummary": "ESTP，人生苦短，必须及时行乐！我喜欢美食探店和说走就走的旅行，擅长制定最酷的行程和挖掘地方特色小吃。",
            "partnerExpectations": "希望找到一个说走就走、能吃辣、不矫情的旅行/美食搭子。我们现在就在成都，先从吃串串开始吧！",
            "optionalInfo": {"age": "25-30岁", "education": "本科及以下", "zodiac": "白羊座", "mbti": "ESTP",
                             "hobbies": ["环球旅行", "美食", "冲浪"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "尝试拍摄 Vlog，记录每一次旅行的精彩瞬间。",
                            "你最喜欢的城市是哪，为什么？": "曼谷，夜市的喧嚣和食物的丰富性让人兴奋。"},
        },
        {  # 07: 电影深度、INFP、理想主义
            "userId": "user_wen_07", "displayName": "李文", "gender": "男", "region": "北京",
            "primaryIntent": "电影搭子",
            "UserBioSummary": "INFP型理想主义者，专注于电影和文学评论。我关注电影背后的社会议题和导演的个人表达。比起爆米花大片，更爱文艺片和纪录片。",
            "partnerExpectations": "寻找能一起看深奥文艺片，并且能在电影结束后花两小时讨论意义的电影搭子。",
            "optionalInfo": {"age": "25-30岁", "education": "硕士", "zodiac": "巨蟹座", "mbti": "INFP",
                             "hobbies": ["电影评论", "诗歌", "纪录片"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习法语，为了更好地理解法国新浪潮电影。",
                            "你最喜欢的城市是哪，为什么？": "巴黎，是文学和艺术的摇篮，也是很多伟大电影的诞生地。"},
        },
        {  # 08: 职场女性、ENTJ、高效
            "userId": "user_hui_08", "displayName": "张慧", "gender": "女", "region": "上海",
            "primaryIntent": "职场搭子",
            "UserBioSummary": "互联网公司高管，ENTJ。我的生活以目标为导向，效率至上。希望在工作之外能有高质量的社交，拓展人脉和商业思维。",
            "partnerExpectations": "寻找在上海，有创业精神或高职位的职场女性，能一起讨论行业趋势和职业规划，互相提供资源。",
            "optionalInfo": {"age": "35岁以上", "education": "硕士", "zodiac": "狮子座", "mbti": "ENTJ",
                             "hobbies": ["高尔夫", "商业阅读", "红酒品鉴"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "冥想，以管理高强度工作带来的压力。",
                            "你最喜欢的城市是哪，为什么？": "纽约，全球金融和商业的中心，充满机会和挑战。"},
        },
        {  # 09: 游戏电竞、ESTP、直接
            "userId": "user_yu_09", "displayName": "王宇", "gender": "男", "region": "重庆",
            "primaryIntent": "游戏搭子",
            "UserBioSummary": "硬核游戏玩家，主玩策略和MOBA。直来直去，技术至上。在重庆寻找能一起开黑、能打能Carry的队友，拒绝玻璃心和挂机。",
            "partnerExpectations": "最好是MOBA高段位玩家，能接受技术指导和激烈讨论的搭子。",
            "optionalInfo": {"age": "18-24岁", "education": "本科及以下", "zodiac": "白羊座", "mbti": "ESTP",
                             "hobbies": ["电竞", "网球", "直播"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "尝试制作游戏 MOD，理解游戏底层逻辑。",
                            "你最喜欢的城市是哪，为什么？": "西雅图，有很多顶级的游戏公司，是梦想之地。"},
        },
        {  # 10: 环保公益、ENFJ、温暖
            "userId": "user_lan_10", "displayName": "蓝天", "gender": "女", "region": "杭州",
            "primaryIntent": "公益搭子",
            "UserBioSummary": "ENFJ型，致力于环保和动物保护。我希望通过实际行动让世界变得更好。性格温暖、有同理心，注重社区互助和可持续生活。",
            "partnerExpectations": "寻找在杭州一起参与志愿服务、组织环保活动的搭子。我们一起去净滩、去动物收容所吧！",
            "optionalInfo": {"age": "25-30岁", "education": "本科及以下", "zodiac": "水瓶座", "mbti": "ENFJ",
                             "hobbies": ["志愿服务", "园艺", "素食烹饪"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "零浪费生活方式，挑战一个月不产生垃圾。",
                            "你最喜欢的城市是哪，为什么？": "温哥华，城市被自然环绕，人和环境和谐共存。"},
        },
        {  # 11: 咖啡品鉴、ISTP、独行
            "userId": "user_xu_11", "displayName": "徐来", "gender": "男", "region": "厦门",
            "primaryIntent": "兴趣搭子",
            "UserBioSummary": "ISTP，独来独往的咖啡爱好者。我对精品咖啡的烘焙和冲煮技术有深入研究。喜欢在海边独坐，享受一杯手冲带来的片刻宁静。",
            "partnerExpectations": "在厦门寻找能一起探索小众咖啡馆、交流冲煮心得的兴趣搭子，要求对咖啡有基本了解和尊重。",
            "optionalInfo": {"age": "30-35岁", "education": "本科及以下", "zodiac": "处女座", "mbti": "ISTP",
                             "hobbies": ["手冲咖啡", "摩托车", "维修"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习维修老式咖啡机。",
                            "你最喜欢的城市是哪，为什么？": "墨尔本，拥有全球最顶尖的咖啡文化。"},
        },
        {  # 12: 健身撸铁、ESTJ、务实
            "userId": "user_ding_12", "displayName": "丁宁", "gender": "女", "region": "北京",
            "primaryIntent": "健身搭子",
            "UserBioSummary": "ESTJ型，健身房的常客，主要做力量训练。目标明确，执行力强。希望找一个能互相监督、一起突破 PR 的搭子。",
            "partnerExpectations": "在北京同一区域的健身搭子，最好也是力量训练爱好者，能互相保护和鼓励。",
            "optionalInfo": {"age": "25-30岁", "education": "本科及以下", "zodiac": "摩羯座", "mbti": "ESTJ",
                             "hobbies": ["举重", "营养学", "跑步"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习力量举的专业技巧，目标是参加业余比赛。",
                            "你最喜欢的城市是哪，为什么？": "北京，生活配套完善，能找到很多专业的健身工作室。"},
        },
        {  # 13: 摄影、INTP、逻辑
            "userId": "user_hao_13", "displayName": "刘昊", "gender": "男", "region": "深圳",
            "primaryIntent": "摄影搭子",
            "UserBioSummary": "INTP型思考者，热衷于街头和建筑摄影。我喜欢用镜头捕捉城市复杂的几何结构和瞬间的光影。生活简单，逻辑先行。",
            "partnerExpectations": "在深圳，寻找能一起扫街、交流后期技巧和寻找独特机位的摄影搭子，对色彩理论有基础了解。",
            "optionalInfo": {"age": "25-30岁", "education": "硕士", "zodiac": "水瓶座", "mbti": "INTP",
                             "hobbies": ["街头摄影", "数码后期", "解谜游戏"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "使用胶片相机，体验传统摄影的魅力。",
                            "你最喜欢的城市是哪，为什么？": "东京，城市规划和高耸的建筑提供了绝佳的摄影题材。"},
        },
        {  # 14: 戏剧演出、ENFP、热情
            "userId": "user_jing_14", "displayName": "杨静", "gender": "女", "region": "上海",
            "primaryIntent": "文化搭子",
            "UserBioSummary": "ENFP，对戏剧、音乐剧和各类小型演出有着无限的热情。性格外向，喜欢结识新朋友，享受舞台带来的情感冲击。",
            "partnerExpectations": "在上海，寻找能一起抢票、一起看戏，并在演出结束后分享观后感的文化搭子。希望对方也是一个情感丰富的人。",
            "optionalInfo": {"age": "18-24岁", "education": "本科及以下", "zodiac": "双子座", "mbti": "ENFP",
                             "hobbies": ["音乐剧", "戏剧", "写作", "社交"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习剧本创作，尝试写一个短篇喜剧。",
                            "你最喜欢的城市是哪，为什么？": "伦敦，西区剧院的氛围是无与伦比的。"},
        },
        {  # 15: 烹饪美食、ISFJ、顾家
            "userId": "user_min_15", "displayName": "周敏", "gender": "女", "region": "杭州",
            "primaryIntent": "美食搭子",
            "UserBioSummary": "ISFJ型，享受自己在家烹饪和烘焙。喜欢研究菜谱，用美食为家人和朋友带来温暖。我的生活平静且有条理。",
            "partnerExpectations": "寻找在杭州能一起去菜市场、交流烹饪心得的美食搭子。也欢迎能互相品尝对方厨艺的朋友。",
            "optionalInfo": {"age": "35岁以上", "education": "本科及以下", "zodiac": "金牛座", "mbti": "ISFJ",
                             "hobbies": ["烘焙", "中式烹饪", "园艺"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "尝试制作法式甜点，对精确度要求很高。",
                            "你最喜欢的城市是哪，为什么？": "杭州，生活节奏适中，有时间享受烹饪的乐趣。"},
        },
        {  # 16: 金融投资、ESTJ、精明
            "userId": "user_qi_16", "displayName": "钱琪", "gender": "男", "region": "深圳",
            "primaryIntent": "职场搭子",
            "UserBioSummary": "ESTJ，金融行业从业者。对宏观经济和投资策略有独到见解。寻找能一起分析市场、分享商业洞察的高效搭子。",
            "partnerExpectations": "寻找能一起讨论金融、投资和商业模式的职场搭子。要求思维清晰，数据驱动。",
            "optionalInfo": {"age": "30-35岁", "education": "硕士", "zodiac": "天蝎座", "mbti": "ESTJ",
                             "hobbies": ["股票分析", "网球", "商业杂志阅读"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "深入研究绿色金融和ESG投资的趋势。",
                            "你最喜欢的城市是哪，为什么？": "香港，作为亚洲金融中心，能感受到最前沿的市场脉动。"},
        },
        {  # 17: 音乐制作、INFP、内向
            "userId": "user_bo_17", "displayName": "吴波", "gender": "男", "region": "北京",
            "primaryIntent": "音乐搭子",
            "UserBioSummary": "INFP型，独立音乐制作人。我的世界由合成器和旋律构成。比起现场演出，更喜欢在工作室里沉浸于声音设计和创作。",
            "partnerExpectations": "寻找能一起交流音乐制作软件、分享小众音乐资源的音乐搭子，最好对电子乐或实验音乐感兴趣。",
            "optionalInfo": {"age": "25-30岁", "education": "本科及以下", "zodiac": "双鱼座", "mbti": "INFP",
                             "hobbies": ["音乐制作", "合成器", "录音"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习模块化合成器（Modular Synth）的声音设计。",
                            "你最喜欢的城市是哪，为什么？": "冰岛雷克雅未克，那里的孤独和空旷感是创作的绝佳背景。"},
        },
        {  # 18: 宠物爱好者、ESFP、社交
            "userId": "user_can_18", "displayName": "何灿", "gender": "女", "region": "广州",
            "primaryIntent": "宠物搭子",
            "UserBioSummary": "ESFP，外向且充满爱心。我家有三只猫，一只有点叛逆的狗。热衷于交流养宠心得，喜欢在户外和宠物一起玩耍。",
            "partnerExpectations": "寻找在广州的宠物搭子，能一起遛狗、分享宠物零食配方、交流宠物医疗知识。",
            "optionalInfo": {"age": "18-24岁", "education": "本科及以下", "zodiac": "狮子座", "mbti": "ESFP",
                             "hobbies": ["养宠物", "遛狗", "宠物摄影"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习宠物急救知识，以应对突发状况。",
                            "你最喜欢的城市是哪，为什么？": "旧金山，对宠物非常友好，随处可见带着狗的居民。"},
        },
        {  # 19: 历史文学、ISTJ、沉稳
            "userId": "user_fei_19", "displayName": "郑飞", "gender": "男", "region": "北京",
            "primaryIntent": "历史搭子",
            "UserBioSummary": "ISTJ，对中国古代史和军事史有深入研究。性格沉稳，不苟言笑，但一谈到历史话题就会变得滔滔不绝。我喜欢逛博物馆。",
            "partnerExpectations": "在北京寻找能一起逛历史遗迹、博物馆、图书馆的搭子，要求对历史文化有严肃的求知态度。",
            "optionalInfo": {"age": "35岁以上", "education": "硕士", "zodiac": "摩羯座", "mbti": "ISTJ",
                             "hobbies": ["军事史", "博物馆", "古典音乐"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "深入研究清代皇家建筑群的布局与功能。",
                            "你最喜欢的城市是哪，为什么？": "北京，历史遗迹和文化氛围无可替代。"},
        },
        {  # 20: 户外徒步、ENFJ、领导力
            "userId": "user_tao_20", "displayName": "郭涛", "gender": "男", "region": "成都",
            "primaryIntent": "户外搭子",
            "UserBioSummary": "ENFJ型，户外徒步和露营爱好者。擅长组织活动和带领团队，喜欢探索川西的秘境。我注重安全和团队协作。",
            "partnerExpectations": "寻找能一起挑战川西高原徒步路线、具备基本户外生存技能的搭子，希望对方有团队精神。",
            "optionalInfo": {"age": "30-35岁", "education": "本科及以下", "zodiac": "射手座", "mbti": "ENFJ",
                             "hobbies": ["徒步", "露营", "自驾游", "登山"]},
            "openAnswers": {"你最近在学习或尝试的新事物是什么？": "学习专业的野外急救技术。",
                            "你最喜欢的城市是哪，为什么？": "瑞士因特拉肯，那是户外运动的天堂。 Nox: "},
        },
    ]

    # --- 注入数据到 MongoDB ---
    db = get_db()

    if db is None:
        print("注入失败。请检查 MongoDB 服务是否运行。")
        return

    users_collection = db['users']
    profiles_collection = db['profiles']

    users_to_insert = []
    profiles_to_insert = []

    for template in data_templates:
        user_id = template['userId']
        display_name = template['displayName']

        user_info = user_map.get(user_id)
        if not user_info:
            print(f"警告：找不到 userId {user_id} 的基础信息。跳过。")
            continue

        email = f"{user_info['email_suffix']}@test.com"

        # 1. 构造 users 集合数据
        users_to_insert.append({
            "userId": user_id,
            "email": email,
            "passwordHash": PASSWORD_HASH,
            "createdAt": time.time(),
        })

        # 2. 构造 profiles 集合数据
        profile_doc = {
            "userId": user_id,
            "displayName": display_name,
            "UserBioSummary": template['UserBioSummary'],
            "partnerExpectations": template['partnerExpectations'],
            "timestamp": int(time.time() * 1000),
            "basicInfo": {
                "primaryIntent": template['primaryIntent'],
                "gender": template['gender'],
                "region": template['region'],
                "displayName": display_name,
                "email": email,
            },
            "optionalInfo": template['optionalInfo'],
            "openAnswers": template['openAnswers'],
            "selectedQuestions": list(template['openAnswers'].keys())
        }
        profiles_to_insert.append(profile_doc)

    try:
        # 清空并重新插入用户和资料 (只清除 mock 数据，不清除用户自己的数据)
        users_collection.delete_many({"userId": {"$regex": "^user_"}})
        profiles_collection.delete_many({"userId": {"$regex": "^user_"}})

        users_collection.insert_many(users_to_insert)
        profiles_collection.insert_many(profiles_to_insert)

        print(f"\n🎉 数据注入成功！")
        print(f"  - 已成功注入 {len(users_to_insert)} 条用户认证数据到 'users' 集合。")
        print(f"  - 已成功注入 {len(profiles_to_insert)} 条详细资料数据到 'profiles' 集合。")
        print("\n--- 请继续运行 generate_embeddings.py 来生成向量 ---")

    except Exception as e:
        print(f"\n❌ 数据注入失败：{e}")


if __name__ == '__main__':
    generate_mock_data()