from app.agents.nodes.knowledge import vectorstore

# 直接用一段测试文本查询
test_query = "大学生压力管理"
docs = vectorstore.similarity_search(test_query, k=3)

print(f"查询: {test_query}")
print(f"结果数量: {len(docs)}")
for i, doc in enumerate(docs, 1):
    source = doc.metadata.get("source", "?")
    h1 = doc.metadata.get("H1", "N/A")
    print(f"\n[{i}] {source} > {h1}")
    print(f"    {doc.page_content[:200]}...")
