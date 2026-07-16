import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from app.agents.state import AgentState
from app.core.config import settings
from app.services.task_queue import task_queue

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    model=settings.llm_model_id,
    api_key=settings.api_key,
    base_url=settings.base_url,
    temperature=0,
)

RISK_PROMPT = """
你是一个心理危机干预评估专家（RiskGuardianAgent）。
请根据用户的对话内容和提供的上下文，评估当前的风险等级。
仅输出一个单词：low, medium, high, 或 critical。
不要包含任何解释。
"""


async def risk_guardian_node(state: AgentState) -> dict:
    logger.info("[RiskGuardianAgent] 开始风险评估")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", RISK_PROMPT),
        ("human", "用户最新消息：{last_message}\n\n参考知识：{context}"),
    ])
    chain = prompt | llm | StrOutputParser()

    last_message = state["messages"][-1].content if state["messages"] else ""

    risk_level = await chain.ainvoke({
        "last_message": last_message,
        "context": state.get("retrieved_context", "")
    })
    risk_level = risk_level.strip().lower()

    if risk_level not in ["low", "medium", "high", "critical"]:
        logger.warning(f"[RiskGuardianAgent] 未识别的风险等级 '{risk_level}'，降级为 low")
        risk_level = "low"

    logger.info(f"[RiskGuardianAgent] 评估风险等级: {risk_level}")

    # 如果 risk_level 为 high 或 critical，在此处推入异步任务队列发送预警
    if risk_level in ["high", "critical"]:
        logger.warning(f"[RiskGuardianAgent] 检测到高风险，推入预警队列")
        await task_queue.enqueue(
            task_type="send_alert",
            payload={
                "user_id": state.get("user_id", "unknown"),
                "session_id": state.get("session_id", "unknown"),
                "risk_level": risk_level,
                "last_message": last_message
            }
        )

    return {"risk_level": risk_level}
