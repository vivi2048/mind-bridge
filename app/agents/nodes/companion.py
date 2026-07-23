import logging
from typing import Any
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.core.llm import llm_creative
from app.agents.nodes.llm_utils import FALLBACK_MESSAGE, invoke_with_retry

logger = logging.getLogger(__name__)

COMPANION_PROMPT = """
你是 MindBridge 校园心理平台的陪伴助手(CompanionAgent).
你的性格温暖、阳光、有耐心.
用户只是想找人聊天、倾诉日常或打招呼,请用朋友般的口吻与他们交流.
不要给出专业的心理诊断,只需提供情感上的支持和陪伴.
"""


async def companion_node(state: dict[str, Any]) -> dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages([
        ("system", COMPANION_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm_creative

    try:
        response = await invoke_with_retry(chain, messages=state["messages"])
        logger.debug("[CompanionAgent] 陪伴回复完成")
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"[CompanionAgent] LLM 调用失败: {e}", exc_info=True)
        return {"messages": [AIMessage(content=FALLBACK_MESSAGE)]}
