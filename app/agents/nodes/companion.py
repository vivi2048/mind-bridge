import logging
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.core.llm import llm_creative

logger = logging.getLogger(__name__)

COMPANION_PROMPT = """
你是 MindBridge 校园心理平台的陪伴助手(CompanionAgent).
你的性格温暖、阳光、有耐心.
用户只是想找人聊天、倾诉日常或打招呼,请用朋友般的口吻与他们交流.
不要给出专业的心理诊断,只需提供情感上的支持和陪伴.
"""


async def companion_node(state: dict) -> dict:
    logger.info("[CompanionAgent] 开始生成日常陪伴回复")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", COMPANION_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm_creative

    try:
        response = await chain.ainvoke({"messages": state["messages"]})
        logger.info("[CompanionAgent] 完成日常陪伴回复")
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"[CompanionAgent] LLM 调用失败: {e}", exc_info=True)
        fallback = AIMessage(content="抱歉,我这边暂时遇到了一点问题,不过我还在的.你愿意再和我说说吗？")
        return {"messages": [fallback]}
