import logging
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agents.state import AgentState
from app.core.llm import llm_default
from app.services.task_queue import get_task_queue
from app.agents.nodes.llm_utils import invoke_with_retry

logger = logging.getLogger(__name__)

RISK_PROMPT = """
你是一个心理危机干预评估专家(RiskGuardianAgent).
请根据用户的对话内容和提供的上下文,评估当前的风险等级.

只输出风险等级单词: low / medium / high / critical,不要包含任何其他文字.

示例: low
"""


async def risk_guardian_node(state: AgentState) -> dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages([
        ("system", RISK_PROMPT),
        ("human", "用户最新消息:{last_message}\n\n参考知识:{context}"),
    ])
    chain = prompt | llm_default | StrOutputParser()

    # 使用当前用户输入,而非 messages[-1]（可能是 AI 消息）
    last_message = state.get("current_user_input", "")

    try:
        result = await invoke_with_retry(
            chain, last_message=last_message, context=state.get("retrieved_context", "")
        )
        
        # 解析风险等级（处理 "low" 或 "风险等级: low" 等格式）
        first_line = result.strip().split("\n")[0].strip().lower()
        risk_level = first_line.split(':', 1)[1].strip() if ':' in first_line else first_line
    except Exception as e:
        logger.error(f"[RiskGuardianAgent] 风险评估失败: {e}", exc_info=True)
        risk_level = "low"

    if risk_level not in ["low", "medium", "high", "critical"]:
        logger.warning(f"[RiskGuardianAgent] 未识别的风险等级 '{risk_level}',降级为 low")
        risk_level = "low"

    logger.info(f"[RiskGuardianAgent] 风险等级: {risk_level}")

    # 如果 risk_level 为 high 或 critical,推入异步任务队列发送预警
    if risk_level in ["high", "critical"]:
        logger.warning(f"[RiskGuardianAgent] 检测到高风险,推入预警队列")
        await get_task_queue().enqueue(
            task_type="send_alert",
            payload={
                "user_id": state.get("user_id", 0),
                "session_id": state.get("session_id", 0),
                "risk_level": risk_level,
                "last_message": last_message,
                "target": "campus_crisis_center"
            }
        )

    return {"risk_level": risk_level}
