from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from app.agents.state import AgentState
from app.core.config import settings

llm = ChatOpenAI(
    model=settings.llm_model_id,
    api_key=settings.api_key,
    base_url=settings.base_url,
    temperature=0.5,
)

COUNSELOR_PROMPT = """
你是 MindBridge 校园心理平台的专业心理咨询师（CounselorAgent）。
请综合前序节点提供的信息：
1. 知识库检索到的专业内容：{context}
2. 风险守卫节点的风控评估：风险等级为 {risk_level}

为用户提供专业、有深度、充满同理心的心理支持回复。
如果风险等级为 high 或 critical，请务必在回复中强烈建议用户立即寻求校园心理中心或专业医院的帮助，并提供 24 小时心理危机干预热线：400-161-9995。
"""


async def counselor_node(state: AgentState) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", COUNSELOR_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm

    response = await chain.ainvoke({
        "messages": state["messages"],
        "context": state.get("retrieved_context", "无"),
        "risk_level": state.get("risk_level", "low")
    })
    print("[CounselorAgent] 生成专业心理咨询回复")

    return {"messages": [response]}
