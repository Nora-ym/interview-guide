# interview-guide
### ✨ 核心功能
- 📄 简历智能解析：上传 PDF/Word 简历，AI 自动提取技能、经历，生成优劣势分析与改进建议
- 💬 多模式模拟面试：支持文字 / 语音实时对话，覆盖 Java/Python/ 前端等 10 + 方向，3 档难度可调
- 📚 RAG 知识库问答：上传技术文档构建专属知识库，AI 基于文档精准回答，解决幻觉问题
- 📅 面试日程管理：AI 解析邮件邀请，自动创建日程，支持面试提醒与复盘记录

### 🛠️ 技术栈
- 后端：	FastAPI + SQLAlchemy 2.0 + Alembic + Celery
- 数据库：	MySQL 8.0 + Redis + ChromaDB（向量数据库）
- 前端：	React 18 + TypeScript + Vite + Tailwind CSS
- AI 能力：智谱 GLM-4 + 阿里云通义千问 + SSE 流式响应
- 部署：Docker + Docker Compose + WSL2 兼容

### 🚀 快速开始
#### 方式一：Docker 一键启动
```
# 1. 克隆项目
git clone https://github.com/你的用户名/interview-guide.git
cd interview-guide

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的智谱/阿里云 API Key

# 3. 启动所有服务（自动拉取MySQL/Redis/前后端）
docker-compose up -d

# 4. 初始化数据库表
docker exec -it interview-backend alembic upgrade head
```
✅ 访问地址：
- 前端页面：http://localhost:5173
- 后端接口文档：http://localhost:8000/docs
#### 方式二：本地开发启动
```
# 后端启动
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端启动（新开终端）
cd frontend
npm install
npm run dev
```

### 📁 项目结构
```
interview-guide/
├── backend/          # FastAPI 后端核心
│   ├── api/          # API 路由层
│   ├── models/       # 数据库ORM模型
│   ├── services/     # 业务逻辑层
│   ├── ai/           # 大模型调用与RAG实现
│   └── main.py       # 应用入口
├── frontend/         # React 前端
│   ├── src/pages/    # 页面组件
│   ├── src/api/      # HTTP请求封装
│   └── src/components/ # 通用组件
├── alembic/          # 数据库迁移脚本
├── docker-compose.yml
├── .env.example      # 环境变量模板
└── README.md
```

### ⚙️ 必配环境变量
```
# JWT 认证密钥（自定义随机字符串）
SECRET_KEY=your-random-secret-key-here

# AI 模型（二选一即可）
ZHIPU_API_KEY=your-zhipu-api-key
# ALIBABA_API_KEY=your-alibaba-api-key
```

### 📸 演示截图



### 声明
*本项目复刻于java-guide的基于 Spring Boot 4.0 + Java 21 + Spring AI + PostgreSQL + pgvector + RustFS + Redis，实现简历智能分析、AI模拟面试、知识库RAG检索等核心功能。*
详细了解见[interview-guide](javaguide.cn/zhuanlan/interview-guide.html)




