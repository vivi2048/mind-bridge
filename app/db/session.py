from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# 1. 创建异步数据库引擎
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # 如果 debug=True，会在控制台打印生成的 SQL 语句，方便调试
    pool_pre_ping=True,
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 允许超出 pool_size 的最大并发连接数
)

# 2. 创建异步会话工厂
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def dispose_engine():
    """
    关闭数据库引擎，释放所有连接资源。
    应在应用关闭时调用。
    """
    await async_engine.dispose()
