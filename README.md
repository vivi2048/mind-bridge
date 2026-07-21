<div align="center">
  <h2>MindBridge — 校园心理健康智能问答系统</h2>
  <p>基于 LangGraph 多智能体的 AI 心理陪伴与危机预警平台</p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.0-indigo" alt="version">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="license">
  <img src="https://img.shields.io/badge/python-3.11%2B-teal" alt="python">
  <img src="https://img.shields.io/badge/docker-ready-green" alt="docker">
</p>

通过 Supervisor → Companion / Counselor 多智能体路由,为学生提供情绪陪伴、专业心理咨询与实时风险预警.支持 RAG 知识检索、流式对话与会话记忆.

---

## ✨ 功能

|          |                               |
|----------|-------------------------------|
| **智能路由** | Supervisor 自动识别意图,分流至陪伴或咨询通道  |
| **情绪陪伴** | 温暖友好的日常对话,缓解孤独与压力             |
| **专业咨询** | 基于 RAG 知识库的心理学回复,覆盖 11 个主题领域  |
| **风险预警** | 实时评估风险等级(低/中/高/危急),高危自动触发异步预警 |
| **会话记忆** | MySQL 持久化对话历史,多轮上下文连续对话       |
| **流式响应** | SSE 打字机效果,实时展示 AI 回复          |
| **前端界面** | 开箱即用的 Web 聊天页面,支持 Markdown 渲染        |
| **异步任务** | Redis 任务队列,支持死信重试与预警闭环        |

## 🏗️ 架构

```
                        ┌─────────────┐
                        │  用户输入    │
                        └──────┬──────┘
                               ▼
                    ┌────────────────────┐
                    │ 👁️ Supervisor Node  │ ← 意图分类
                    └────────┬───────────┘
                             ▼
                     ┌───────────────────┐
                     │  🧠 Memory Node   │ ← 加载历史对话
                     └────────┬──────────┘
                              │
                  ┌───────────┴───────────┐
                  │                       │
              chat  │                 consult / risk
                  ▼                       ▼
        ┌──────────────┐       ┌─────────────────┐
        │ 🫂 Companion  │       │ 📚 Knowledge Node│ ← RAG 检索
        └──────┬───────┘       └───────┬─────────┘
               │                       ▼
               │             ┌──────────────────┐
               │             │ 🛡️ Risk Guardian  │ ← 风险评估
               │             └───────┬──────────┘
               │                     ▼
               │             ┌──────────────────┐
               │             │ 🧑‍⚕️ Counselor Node │ ← 专业回复
               │             └───────┬──────────┘
               │                     │
               └─────────┬───────────┘
                         ▼
               ┌──────────────────┐
               │ 💾 Save Memory    │ → 持久化
               └──────────────────┘
```

## 🛠️ 技术栈

**LangGraph** · **FastAPI** · **ChromaDB** · **MySQL 8.0** · **Redis 7** · **Docker Compose**

| 层级              | 技术                                 |
|-----------------|------------------------------------|
| 智能体编排           | LangGraph (StateGraph + 条件路由)      |
| LLM / Embedding | OpenAI 兼容接口 / 本地 bge-large-zh       |
| 向量数据库           | ChromaDB(本地持久化)                    |
| 关系数据库           | MySQL 8.0 (SQLAlchemy Async)       |
| 消息队列            | Redis 7 (异步预警任务)                   |
| Web 框架          | FastAPI + Uvicorn                  |
| 容器化             | Docker Compose                     |

## 🚀 快速开始

### 环境要求

- Docker & Docker Compose
- OpenAI 兼容的 LLM API(如 DashScope / 本地 Ollama)

### 1. 克隆项目

```bash
git clone https://github.com/vivi2048/mind-bridge.git
cd mind-bridge
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env,填入 API 配置
```

**必填项:**

| 变量                   | 说明             | 示例                                                  |
|----------------------|----------------|-----------------------------------------------------|
| `API_KEY`            | LLM API 密钥     | `sk-xxx`                                            |
| `BASE_URL`           | LLM API 地址     | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL_ID`       | 对话模型名称         | `qwen3.6-flash`                                     |
| `EMBEDDING_BACKEND`  | Embedding 模式   | `api`(推荐)或 `local`                               |

**Embedding 配置(二选一):**

- **Local 模式(默认)**:需先下载模型(见下方),零 API 成本
- **API 模式**:填写 `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL_ID`(如 `text-embedding-v3`)

<details>
<summary>📥 本地 Embedding 模型下载(仅 local 模式需要)</summary>

运行一键下载脚本:

```bash
python scripts/download_embedding_model.py
```

下载完成后,修改 `.env`:

```bash
EMBEDDING_BACKEND=local
EMBEDDING_MODEL_ID=./data/embedding_models/models/BAAI/bge-large-zh-v1.5/snapshots/master
EMBEDDING_CACHE_DIR=./data/embedding_models
```

然后启动:

```bash
docker-compose up -d --build
```

> 💡 模型约 1.3GB,首次下载需要几分钟.下载失败时脚本会提供 HuggingFace 镜像备选方案.

</details>

> 💡 Docker 环境下 `DATABASE_URL` 和 `REDIS_URL` 由 docker-compose 自动注入,无需手动配置.

### 3. 一键启动

```bash
docker-compose up -d --build
```

启动后自动执行:建表 → 导入知识库 → 创建测试用户(`test` / `test123`)

应用运行在 <http://localhost:8000>,浏览器访问即可开始对话.

> 💡 **开发模式**:`docker-compose up -d` 自动加载 `docker-compose.override.yml`,代码挂载 + 热重载,改完即生效.

## 📖 API

### POST `/api/chat` — 流式对话

```json
{
  "user_id": 1001,
  "session_id": 100101,
  "message": "最近考试压力好大,总是睡不着"
}
```

SSE 响应流:

```
data: {"type": "token", "content": "我能理解"}
data: {"type": "token", "content": "你的感受"}
data: {"type": "done", "risk_level": "low"}
```

| type    | 说明          |
|---------|-------------|
| `token` | AI 回复片段     |
| `done`  | 完成信号 + 风险等级 |
| `error` | 错误信息        |

## 📁 项目结构

```
mind-bridge/
├── app/
│   ├── agents/            # 智能体(graph / state / nodes)
│   ├── api/               # API 路由(SSE 流式)
│   ├── core/              # 配置管理 + LLM/Embedding 实例管理
│   ├── db/                # 数据库连接
│   ├── models/            # 数据模型
│   ├── services/          # 任务队列 + 风险工具
│   └── static/            # 前端页面
├── knowledge/             # 心理健康知识库(11 篇 Markdown)
├── scripts/               # 初始化工具
│   ├── init_db.py             # 数据库初始化
│   ├── ingest_knowledge.py    # 知识库导入(按标题切分 + 去重)
│   ├── create_test_user.py    # 测试用户创建
│   └── download_embedding_model.py # 本地 Embedding 模型下载
├── tests/                 # 自动化测试
│   ├── run_tests.py           # 测试脚本
│   ├── dataset/               # 测试数据集(JSON,115 条)
│   ├── reports/               # 测试报告输出
│   └── debug/                 # 调试脚本
├── data/                  # 数据目录(不提交到 Git)
│   ├── chroma_db/             # 向量数据库
│   └── embedding_models/      # 本地 Embedding 模型
└── logs/                  # 应用日志
```

## 🛠️ 常用命令

### 重建知识库

知识库首次启动时自动构建,后续启动会跳过.如需强制重建:

```bash
docker exec mindbridge_app python -m scripts.ingest_knowledge --force
```

### 运行自动化测试

运行完整测试套件(115 条测试用例):

```bash
docker exec mindbridge_app python -m tests.run_tests
```

测试报告输出到 `tests/reports/` 目录.

### 运行连通性测试

测试 MySQL、Redis、LLM、Embedding 的连接状态:

```bash
docker exec mindbridge_app python -m tests.debug.test_config
```

## 📖 知识库主题

学业压力与倦怠 · 焦虑与恐慌 · 情绪低落与抑郁 · 校园心理健康资源 · 心理咨询转介 · 风险评估政策 · 人际关系与家庭 · 隐私边界与伦理 · 睡眠与自我关怀 · 适应与过渡期 · 考试季指导

## 🔒 数据说明

- 对话记录持久化在 MySQL,向量数据库存储于本地 `data/chroma_db/`
- 数据一致性由应用层控制,会话不存在时自动创建
- 日志输出到 `logs/app.log`,同时打印到容器控制台

## 🤝 贡献

欢迎提交 Issue 和 Pull Request.

## 📄 许可证

[MIT License](LICENSE)

---

<sub>本项目仅供学习交流,不构成任何医疗建议.如有心理危机请及时联系专业机构.</sub>
