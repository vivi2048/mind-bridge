from typing import TypedDict, Annotated, List, Literal, Optional

from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    LangGraph 的全局状态定义.
    除了对话历史,还应包含贯穿整个工作流的生命周期标识和业务状态.
    """
    # 1. 对话消息历史 (使用 LangGraph 内置的 add_messages reducer,自动处理消息追加)
    messages: Annotated[List, add_messages]

    # 2. 核心业务标识 (必须补充)
    user_id: int          # 触发对话的用户 ID
    session_id: int       # 当前对话的会话 ID (用于隔离不同对话上下文)

    # 3. 当前识别的意图 (由 SupervisorAgent 决定)
    current_intent: Optional[Literal["chat", "consult", "risk"]]

    # 4. 风险评估信息 (由 RiskGuardianAgent 写入)
    risk_level: Optional[str]
    risk_reason: Optional[str]

    # 5. 检索到的知识上下文 (由 KnowledgeAgent 写入)
    retrieved_context: Optional[str]

    # 6. 用户提问
    current_user_input: str

    # 7. 历史消息计数 (由 MemoryAgent 写入,供 SaveMemoryAgent 使用)
    _history_count: int