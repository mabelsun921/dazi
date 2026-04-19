# BuddyMatcher 项目接口文档

> 文档版本: 1.0.0  
> 更新日期: 2026-04-18  
> 项目描述: 找搭子社交平台 - 活动匹配与灵魂匹配

---

## 目录

1. [项目概述](#项目概述)
2. [模块功能列表](#模块功能列表)
3. [数据库集合](#数据库集合)
4. [接口文档](#接口文档)
5. [认证模块](#认证模块)
6. [用户模块](#用户模块)
7. [活动模块](#活动模块)
8. [匹配模块](#匹配模块)
9. [评价模块](#评价模块)
10. [消息模块](#消息模块)
11. [搭子请求模块](#搭子请求模块)
12. [附录](#附录)

---

## 项目概述

BuddyMatcher 是一个找搭子社交平台，提供以下核心功能：

- **用户认证**：注册、登录
- **用户资料管理**：完善个人资料、设置隐私
- **活动广场**：浏览、发布、搜索活动
- **活动推荐**：AI 智能推荐匹配活动
- **灵魂匹配**：基于性格的智能匹配
- **活动申请**：申请参加活动
- **评价系统**：活动后互评
- **即时通讯**：用户间私信

---

## 模块功能列表

| 模块名称 | 功能描述 | 状态 |
|---------|---------|------|
| 认证模块 | 用户注册、登录、token验证 | ✅ 完成 |
| 用户资料模块 | 完善资料、AI标签生成、隐私设置 | ✅ 完成 |
| 活动广场模块 | 发布活动、浏览活动、搜索活动 | ✅ 完成 |
| 活动推荐模块 | AI智能推荐匹配活动 | ✅ 完成 |
| 灵魂匹配模块 | 基于MBTI/性格的匹配 | ✅ 完成 |
| 活动申请模块 | 申请参加活动、审批 | ✅ 完成 |
| 评价模块 | 活动后互评、信誉分计算 | ✅ 完成 |
| 消息模块 | 即时通讯、对话列表 | ✅ 完成 |
| 搭子请求模块 | 短期找搭子诉求发布与匹配 | ✅ 完成 |
| 嵌入向量模块 | 用户向量生成、相似度计算 | ✅ 完成 |

---

## 数据库集合

### 1. users (用户表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| name | String | 用户名 |
| email | String | 邮箱（唯一） |
| password | String | 加密后的密码 |
| created_at | DateTime | 创建时间 |

### 2. profiles (用户资料表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| user_id | ObjectId | 关联users表 |
| name | String | 显示名称 |
| gender | String | 性别 |
| age | Integer | 年龄 |
| mbti | String | MBTI人格类型 |
| occupation | String | 职业 |
| hobbies | Array | 爱好列表 |
| personality | String | 个人简介 |
| location | Object | 位置 {city, district} |
| privacy_settings | Object | 隐私设置 |
| reputation | Float | 信誉分 (0-5) |
| ai_tags | Array | AI生成标签 |
| embedding_vector | Array | 嵌入向量 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3. activities (活动表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| user_id | ObjectId | 发起者ID |
| title | String | 活动标题 |
| content | String | 活动内容 |
| category | String | 分类 |
| location | Object | 地点 {city, district, address} |
| time | DateTime | 活动时间 |
| requirements | String | 对参与者的要求 |
| tags | Array | 标签 |
| max_participants | Integer | 最大参与人数 |
| status | String | 状态 (ongoing/completed/cancelled) |
| participants | Array | 已参与者ID列表 |
| created_at | DateTime | 创建时间 |

### 4. applications (活动申请表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| activity_id | ObjectId | 活动ID |
| user_id | ObjectId | 申请者ID |
| message | String | 申请留言 |
| status | String | 状态 (pending/approved/rejected) |
| created_at | DateTime | 申请时间 |

### 5. reviews (评价表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| from_uid | ObjectId | 评价者ID |
| to_uid | ObjectId | 被评价者ID |
| activity_id | ObjectId | 活动ID |
| rating | Integer | 评分 (1-5) |
| comment | String | 评价内容 |
| created_at | DateTime | 评价时间 |

### 6. actions (匹配行为表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| from_uid | ObjectId | 发起者ID |
| to_uid | ObjectId | 目标用户ID |
| action | String | 行为 (like/pass/superlike) |
| created_at | DateTime | 操作时间 |

### 7. conversations (会话表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| participants | Array | 参与者ID列表 |
| last_message | String | 最后一条消息 |
| last_message_at | DateTime | 最后消息时间 |
| created_at | DateTime | 创建时间 |

### 8. messages (消息表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| conversation_id | ObjectId | 会话ID |
| sender_id | ObjectId | 发送者ID |
| content | String | 消息内容 |
| created_at | DateTime | 发送时间 |

### 9. buddy_requests (搭子请求表)

| 字段 | 类型 | 描述 |
|-----|------|------|
| _id | ObjectId | 主键 |
| user_id | ObjectId | 发布者ID |
| title | String | 诉求标题 |
| content | String | 诉求内容 |
| request_type | String | 类型 (找搭子/找活动) |
| preferred_time | String | 偏好时间 |
| preferred_location | String | 偏好地点 |
| status | String | 状态 (open/closed) |
| created_at | DateTime | 创建时间 |

---

## 接口文档

---

## 认证模块

### 1. 用户注册

**接口**: `POST /api/auth/register`

**请求体**:
```json
{
  "name": "用户名",
  "email": "user@example.com",
  "password": "密码"
}
```

**响应** (200):
```json
{
  "message": "User registered successfully",
  "user_id": "用户ID",
  "user": {
    "user_id": "用户ID",
    "name": "用户名",
    "email": "user@example.com"
  }
}
```

**错误响应**:
- 400: 缺少必填字段
- 400: 邮箱已注册

---

### 2. 用户登录

**接口**: `POST /api/auth/login`

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "密码"
}
```

**响应** (200):
```json
{
  "message": "Login successful",
  "user": {
    "user_id": "用户ID",
    "name": "用户名",
    "email": "user@example.com"
  }
}
```

**错误响应**:
- 400: 缺少必填字段
- 401: 邮箱或密码错误

---

## 用户模块

### 3. 获取用户资料

**接口**: `GET /api/profile/<user_id>`

**响应** (200):
```json
{
  "user_id": "用户ID",
  "name": "用户名",
  "gender": "性别",
  "age": 25,
  "mbti": "INTJ",
  "occupation": "工程师",
  "hobbies": ["篮球", "读书"],
  "personality": "性格描述",
  "location": {
    "city": "北京",
    "district": "朝阳区"
  },
  "reputation": 4.5,
  "ai_tags": ["外向", "理性"],
  "privacy_settings": {
    "age_visible": true,
    "occupation_visible": true
  }
}
```

---

### 4. 更新用户资料

**接口**: `PUT /api/profile/<user_id>`

**请求体**:
```json
{
  "name": "新用户名",
  "gender": "男",
  "age": 25,
  "mbti": "INTJ",
  "occupation": "工程师",
  "hobbies": ["篮球", "读书"],
  "personality": "性格描述",
  "location": {
    "city": "北京",
    "district": "朝阳区"
  },
  "ai_tags": ["外向", "理性"],
  "privacy_settings": {
    "age_visible": true,
    "occupation_visible": true
  }
}
```

**响应** (200):
```json
{
  "message": "Profile updated successfully"
}
```

---

### 5. 获取所有用户资料

**接口**: `GET /api/profile/all?current_user_id=<user_id>`

**响应** (200):
```json
[
  {
    "user_id": "用户ID",
    "name": "用户名",
    "gender": "性别",
    "age": 25,
    "mbti": "INTJ",
    "occupation": "工程师",
    "hobbies": ["篮球", "读书"],
    "personality": "性格描述",
    "location": {
      "city": "北京",
      "district": "朝阳区"
    },
    "reputation": 4.5,
    "ai_tags": ["外向", "理性"]
  }
]
```

---

### 6. 获取用户详细信息

**接口**: `GET /api/user/<user_id>/details`

**响应** (200):
```json
{
  "profile": {
    "user_id": "用户ID",
    "name": "用户名",
    "gender": "性别",
    "age": 25,
    "mbti": "INTJ",
    "occupation": "工程师",
    "hobbies": ["篮球", "读书"],
    "personality": "性格描述",
    "location": {"city": "北京", "district": "朝阳区"},
    "reputation": 4.5,
    "ai_tags": ["外向", "理性"]
  },
  "ongoing_activities": [],
  "past_activities": [],
  "reviews": []
}
```

---

### 7. 获取用户统计数据

**接口**: `GET /api/user/<user_id>/stats`

**响应** (200):
```json
{
  "total_activities": 10,
  "completed_activities": 5,
  "total_reviews": 8,
  "average_rating": 4.5
}
```

---

## 活动模块

### 8. 创建活动

**接口**: `POST /api/activities`

**请求头**: Content-Type: application/json

**请求体**:
```json
{
  "user_id": "发起者ID",
  "title": "活动标题",
  "content": "活动内容",
  "category": "分类",
  "location": {
    "city": "北京",
    "district": "朝阳区",
    "address": "具体地址"
  },
  "time": "2026-05-01T14:00:00Z",
  "requirements": "对参与者的要求",
  "tags": ["标签1", "标签2"],
  "max_participants": 10
}
```

**响应** (201):
```json
{
  "message": "Activity created successfully",
  "activity_id": "活动ID"
}
```

---

### 9. 获取活动列表

**接口**: `GET /api/activities`

**响应** (200):
```json
[
  {
    "_id": "活动ID",
    "user_id": "发起者ID",
    "title": "活动标题",
    "content": "活动内容",
    "category": "分类",
    "location": {"city": "北京", "district": "朝阳区"},
    "time": "2026-05-01T14:00:00Z",
    "requirements": "要求",
    "tags": ["标签1", "标签2"],
    "max_participants": 10,
    "status": "ongoing",
    "participants": ["用户ID"],
    "created_at": "创建时间"
  }
]
```

---

### 10. 获取单个活动

**接口**: `GET /api/activities/<activity_id>`

**响应** (200):
```json
{
  "_id": "活动ID",
  "user_id": "发起者ID",
  "title": "活动标题",
  "content": "活动内容",
  "category": "分类",
  "location": {"city": "北京", "district": "朝阳区"},
  "time": "2026-05-01T14:00:00Z",
  "requirements": "要求",
  "tags": ["标签1", "标签2"],
  "max_participants": 10,
  "status": "ongoing",
  "participants": ["用户ID"],
  "created_at": "创建时间"
}
```

---

### 11. 申请参加活动

**接口**: `POST /api/activities/<activity_id>/apply`

**请求体**:
```json
{
  "user_id": "申请者ID",
  "message": "申请留言"
}
```

**响应** (201):
```json
{
  "message": "Application submitted successfully",
  "application_id": "申请ID"
}
```

---

### 12. 获取活动申请列表

**接口**: `GET /api/activities/<activity_id>/applications`

**响应** (200):
```json
[
  {
    "_id": "申请ID",
    "activity_id": "活动ID",
    "user_id": "申请者ID",
    "message": "申请留言",
    "status": "pending",
    "created_at": "申请时间"
  }
]
```

---

### 13. 处理申请

**接口**: `PUT /api/applications/<application_id>`

**请求体**:
```json
{
  "status": "approved"  // 或 "rejected"
}
```

**响应** (200):
```json
{
  "message": "Application updated successfully"
}
```

---

### 14. 获取用户发起的活动申请

**接口**: `GET /api/user/<user_id>/host-applications`

**说明**: 获取用户作为活动发起者收到的所有报名申请

**响应** (200):
```json
[
  {
    "_id": "申请ID",
    "activity_id": "活动ID",
    "activity_title": "活动标题",
    "applicant_id": "申请者ID",
    "applicant_name": "申请者昵称",
    "status": "pending",
    "created_at": "申请时间"
  }
]
```

---

### 15. 更新活动信息

**接口**: `PUT /api/activities/<activity_id>`

**请求体**:
```json
{
  "user_id": "用户ID（必须为活动发起者）",
  "title": "活动标题",
  "content": "活动内容",
  "category": "分类",
  "location": {"city": "城市", "district": "区县"},
  "budget": 100,
  "time": "2026-05-01T14:00:00",
  "requirements": "参与要求",
  "tags": ["标签1", "标签2"],
  "people_range": {"min": 3, "max": 10},
  "need_confirmation": true,
  "deposit": 50
}
```

**响应** (200):
```json
{
  "message": "Activity updated successfully"
}
```

---

### 16. 删除/撤销活动

**接口**: `DELETE /api/activities/<activity_id>?user_id=<user_id>`

**说明**: 撤销/删除自己发起的活动，同时删除相关申请记录

**响应** (200):
```json
{
  "message": "Activity deleted successfully"
}
```

---

### 17. 搜索活动

**接口**: `POST /api/activities/search`

**请求体**:
```json
{
  "query": "搜索关键词"
}
```

**响应** (200):
```json
[
  {
    "_id": "活动ID",
    "title": "活动标题",
    "content": "活动内容",
    "category": "分类"
  }
]
```

---

### 15. AI活动hint生成

**接口**: `POST /api/activity/ai_hint`

**请求体**:
```json
{
  "activity_description": "周末想组织一次爬山活动，希望找有经验的伙伴一起"
}
```

**响应** (200):
```json
{
  "title": "周末运动",
  "category": "运动",
  "duration": "2-3小时",
  "location_type": "户外",
  "people_count": {
    "min": 3,
    "max": 10
  },
  "tags": ["运动", "户外"],
  "description": "周末想组织一次爬山活动，希望找有经验的伙伴一起",
  "requirements": "性格好，易相处"
}
```

**说明**:
- 当Google Gemini API不可用时，系统会自动使用本地规则引擎生成活动提示
- 本地规则会根据活动描述中的关键词自动判断分类、生成标题和标签
```

---

## 匹配模块

### 16. 活动推荐

**接口**: `POST /api/activities/recommend`

**请求体**:
```json
{
  "user_id": "用户ID"
}
```

**响应** (200):
```json
[
  {
    "_id": "活动ID",
    "title": "活动标题",
    "match_score": 85,
    "match_reason": "匹配理由"
  }
]
```

---

### 17. 用户匹配度评分

**接口**: `POST /api/match/score`

**请求体**:
```json
{
  "profile_a": {
    "name": "用户A",
    "mbti": "INTJ",
    "personality": "性格描述",
    "hobbies": ["篮球"],
    "occupation": "工程师"
  },
  "profile_b": {
    "name": "用户B",
    "mbti": "ENFP",
    "personality": "性格描述",
    "hobbies": ["足球"],
    "occupation": "设计师"
  },
  "match_mode": "similarity"  // 或 "complementary"
}
```

**响应** (200):
```json
{
  "matchScore": 75,
  "matchLevel": "高度匹配",
  "detailedRationale": {
    "overlapPoints": ["共同点1", "共同点2"],
    "complementaryPoints": ["互补点1"],
    "mismatchPoints": ["不匹配点1"],
    "summary": "总结"
  },
  "objectiveOverlapScore": 45,
  "matchMode": "similarity"
}
```

---

### 18. 活动匹配度评分

**接口**: `POST /api/activity/score`

**请求体**:
```json
{
  "profile": {
    "name": "用户名",
    "gender": "性别",
    "mbti": "INTJ",
    "occupation": "工程师",
    "personality": "性格描述",
    "location": {"city": "北京", "district": "朝阳区"},
    "ai_tags": ["外向", "理性"],
    "reputation": 4.5
  },
  "activity": {
    "title": "活动标题",
    "content": "活动内容",
    "category": "分类",
    "location": {"city": "北京", "district": "朝阳区"},
    "requirements": "要求",
    "tags": ["标签1", "标签2"]
  }
}
```

**响应** (200):
```json
{
  "score": 85,
  "reason": "匹配理由详细说明..."
}
```

---

### 19. 批量评分

**接口**: `POST /api/batch_score`

**请求体**:
```json
{
  "user_id": "用户ID",
  "activities": ["活动ID1", "活动ID2"]
}
```

**响应** (200):
```json
{
  "results": [
    {
      "activity_id": "活动ID1",
      "score": 85
    }
  ]
}
```

---

### 20. 记录匹配行为

**接口**: `POST /api/actions`

**请求体**:
```json
{
  "from_uid": "发起者ID",
  "to_uid": "目标用户ID",
  "action": "like"  // like / pass / superlike
}
```

**响应** (201):
```json
{
  "message": "Action recorded",
  "match": true  // 是否匹配成功
}
```

---

## 评价模块

### 21. 创建评价

**接口**: `POST /api/reviews`

**请求体**:
```json
{
  "from_uid": "评价者ID",
  "to_uid": "被评价者ID",
  "activity_id": "活动ID",
  "rating": 5,
  "comment": "评价内容"
}
```

**响应** (201):
```json
{
  "message": "Review created successfully",
  "review_id": "评价ID"
}
```

---

### 22. 获取用户评价

**接口**: `GET /api/reviews/<user_id>`

**响应** (200):
```json
[
  {
    "_id": "评价ID",
    "from_uid": "评价者ID",
    "to_uid": "被评价者ID",
    "activity_id": "活动ID",
    "rating": 5,
    "comment": "评价内容",
    "created_at": "评价时间"
  }
]
```

---

## 消息模块

### 23. 创建或获取对话

**接口**: `POST /api/conversations`

**请求体**:
```json
{
  "user1_id": "用户1ID",
  "user2_id": "用户2ID"
}
```

**响应** (200):
```json
{
  "conversation_id": "会话ID",
  "exists": true
}
```

**响应** (201 - 新创建):
```json
{
  "conversation_id": "会话ID",
  "exists": false
}
```

---

### 24. 获取对话列表

**接口**: `GET /api/conversations/<user_id>`

**响应** (200):
```json
[
  {
    "_id": "会话ID",
    "participants": ["用户ID1", "用户ID2"],
    "last_message": "最后一条消息",
    "last_message_at": "时间",
    "other_user": {
      "user_id": "对方ID",
      "name": "对方用户名"
    }
  }
]
```

---

### 25. 获取消息历史

**接口**: `GET /api/conversations/<conversation_id>/messages`

**响应** (200):
```json
{
  "messages": [
    {
      "_id": "消息ID",
      "sender_id": "发送者ID",
      "content": "消息内容",
      "created_at": "发送时间"
    }
  ]
}
```

---

### 26. 发送消息

**接口**: `POST /api/messages`

**请求体**:
```json
{
  "conversation_id": "会话ID",
  "sender_id": "发送者ID",
  "content": "消息内容"
}
```

**响应** (201):
```json
{
  "message": "Message sent successfully",
  "message_id": "消息ID"
}
```

---

## 搭子请求模块

### 27. 创建搭子请求

**接口**: `POST /api/buddy_requests`

**请求体**:
```json
{
  "user_id": "发布者ID",
  "title": "诉求标题",
  "content": "诉求内容",
  "request_type": "找搭子",
  "preferred_time": "周末",
  "preferred_location": "北京"
}
```

**响应** (201):
```json
{
  "message": "Buddy request created successfully",
  "request_id": "请求ID"
}
```

---

### 28. 获取搭子请求列表

**接口**: `GET /api/buddy_requests?user_id=<user_id>`

**响应** (200):
```json
[
  {
    "_id": "请求ID",
    "user_id": "发布者ID",
    "title": "诉求标题",
    "content": "诉求内容",
    "request_type": "找搭子",
    "preferred_time": "周末",
    "preferred_location": "北京",
    "status": "open",
    "created_at": "创建时间"
  }
]
```

---

### 29. 更新搭子请求

**接口**: `PUT /api/buddy_requests/<request_id>`

**请求体**:
```json
{
  "title": "新标题",
  "content": "新内容",
  "status": "closed"
}
```

**响应** (200):
```json
{
  "message": "Buddy request updated successfully"
}
```

---

### 30. 删除搭子请求

**接口**: `DELETE /api/buddy_requests/<request_id>`

**响应** (200):
```json
{
  "message": "Buddy request deleted successfully"
}
```

---

### 31. 搭子请求匹配

**接口**: `POST /api/buddy_request/match`

**请求体**:
```json
{
  "user_id": "用户ID",
  "request_id": "请求ID"
}
```

**响应** (200):
```json
{
  "matches": [
    {
      "_id": "匹配的请求ID",
      "user_id": "发布者ID",
      "title": "诉求标题",
      "match_score": 85,
      "match_reasons": ["匹配原因1", "匹配原因2"]
    }
  ]
}
```

---

## 附录

### A. 评分规则

1. **用户信誉分**：
   - 由其他用户评价计算得出
   - 计算公式：所有评价的平均分
   - 范围：0-5分
   - 只有至少10个评价后才显示

2. **活动匹配度**：
   - 由AI (Gemini) 评估
   - 考虑因素：兴趣匹配、地点便利、时间合适度、发起者评分等
   - 范围：0-100分

3. **用户匹配度**：
   - 支持两种模式：相似性(similarity) 和 互补性(complementary)
   - 由AI (Gemini) 评估
   - 范围：0-100分

### B. 状态说明

| 状态 | 说明 |
|-----|------|
| activity.status | ongoing(进行中) / completed(已完成) / cancelled(已取消) |
| application.status | pending(待审批) / approved(已通过) / rejected(已拒绝) |
| buddy_request.status | open(开放) / closed(已关闭) |
| action.action | like(喜欢) / pass(跳过) / superlike(超级喜欢) |

### C. 错误码

| 错误码 | 说明 |
|-------|------|
| 400 | 请求参数错误 |
| 401 | 未授权/认证失败 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

*文档最后更新: 2026-04-18*
