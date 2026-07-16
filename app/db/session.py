from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# 1. 创建异步数据库引擎
# pool_pre_ping=True: 在从连接池获取连接前，先发送一个轻量级 SQL 测试连接是否存活。
# 这能有效防止 MySQL 长时间空闲后断开连接导致的 "MySQL server has gone away" 错误。
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # 如果 debug=True，会在控制台打印生成的 SQL 语句，方便调试
    pool_pre_ping=True,
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 允许超出 pool_size 的最大并发连接数
)

# 2. 创建异步会话工厂
# expire_on_commit=False: 提交后不自动过期对象属性。
# 这在异步环境中非常重要，可以防止在后台任务或返回响应时，因为懒加载（Lazy Load）触发异步 IO 而报错。
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 4. 定义 FastAPI 的依赖项 (Dependency)
# 在路由函数中通过 `db: AsyncSession = Depends(get_db)` 注入
async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """
    获取数据库会话的依赖项。
    确保每个请求使用独立的会话，并在请求结束后安全关闭。
    """
    async with async_session_factory() as session:
        try:
            yield session
            # 如果没有异常，正常提交事务（由具体的业务代码决定何时 commit）
        except Exception:
            # 如果发生异常，回滚事务
            await session.rollback()
            raise
        finally:
            # 无论成功与否，最终关闭会话，将连接归还给连接池
            await session.close()
