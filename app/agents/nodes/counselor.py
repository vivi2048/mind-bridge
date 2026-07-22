import asyncio
import logging
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.agents.state import AgentState
from app.core.llm import llm_balanced
from app.core.rate_limiter import llm_rate_limiter

logger = logging.getLogger(__name__)

COUNSELOR_PROMPT = """
你是 MindBridge 校园心理平台的专业心理咨询师(CounselorAgent).
请综合前序节点提供的信息:
1. 知识库检索到的专业内容:{context}
2. 风险守卫节点的风控评估:风险等级为 {risk_level}

为用户提供专业、有深度、充满同理心的心理支持回复.
如果风险等级为 high 或 critical,请务必在回复中强烈建议用户立即寻求校园心理中心或专业医院的帮助,并提供 24 小时心理危机干预热线:400-161-9995.
"""


async def counselor_node(state: AgentState) -> dict:
    risk_level = state.get('risk_level', 'unknown')
    prompt = ChatPromptTemplate.from_messages([
        ("system", COUNSELOR_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm_balanced

    try:
        # 使用限流器防止触发上游 API 速率限制
        await llm_rate_limiter.acquire()
        response = await chain.ainvoke({
            "messages": state["messages"],
            "context": state.get("retrieved_context", "无"),
            "risk_level": risk_level
        })
        logger.debug(f"[CounselorAgent] 咨询回复完成, risk_level={risk_level}")
        return {"messages": [response]}
    except Exception as e:
        # 如果是 429 限流错误,等待后重试一次
        if "429" in str(e) or "RateLimit" in str(e):
            logger.warning(f"[CounselorAgent] 触发限流, 5s 后重试")
            await asyncio.sleep(5)
            try:
                await llm_rate_limiter.acquire()
                response = await chain.ainvoke({
                    "messages": state["messages"],
                    "context": state.get("retrieved_context", "无"),
                    "risk_level": risk_level
                })
                logger.debug(f"[CounselorAgent] 重试成功, risk_level={risk_level}")
                return {"messages": [response]}
            except Exception as retry_error:
                logger.error(f"[CounselorAgent] 重试失败: {retry_error}")
        
        logger.error(f"[CounselorAgent] LLM 调用失败: {e}", exc_info=True)
        fallback = AIMessage(content="感谢你的信任.我这边暂时遇到了一点技术问题,但你的感受对我来说很重要.如果现在不方便,我们可以稍后再聊,你也可以随时拨打 24 小时心理危机干预热线:400-161-9995.")
        return {"messages": [fallback]}
