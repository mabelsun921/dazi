# BuddyMatcher 部署配置

## 项目结构

```
buddyMatcher/
├── backend/
│   ├── app.py              # Flask 主应用
│   ├── requirements.txt   # Python 依赖
│   └── ...
├── frontend/               # React 前端
│   ├── package.json
│   └── ...
├── railway.json           # Railway 部署配置
└── Dockerfile            # Docker 配置
```

## 环境变量

部署时需要设置以下环境变量：

### 后端 (Railway)
```
GEMINI_API_KEY=你的Gemini API密钥
MONGO_URI=mongodb://用户名:密码@host:27017/数据库名
```

### 前端 (Vercel/Railway)
```
VITE_API_URL=https://你的后端地址.railway.app
```

## 部署方案

### 方案一：Railway (推荐)

#### 1. 后端部署到 Railway
1. 注册 [Railway](https://railway.app)
2. 点击 "New Project" -> "Deploy from GitHub"
3. 选择你的仓库
4. 添加环境变量：
   - `GEMINI_API_KEY`
   - `MONGO_URI` (使用 MongoDB Atlas 免费集群)
5. Railway 会自动检测 Python 项目并部署

#### 2. 前端部署到 Vercel
1. 注册 [Vercel](https://vercel.com)
2. 导入你的前端项目
3. 设置环境变量：
   - `VITE_API_URL` = 你的Railway后端URL
4. 部署

### 方案二：Render

#### 1. 后端部署到 Render
1. 注册 [Render](https://render.com)
2. 创建 Web Service
3. 连接 GitHub 仓库
4. 设置：
   - Build Command: `cd backend && pip install -r requirements.txt`
   - Start Command: `cd backend && gunicorn app:app -b 0.0.0.0:$PORT`
5. 添加环境变量

#### 2. 前端部署到 Netlify/Vercel
同上

## MongoDB 数据库 (免费)

推荐使用 MongoDB Atlas 免费集群：
1. 注册 [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. 创建免费集群 (M0 Sandbox)
3. 创建数据库用户
4. 获取连接字符串，格式：
   ```
   mongodb+srv://用户名:密码@cluster.xxxxx.mongodb.net/数据库名
   ```

## 快速开始

### 1. Fork/Clone 仓库
```bash
git clone https://github.com/你的用户名/buddyMatcher.git
cd buddyMatcher
```

### 2. 配置环境变量
在 Railway/Render 后台设置：
- `GEMINI_API_KEY`: 从 Google AI Studio 获取
- `MONGO_URI`: 从 MongoDB Atlas 获取

### 3. 部署前端
```bash
cd frontend
vercel --prod
```

### 4. 更新前端 API 地址
部署后端后，更新前端的 API 地址为实际的后端URL

## 注意事项

1. **CORS 配置**: 后端已配置允许所有来源，生产环境建议限制
2. **安全**: 不要将 API Key 提交到代码中
3. **域名**: 部署后记得更新前端的 API 地址
