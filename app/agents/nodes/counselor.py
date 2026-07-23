import logging
from typing import Any
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.agents.state import AgentState
from app.core.llm import llm_balanced
from app.agents.nodes.llm_utils import FALLBACK_MESSAGE, invoke_with_retry

logger = logging.getLogger(__name__)

COUNSELOR_PROMPT = """
你是 MindBridge 校园心理平台的专业心理咨询师(CounselorAgent).
请综合前序节点提供的信息:
1. 知识库检索到的专业内容:{context}
2. 风险守卫节点的风控评估:风险等级为 {risk_level}

为用户提供专业、有深度、充满同理心的心理支持回复.
如果风险等级为 high 或 critical,请务必在回复中强烈建议用户立即寻求校园心理中心或专业医院的帮助.
"""


async def counselor_node(state: AgentState) -> dict[str, Any]:
    risk_level = state.get('risk_level', 'unknown')
    prompt = ChatPromptTemplate.from_messages([
        ("system", COUNSELOR_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm_balanced

    try:
        response = await invoke_with_retry(
            chain,
            messages=state["messages"],
            context=state.get("retrieved_context", "无"),
            risk_level=risk_level,
        )
        logger.debug(f"[CounselorAgent] 咨询回复完成, risk_level={risk_level}")
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"[CounselorAgent] LLM 调用失败: {e}", exc_info=True)
        return {"messages": [AIMessage(content=FALLBACK_MESSAGE)]}
