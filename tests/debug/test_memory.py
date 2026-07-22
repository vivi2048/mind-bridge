import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.entities import ChatMessage
from langchain_core.messages import HumanMessage, AIMessage


async def test_memory_node():
    test_session_id = 100101

    print(f"测试 session_id={test_session_id} 的历史消息加载...")

    async with async_session_factory() as session:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == test_session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await session.execute(stmt)
        db_messages = result.scalars().all()

    print(f"查询到 {len(db_messages)} 条消息")

    history_messages = []
    for i, msg in enumerate(db_messages, 1):
        # 防御性检查:如果真的是 int,就跳过并警告
        if isinstance(msg, int):
            print(f"  [{i}] ⚠ int 类型,跳过")
            continue

        try:
            role = msg.role
            content = msg.content[:50]
            print(f"  [{i}] {role}: {content}...")

            if role == "user":
                history_messages.append(HumanMessage(content=msg.content, id=f"db-{msg.id}"))
            elif role == "assistant":
                history_messages.append(AIMessage(content=msg.content, id=f"db-{msg.id}"))

        except AttributeError as e:
            print(f"  [{i}] ✗ 属性错误: {e}")

    print(f"\n转换后 LangChain 消息: {len(history_messages)} 条")
    return history_messages


if __name__ == "__main__":
    asyncio.run(test_memory_node())
