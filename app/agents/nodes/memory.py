from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.entities import ChatMessage  # 注意确认你的模型导入路径


async def memory_node(state: dict) -> dict:
    """
    记忆加载节点：从 MySQL 加载当前会话的历史消息。
    """
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    current_input = state.get("current_user_input")  # 获取当前用户输入

    print(f"[MemoryAgent] 正在加载用户 {user_id} 会话 {session_id} 的历史记忆...")

    if not session_id:
        return {}

    history_messages = []
    try:
        async with async_session_factory() as session:
            # 使用标准的 select(ChatMessage) 写法
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
            result = await session.execute(stmt)
            db_messages = result.scalars().all()

            # 将数据库记录转换为 LangChain 的 Message 对象
            for msg in db_messages:
                # 【防御性检查】确保从数据库捞出来的是合法的 ORM 对象
                if not hasattr(msg, "role"):
                    print(f"⚠️ [MemoryAgent] 跳过非法数据: {type(msg)}")
                    continue

                if msg.role == "user":
                    history_messages.append(HumanMessage(content=msg.content, id=f"db-{msg.id}"))
                elif msg.role == "assistant":
                    history_messages.append(AIMessage(content=msg.content, id=f"db-{msg.id}"))
    except Exception as e:
        print(f"[MemoryAgent] 加载历史记忆失败: {e}")

    history_messages.append(HumanMessage(content=current_input))
    print(f"[MemoryAgent] 成功加载 {len(history_messages) - 1} 条历史消息")
    return {"messages": history_messages}


async def save_memory_node(state: dict) -> dict:
    """
    记忆保存节点：将本轮最新的对话落盘到 MySQL。
    """
    session_id = state.get("session_id")
    messages = state.get("messages", [])

    # 至少需要 2 条消息（1条用户输入 + 1条AI回复）才进行保存
    if not session_id or len(messages) < 2:
        return {}

    # 提取最后两条消息作为本轮对话
    last_user_msg = messages[-2]
    last_ai_msg = messages[-1]

    try:
        async with async_session_factory() as session:
            # 保存用户消息
            user_msg_obj = ChatMessage(
                session_id=session_id,
                role="user",
                content=last_user_msg.content,
                intent=state.get("current_intent")
            )
            session.add(user_msg_obj)

            # 保存 AI 消息
            ai_msg_obj = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=last_ai_msg.content,
                intent=state.get("current_intent")
            )
            session.add(ai_msg_obj)

            await session.commit()

    except Exception as e:
        print(f"[SaveMemory] 保存对话失败: {e}")
        # 注意：这里不要抛出异常，以免阻断 AI 返回给用户

    print(f"[SaveMemory] 会话 {session_id} 对话已保存")
    return {}
