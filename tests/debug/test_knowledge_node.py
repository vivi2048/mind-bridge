import logging
from app.agents.nodes.knowledge import vectorstore  # 直接导入节点里的向量库实例
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# 直接用一段测试文本查询
test_query = "大学生压力管理"
docs = vectorstore.similarity_search(test_query, k=3)

logger.info(f"直接查询结果数量: {len(docs)}")
for i, doc in enumerate(docs, 1):
    logger.info(f"\n--- 结果 {i} ---")
    logger.info(f"Source: {doc.metadata.get('source', '?')}")
    logger.info(f"H1: {doc.metadata.get('H1', 'N/A')}")
    logger.info(f"H2: {doc.metadata.get('H2', 'N/A')}")
    logger.info(f"H3: {doc.metadata.get('H3', 'N/A')}")
    logger.info(f"Content:\n{doc.page_content}")