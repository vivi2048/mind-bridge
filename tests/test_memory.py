import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.entities import ChatMessage  # 确保路径正确
from langchain_core.messages import HumanMessage, AIMessage


async def test_memory_node():
    # 替换为你实际存在的 session_id
    test_session_id = 100101

    print(f"正在测试 session_id={test_session_id} 的历史消息加载...")

    async with async_session_factory() as session:
        # 【推荐写法】使用 select(ChatMessage) 代替 __table__.select()
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == test_session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await session.execute(stmt)
        db_messages = result.scalars().all()

    print(db_messages)
    print(f"原始查询结果类型: {type(db_messages)}")
    print(f"列表长度: {len(db_messages)}")

    history_messages = []
    for i, msg in enumerate(db_messages):
        print(f"--- 第 {i + 1} 条数据 ---")
        print(f"  数据类型: {type(msg)}")
        print(f"  数据内容: {msg}")

        # 防御性检查：如果真的是 int，就跳过并警告
        if isinstance(msg, int):
            print(f"警告: 发现了 int 类型的数据，可能是主键 ID！")
            continue

        # 尝试访问 role 属性
        try:
            print(f"  角色(role): {msg.role}")
            print(f"  内容(content): {msg.content[:50]}...")

            if msg.role == "user":
                history_messages.append(HumanMessage(content=msg.content, id=f"db-{msg.id}"))
            elif msg.role == "assistant":
                history_messages.append(AIMessage(content=msg.content, id=f"db-{msg.id}"))

        except AttributeError as e:
            print(f"报错: {e}")

    print("\n最终转换后的 LangChain 消息数量:", len(history_messages))
    return history_messages


if __name__ == "__main__":
    asyncio.run(test_memory_node())