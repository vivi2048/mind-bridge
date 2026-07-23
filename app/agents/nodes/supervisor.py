import logging
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.agents.state import AgentState
from app.core.llm import llm_default
from app.core.config import settings
from app.agents.nodes.llm_utils import invoke_with_retry

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
async def supervisor_node(state: AgentState) -> dict[str, Any]:
    """
    SupervisorAgent 节点:负责意图识别与路由.
    仅根据当前用户输入分类,不发送完整历史消息以节省 token.
    """
    # 测试模式:强制所有请求触发 RAG
    if settings.force_rag:
        logger.debug("[SupervisorAgent] 测试模式:强制路由到 consult")
        return {"current_intent": "consult"}
    
    current_input = state.get("current_user_input", "")
    
    # 规则优先:快速识别明显意图(跳过 LLM 调用,提升响应速度)
    # 1. 风险关键词检测 (最高优先级)
    risk_keywords = [
        # 直接表达
        "自杀", "自残", "不想活", "去死", "跳楼", "割腕", "服药",
        "活不下去", "没有意义", "结束生命", "自我伤害", "想死",
        # 隐晦表达
        "消失", "离开这个世界", "看不到希望", "绝望", "解脱",
        "不如死了", "活着没意思", "想解脱", "一了百了",
        # 具体方法
        "安眠药", "农药", "上吊", "割脉",
        "死了更好", "出车祸", "是个负担", "遗书", "跳下去", "快疯了", "让我去死"
    ]
    if any(kw in current_input for kw in risk_keywords):
        logger.info("[SupervisorAgent] 识别到意图: risk (规则匹配)")
        return {"current_intent": "risk"}
    
    # 2. 心理咨询场景检测 (优先于 chat,避免混合场景误判)
    consult_keywords = [
        # 心理症状词
        "焦虑", "抑郁", "压力大", "失眠", "恐惧", "恐慌", "噩梦",
        "心情不好", "情绪低落", "睡不着", "学不进去",
        "注意力不集中", "记忆力下降", "烦躁", "易怒",
        # 情绪状态描述
        "想哭", "紧张", "发脾气", "后悔", "自责", "崩溃", "逃避",
        "没意思", "没意义", "迷茫", "孤独", "自卑", "失败",
        # 人际关系困扰
        "室友", "吵架", "失恋", "分手", "男朋友", "女朋友",
        # 行为问题
        "拖延"
    ]
    if any(kw in current_input for kw in consult_keywords):
        logger.info("[SupervisorAgent] 识别到意图: consult (规则匹配)")
        return {"current_intent": "consult"}
    
    # 3. 简单聊天模式检测
    chat_patterns = [
        # 问候语
        "你好", "在吗", "嗨", "早上好", "晚上好", "下午好",
        "你是谁", "你叫什么", "谢谢", "感谢", "再见", "拜拜",
        # 简单回应
        "嗯", "好的", "哦", "啊", "哈哈",
        # 非心理类话题
        "天气", "论文", "作业", "电影", "笑话", "好看", "计划",
        "聊天", "日记", "帮我写", "你能帮我"
    ]
    if any(pattern in current_input for pattern in chat_patterns):
        logger.info("[SupervisorAgent] 识别到意图: chat (规则匹配)")
        return {"current_intent": "chat"}
    
    # 3. 模型兜底:复杂问题才调用 LLM
    logger.debug("[SupervisorAgent] 规则未命中,调用 LLM 识别")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_PROMPT),
        ("human", "{input}"),
    ])

    chain = prompt | llm_default | StrOutputParser()

    try:
        # 调用 LLM 进行意图分类(仅传当前输入,不传历史)
        # invoke_with_retry 内部已处理限流 + 429 重试
        intent = await invoke_with_retry(chain, input=current_input)
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