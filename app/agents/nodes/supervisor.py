import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agents.state import AgentState
from app.core.llm import llm_default

logger = logging.getLogger(__name__)

# 2. 定义路由 Prompt
SUPERVISOR_PROMPT = """
你是一个校园心理健康平台的意图路由专家(SupervisorAgent).
你的唯一任务是分析用户的输入,并将其精准分类为以下三种意图之一:

1. `chat`: 普通日常闲聊、打招呼、无明确心理诉求的对话.
2. `consult`: 明确的心理咨询、心理知识问答、情绪困扰求助(需要检索专业知识).
3. `risk`: 表达出自杀、自残、严重抑郁、伤害他人等高风险倾向,或处于紧急心理危机中.

请仅输出一个单词(chat, consult 或 risk),不要包含任何解释或标点符号.
"""


# type: ignore[arg-type]
# 3. 构建 Supervisor 节点函数
async def supervisor_node(state: AgentState) -> dict:
    """
    SupervisorAgent 节点:负责意图识别与路由.
    仅根据当前用户输入分类,不发送完整历史消息以节省 token.
    """
    logger.info("[SupervisorAgent] 开始意图识别")
    
    current_input = state.get("current_user_input", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_PROMPT),
        ("human", "{input}"),
    ])

    chain = prompt | llm_default | StrOutputParser()

    try:
        # 调用 LLM 进行意图分类（仅传当前输入,不传历史）
        intent = await chain.ainvoke({"input": current_input})
        intent = intent.strip().lower()
    except Exception as e:
        logger.error(f"[SupervisorAgent] LLM 意图分类失败: {e}", exc_info=True)
        intent = "chat"  # 失败时兜底为普通聊天

    # 安全兜底:如果 LLM 输出了非预期的值,默认降级为普通聊天
    if intent not in ["chat", "consult", "risk"]:
        logger.warning(f"[SupervisorAgent] 未识别的意图 '{intent}',降级为 chat")
        intent = "chat"

    logger.info(f"[SupervisorAgent] 识别到意图: {intent}")

    # 将识别结果写回全局状态
    return {"current_intent": intent}
