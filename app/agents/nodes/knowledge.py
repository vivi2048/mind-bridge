import logging
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from app.core.config import settings
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

embeddings = DashScopeEmbeddings(
    model=settings.embedding_model_id,
    dashscope_api_key=settings.api_key
)

vectorstore = Chroma(
    persist_directory=settings.chroma_persist_dir,
    embedding_function=embeddings
)


async def knowledge_node(state: AgentState) -> dict:
    """
    知识检索节点：执行动态 RAG。
    """
    logger.info("[KnowledgeAgent] 开始知识检索")
    
    # 1. 获取用户的最新提问
    user_query = state["current_user_input"]

    # 2. 执行向量检索，获取最相关的 Top-3 知识块
    retrieved_docs = vectorstore.similarity_search(user_query, k=3)

    # 3. 将检索到的知识块拼接成上下文字符串
    if retrieved_docs:
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        logger.info(f"[KnowledgeAgent] 检索到 {len(retrieved_docs)} 个相关知识块，共 {len(context)} 字符")
    else:
        context = ""
        logger.warning("[KnowledgeAgent] 未检索到相关知识")

    return {"retrieved_context": context}
