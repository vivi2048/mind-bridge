"""
测试工具模块:提取 run_tests.py 和 load_test.py 的公共逻辑.
"""
import logging
from typing import Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

# 测试专用 session_id 起始值,避免与真实数据冲突
TEST_SESSION_START = 900000

_session_counter = 0


def generate_session_id() -> int:
    """生成唯一的测试 session_id (900000+)"""
    global _session_counter
    _session_counter += 1
    return TEST_SESSION_START + _session_counter


def calculate_percentiles(data: list) -> Dict[str, float]:
    """计算百分位数 (P50, P90, P95, P99)"""
    if not data:
        return {"P50": 0, "P90": 0, "P95": 0, "P99": 0}

    sorted_data = sorted(data)
    n = len(sorted_data)

    def percentile(p):
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < n else f
        d = k - f
        return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])

    return {
        "P50": percentile(50),
        "P90": percentile(90),
        "P95": percentile(95),
        "P99": percentile(99),
    }


async def clean_test_data():
    """
    清理数据库中的测试数据(session_id >= 900000).
    覆盖: ChatMessage, ChatSession, RiskEvent, AsyncTask.
    """
    if not settings.database_url:
        print("DATABASE_URL 未配置,跳过数据清理")
        return

    from sqlalchemy import select, delete
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from app.models.entities import ChatSession, ChatMessage, RiskEvent, AsyncTask

    try:
        engine = create_async_engine(settings.database_url, echo=False)
    except Exception as e:
        print(f"数据库连接失败,跳过清理: {e}")
        return

    try:
        async with AsyncSession(engine) as session:
            # 1. 清理测试会话及其消息
            result = await session.execute(
                select(ChatSession).where(ChatSession.id >= TEST_SESSION_START)
            )
            test_sessions = result.scalars().all()
            session_count = len(test_sessions)

            message_count = 0
            for s in test_sessions:
                msg_result = await session.execute(
                    select(ChatMessage).where(ChatMessage.session_id == s.id)
                )
                messages = msg_result.scalars().all()
                message_count += len(messages)

                await session.execute(
                    delete(ChatMessage).where(ChatMessage.session_id == s.id)
                )

            await session.execute(
                delete(ChatSession).where(ChatSession.id >= TEST_SESSION_START)
            )

            # 2. 清理测试风险事件
            risk_result = await session.execute(
                select(RiskEvent).where(RiskEvent.session_id >= TEST_SESSION_START)
            )
            risk_count = len(risk_result.scalars().all())

            await session.execute(
                delete(RiskEvent).where(RiskEvent.session_id >= TEST_SESSION_START)
            )

            # 3. 清理异步任务(通过 payload 中的 session_id 过滤)
            all_tasks = (await session.execute(select(AsyncTask))).scalars().all()
            task_count = 0

            for task in all_tasks:
                payload = task.payload or {}
                task_session_id = payload.get('session_id', 0)
                if isinstance(task_session_id, int) and task_session_id >= TEST_SESSION_START:
                    await session.execute(
                        delete(AsyncTask).where(AsyncTask.id == task.id)
                    )
                    task_count += 1

            await session.commit()
            logger.info(
                f"✓ 已清理测试数据: 会话{session_count}个, "
                f"消息{message_count}条, 风险事件{risk_count}条, 任务{task_count}条"
            )
    except Exception as e:
        logger.error(f"清理测试数据失败: {e}", exc_info=True)
    finally:
        await engine.dispose()
