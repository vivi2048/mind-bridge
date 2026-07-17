import logging
from typing import cast
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.entities import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


async def memory_node(state: dict) -> dict:
    """
    记忆加载节点：从 MySQL 加载当前会话的历史消息。
    """
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    current_input = state.get("current_user_input")

    logger.info(f"[MemoryAgent] 加载用户 {user_id} 会话 {session_id} 的历史记忆")

    if not session_id:
        # 没有 session_id，只返回当前输入
        return {"messages": [HumanMessage(content=current_input)]}

    history_messages = []
    history_count = 0
    
    try:
        async with async_session_factory() as session:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
            result = await session.execute(stmt)
            db_messages = result.scalars().all()

            # 将数据库记录转换为 LangChain 的 Message 对象
            for msg in db_messages:
                if not hasattr(msg, "role"):
                    logger.warning(f"[MemoryAgent] 跳过非法数据: {type(msg)}")
                    continue

                if msg.role == "user":
                    history_messages.append(HumanMessage(content=msg.content, id=f"db-{cast(int, msg.id)}"))
                    history_count += 1
                elif msg.role == "assistant":
                    history_messages.append(AIMessage(content=msg.content, id=f"db-{cast(int, msg.id)}"))
                    history_count += 1
    except Exception as e:
        logger.error(f"[MemoryAgent] 加载历史记忆失败: {e}", exc_info=True)

    # 添加当前用户输入
    history_messages.append(HumanMessage(content=current_input))
    
    logger.info(f"[MemoryAgent] 成功加载 {history_count} 条历史消息，加上当前输入共 {len(history_messages)} 条")
    
    # 记录历史消息数量，供 save_memory_node 使用（只计算从 DB 加载的数量，不含当前输入）
    return {
        "messages": history_messages,
        "_history_count": history_count
    }


async def save_memory_node(state: dict) -> dict:
    """
    记忆保存节点：将本轮最新的对话落盘到 MySQL。
    如果会话不存在，则自动创建。
    """
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    messages = state.get("messages", [])
    history_count = state.get("_history_count", 0)
    current_intent = state.get("current_intent")

    logger.info(f"[SaveMemory] 开始保存: session_id={session_id}, 总消息数={len(messages)}, history_count={history_count}")

    if not session_id or not messages:
        logger.warning("[SaveMemory] 跳过保存: session_id 或 messages 为空")
        return {}

    try:
        async with async_session_factory() as session:
            # 确保会话存在（自动创建）
            existing = await session.get(ChatSession, session_id)
            if not existing:
                logger.info(f"[SaveMemory] 会话 {session_id} 不存在，自动创建")
                new_session = ChatSession(id=cast(int, session_id), user_id=cast(int, user_id))
                session.add(new_session)
                await session.flush()  # 先落盘，确保外键可用

            # 找到本轮新增的消息（历史消息之后的部分）
            new_messages = messages[history_count:] if history_count < len(messages) else []
            
            if not new_messages:
                logger.info("[SaveMemory] 没有新消息需要保存")
                return {}

            # 提取本轮的用户消息和 AI 回复
            last_user_msg = None
            last_ai_msg = None
            
            for msg in reversed(new_messages):
                if isinstance(msg, HumanMessage) and last_user_msg is None:
                    last_user_msg = msg
                elif isinstance(msg, AIMessage) and last_ai_msg is None:
                    last_ai_msg = msg
                
                if last_user_msg and last_ai_msg:
                    break

            # 保存用户消息
            if last_user_msg:
                user_msg_obj = ChatMessage(
                    session_id=cast(int, session_id),
                    role="user",
                    content=cast(str, last_user_msg.content),
                    intent=current_intent
                )
                session.add(user_msg_obj)

            # 保存 AI 消息
            if last_ai_msg:
                ai_msg_obj = ChatMessage(
                    session_id=cast(int, session_id),
                    role="assistant",
                    content=cast(str, last_ai_msg.content),
                    intent=current_intent
                )
                session.add(ai_msg_obj)

            await session.commit()
            
            saved_count = (1 if last_user_msg else 0) + (1 if last_ai_msg else 0)
            logger.info(f"[SaveMemory] 会话 {session_id} 保存了 {saved_count} 条消息")

    except Exception as e:
        logger.error(f"[SaveMemory] 保存对话失败: {e}", exc_info=True)

    return {}
