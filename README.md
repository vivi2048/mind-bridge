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
| **向量数据库** | ChromaDB |
| **关系数据库** | MySQL 8.0 (SQLAlchemy Async) |
| **消息队列** | Redis 7 (异步预警任务) |
| **Web 框架** | FastAPI + Uvicorn |
| **容器化** | Docker Compose |

## 🚀 快速开始

### 环境要求

- Docker & Docker Compose
- OpenAI 兼容的 LLM API（或本地模型）

### 1. 克隆项目

```bash
git clone https://github.com/vivi2048/mind-bridge.git
cd mind-bridge
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM API 配置
```

关键配置项：

| 变量 | 说明 |
|------|------|
| `LLM_BASE_URL` | LLM API 地址 |
| `LLM_API_KEY` | API 密钥 |
| `LLM_MODEL` | 模型名称 |
| `EMBEDDING_API_KEY` | Embedding 服务密钥 |
| `DATABASE_URL` | MySQL 连接地址 |
| `REDIS_URL` | Redis 连接地址 |

### 3. 一键启动

```bash
docker-compose up -d
```

启动后会自动执行初始化：创建数据库表 → 导入知识库 → 创建测试用户。

应用运行在 **http://localhost:8000**

### 4. 测试对话

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "session_1",
    "message": "最近考试压力好大，总是睡不着"
  }'
```

## 📁 项目结构

```
mind-bridge/
├── app/
│   ├── agents/            # 智能体定义
│   │   ├── graph.py       # LangGraph 状态图
│   │   ├── state.py       # 共享状态模型
│   │   └── nodes/         # 各节点实现
│   │       ├── supervisor.py      # 意图分类
│   │       ├── companion.py       # 日常陪伴
│   │       ├── counselor.py       # 专业咨询
│   │       ├── knowledge.py       # RAG 知识检索
│   │       ├── memory.py          # 对话记忆
│   │       └── risk_guardian.py   # 风险评估与预警
│   ├── api/               # API 路由
│   ├── core/              # 配置管理
│   ├── db/                # 数据库连接
│   ├── models/            # 数据模型
│   └── services/          # 服务层（MCP 工具、任务队列）
├── knowledge/             # 心理健康知识库（11 篇文档）
├── scripts/               # 初始化脚本
├── tests/                 # 测试套件
├── docker-compose.yml     # 容器编排
└── requirements.txt       # Python 依赖
```

## 📖 知识库主题

系统内置 11 篇心理健康领域知识文档，覆盖：

- 学业压力与倦怠 · 焦虑与恐慌 · 情绪低落与抑郁
- 校园心理健康资源 · 心理咨询转介 · 风险评估政策
- 人际关系与家庭 · 隐私边界与伦理 · 睡眠与自我关怀
- 适应与过渡期 · 考试季指导

## 🔗 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat` | POST | 发送聊天消息，返回 AI 回复 |
| `/health` | GET | 健康检查 |

## 📄 License

MIT
