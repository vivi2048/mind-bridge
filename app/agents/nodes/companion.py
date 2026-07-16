from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from app.core.config import settings

llm = ChatOpenAI(
    model=settings.llm_model_id,
    api_key=settings.api_key,
    base_url=settings.base_url,
    temperature=0.7,
)

COMPANION_PROMPT = """
你是 MindBridge 校园心理平台的陪伴助手（CompanionAgent）。
你的性格温暖、阳光、有耐心。
用户只是想找人聊天、倾诉日常或打招呼，请用朋友般的口吻与他们交流。
不要给出专业的心理诊断，只需提供情感上的支持和陪伴。
"""


async def companion_node(state: dict) -> dict:
    prompt = ChatPromptTemplate.from_messages([
        ("system", COMPANION_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])
    chain = prompt | llm

    response = await chain.ainvoke({"messages": state["messages"]})
    print("[CompanionAgent] 完成日常陪伴回复")

    # 将 AI 的回复追加到全局消息列表中
    return {"messages": [response]}
