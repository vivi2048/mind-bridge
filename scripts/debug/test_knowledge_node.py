from app.agents.nodes.knowledge import vectorstore  # 直接导入节点里的向量库实例

# 直接用一段测试文本查询
test_query = "大学生压力管理"
docs = vectorstore.similarity_search(test_query, k=3)

print(f"直接查询结果数量: {len(docs)}")
for doc in docs:
    print(f"- {doc.page_content[:50]}...")