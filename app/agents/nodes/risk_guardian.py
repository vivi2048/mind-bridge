import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agents.state import AgentState
from app.core.llm import llm_default
from app.services.task_queue import task_queue

logger = logging.getLogger(__name__)

RISK_PROMPT = """
你是一个心理危机干预评估专家(RiskGuardianAgent).
请根据用户的对话内容和提供的上下文,评估当前的风险等级.
输出格式要求:
第一行输出风险等级: low, medium, high, 或 critical
第二行输出风险评估理由(一句话概括)
"""


async def risk_guardian_node(state: AgentState) -> dict:
    logger.info("[RiskGuardianAgent] 开始风险评估")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", RISK_PROMPT),
        ("human", "用户最新消息:{last_message}\n\n参考知识:{context}"),
    ])
    chain = prompt | llm_default | StrOutputParser()

    # 使用当前用户输入,而非 messages[-1]（可能是 AI 消息）
    last_message = state.get("current_user_input", "")

    try:
        result = await chain.ainvoke({
            "last_message": last_message,
            "context": state.get("retrieved_context", "")
        })
        lines = result.strip().split("\n", 1)
        risk_level = lines[0].strip().lower()
        risk_reason = lines[1].strip() if len(lines) > 1 else ""
    except Exception as e:
        logger.error(f"[RiskGuardianAgent] 风险评估失败: {e}", exc_info=True)
        risk_level = "low"
        risk_reason = f"风险评估异常,降级为 low: {e}"

    if risk_level not in ["low", "medium", "high", "critical"]:
        logger.warning(f"[RiskGuardianAgent] 未识别的风险等级 '{risk_level}',降级为 low")
        risk_level = "low"

    logger.info(f"[RiskGuardianAgent] 评估风险等级: {risk_level}, 原因: {risk_reason}")

    # 如果 risk_level 为 high 或 critical,推入异步任务队列发送预警
    if risk_level in ["high", "critical"]:
        logger.warning(f"[RiskGuardianAgent] 检测到高风险,推入预警队列")
        await task_queue.enqueue(
            task_type="send_alert",
            payload={
                "user_id": state.get("user_id", 0),
                "session_id": state.get("session_id", 0),
                "risk_level": risk_level,
                "last_message": last_message,
                "target": "campus_crisis_center"
            }
        )

    return {"risk_level": risk_level, "risk_reason": risk_reason}
