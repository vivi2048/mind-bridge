# 🧠 MindBridge — 校园心理健康评估与智能问答系统

> 基于 LangGraph 多智能体架构，为高校学生提供 **情绪陪伴**、**专业心理咨询** 与 **危机风险预警** 的一站式 AI 心理健康支持平台。

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🤗 情绪陪伴 | 温暖友好的日常对话，缓解孤独与压力 |
| 🧑‍⚕️ 专业心理咨询 | 基于 RAG 知识库的心理学专业回复，覆盖学业压力、焦虑抑郁、人际关系等 11 个主题 |
| 🚨 危机风险预警 | 实时评估风险等级（低/中/高/危急），高危情况自动触发异步预警通知 |
| 🧩 智能路由 | Supervisor 节点自动识别用户意图，分流至陪伴或咨询通道 |
| 💾 会话记忆 | 基于 MySQL 的持久化对话历史，支持多轮上下文连续对话 |
| 🌊 流式响应 | 基于 SSE 的打字机效果，实时展示 AI 回复 |
| 🖥️ 前端界面 | 开箱即用的 Web 聊天界面 |

## 🏗️ 系统架构

```
                        ┌─────────────┐
                        │  用户输入    │
                        └──────┬──────┘
                               ▼
                     ┌───────────────────┐
                     │  🧠 Memory Node   │ ← 加载历史对话
                     └────────┬──────────┘
                              ▼
                    ┌────────────────────┐
                    │ 👁️ Supervisor Node  │ ← 意图分类
                    └───┬────────────┬───┘
                  chat  │            │  consult / risk
                        ▼            ▼
              ┌──────────────┐ ┌─────────────────┐
              │ 🫂 Companion  │ │ 📚 Knowledge Node│ ← RAG 知识检索
              └──────┬───────┘ └───────┬─────────┘
                     │                 ▼
                     │       ┌──────────────────┐
                     │       │ 🛡️ Risk Guardian  │ ← 风险评估 + 预警
                     │       └───────┬──────────┘
                     │               ▼
                     │       ┌──────────────────┐
                     └──────►│ 🧑‍⚕️ Counselor Node │ ← 专业回复生成
                             └───────┬──────────┘
                                     ▼
                           ┌──────────────────┐
                           │ 💾 Save Memory    │ → 持久化对话
                           └──────────────────┘
```

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| **智能体编排** | LangGraph (StateGraph + 条件路由) |
| **LLM / Embedding** | OpenAI 兼容接口 / DashScope Embeddings |
| **向量数据库** | ChromaDB（本地持久化） |
| **关系数据库** | MySQL 8.0 (SQLAlchemy Async) |
| **消息队列** | Redis 7 (异步预警任务) |
| **Web 框架** | FastAPI + Uvicorn |
| **容器化** | Docker Compose |

## 🚀 快速开始

### 环境要求

- Docker & Docker Compose
- OpenAI 兼容的 LLM API（如 DashScope / 本地 Ollama）

### 1. 克隆项目

```bash
git clone https://github.com/vivi2048/mind-bridge.git
cd mind-bridge
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入 LLM API 配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_BASE_URL` | LLM API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_API_KEY` | API 密钥 | `sk-xxx` |
| `LLM_MODEL_ID` | 模型名称 | `qwen-plus` |
| `EMBEDDING_API_KEY` | Embedding 密钥 | `sk-xxx` |
| `EMBEDDING_MODEL_ID` | Embedding 模型 | `text-embedding-v3` |

> ⚠️ 使用 Docker 时，**无需配置** `DATABASE_URL` 和 `REDIS_URL`，docker-compose 会自动注入。

### 3. 一键启动

```bash
docker-compose up -d --build
```

启动后自动执行：
1. ✅ MySQL 健康检查（等待数据库就绪）
2. ✅ 创建数据库表结构
3. ✅ 导入知识库到 ChromaDB
4. ✅ 创建测试用户（user: `test` / password: `test123`）

应用运行在 **http://localhost:8000**

### 4. 打开聊天界面

浏览器访问 **http://localhost:8000** 即可开始对话。

### 5. 开发模式（热重载）

```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
```

开发模式下代码修改实时生效，无需重新构建镜像。

## 📁 项目结构

```
mind-bridge/
├── app/
│   ├── agents/                # 智能体定义
│   │   ├── graph.py           # LangGraph 状态图
│   │   ├── state.py           # 共享状态模型
│   │   └── nodes/             # 各节点实现
│   │       ├── supervisor.py  # 意图分类
│   │       ├── companion.py   # 日常陪伴
│   │       ├── counselor.py   # 专业咨询
│   │       ├── knowledge.py   # RAG 知识检索
│   │       ├── memory.py      # 对话记忆（加载 + 保存）
│   │       └── risk_guardian.py  # 风险评估与预警
│   ├── api/
│   │   └── chat.py            # 聊天 API（SSE 流式响应）
│   ├── core/
│   │   └── config.py          # 配置管理 (pydantic-settings)
│   ├── db/
│   │   └── session.py         # 异步数据库连接
│   ├── models/
│   │   └── entities.py        # 数据模型（无外键约束）
│   ├── services/
│   │   ├── mcp_tools.py       # MCP 工具（异步任务封装）
│   │   └── task_queue.py      # Redis 异步任务队列
│   └── static/
│       └── index.html         # 前端聊天界面
├── knowledge/                 # 心理健康知识库（11 篇文档）
├── scripts/                   # 初始化脚本
│   ├── init_db.py             # 建表
│   ├── ingest_knowledge.py    # 知识库导入
│   └── create_test_user.py    # 测试用户创建
├── tests/                     # 测试套件
├── logs/                      # 应用日志（自动挂载）
├── data/
│   └── chroma_db/             # 向量数据库（本地持久化）
├── docker-compose.yml         # 容器编排
├── docker-compose.override.yml # 开发模式（代码挂载 + 热重载）
├── Dockerfile                 # 应用镜像
├── requirements.txt           # Python 依赖
└── .env                       # 环境变量（需自行创建）
```

## 🔗 API

### POST `/api/chat` — 流式对话

发送消息，返回 SSE 流式响应（打字机效果）。

**请求体：**

```json
{
  "user_id": 1001,
  "session_id": 100101,
  "message": "最近考试压力好大，总是睡不着"
}
```

**SSE 响应流：**

```
data: {"type": "token", "content": "我能理解"}

data: {"type": "token", "content": "你的感受"}

data: {"type": "done", "risk_level": "low"}
```

| type | 说明 |
|------|------|
| `token` | AI 回复的一个片段 |
| `done` | 对话完成，附带风险等级 |
| `error` | 错误信息 |

### GET `/health` — 健康检查

```bash
curl http://localhost:8000/health
# {"status": "ok", "message": "MindBridge is running!"}
```

## 🗃️ 数据说明

| 数据 | 存储位置 | 持久化方式 |
|------|----------|------------|
| 对话记录 | MySQL | `mysql_data` Docker 卷 |
| 向量数据库 | ChromaDB | `./data/chroma_db/` 本地目录 |
| 应用日志 | `./logs/app.log` | 本地文件 |
| 缓存/队列 | Redis | `redis_data` Docker 卷 |

> 数据一致性由应用层控制（无外键约束），会话不存在时自动创建。

## 📖 知识库主题

系统内置 11 篇心理健康领域知识文档，覆盖：

- 学业压力与倦怠 · 焦虑与恐慌 · 情绪低落与抑郁
- 校园心理健康资源 · 心理咨询转介 · 风险评估政策
- 人际关系与家庭 · 隐私边界与伦理 · 睡眠与自我关怀
- 适应与过渡期 · 考试季指导

## 📄 License

MIT
