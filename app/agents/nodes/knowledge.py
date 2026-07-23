import asyncio
import logging
from typing import Any
from langchain_chroma import Chroma
from app.core.embeddings import create_embeddings
from app.core.config import settings
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

# 延迟初始化:在首次调用时创建,避免 import 时的副作用
_embeddings: Any = None
_vectorstore: Chroma | None = None


def _get_vectorstore() -> Chroma:
    """获取向量存储实例(懒加载)"""
    global _embeddings, _vectorstore
    if _vectorstore is None:
        logger.debug("[KnowledgeAgent] 初始化 Embedding 和 ChromaDB...")
        _embeddings = create_embeddings()
        _vectorstore = Chroma(
            persist_directory=settings.chroma_persist_dir,
            embedding_function=_embeddings,
            collection_name=settings.chroma_collection_name,
        )
    return _vectorstore


async def knowledge_node(state: AgentState) -> dict[str, Any]:
    """
    知识检索节点:执行动态 RAG.
    """
    # 1. 获取用户的最新提问
    user_query = state["current_user_input"]

    # 2. 执行 MMR 检索(兼顾相关性和多样性),获取 Top-3 知识块
    #    fetch_k=10 先粗筛 10 个候选,lambda_mult=0.5 平衡相关性与多样性
    #    使用 asyncio.to_thread 将同步的 Chroma 搜索移到线程池,避免阻塞事件循环
    vectorstore = _get_vectorstore()
    retrieved_docs = await asyncio.to_thread(
        vectorstore.max_marginal_relevance_search,
        user_query, k=3, fetch_k=10, lambda_mult=0.5
    )

    # 3. 将检索到的知识块拼接成上下文字符串
    if retrieved_docs:
        context = "\n\n".join([doc.page_content for doc in retrieved_docs])
        sources = [doc.metadata.get("source", "unknown") for doc in retrieved_docs]
        logger.info(f"[KnowledgeAgent] 检索到 {len(retrieved_docs)} 个知识块,来源: {', '.join(set(sources))}")
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc.metadata.get("source", "unknown")
            preview = doc.page_content[:200].replace("\n", " ")
            logger.debug(f"[KnowledgeAgent]   [{i}] {source}: {preview}...")
    else:
        context = ""
        logger.warning("[KnowledgeAgent] 未检索到相关知识")

    return {"retrieved_context": context}
