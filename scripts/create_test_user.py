import asyncio
import sys

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.entities import UserAccount

# 配置密码加密上下文（与登录验证时保持一致）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 自定义 unraisable hook 来抑制 aiomysql 的垃圾回收警告
def _suppress_event_loop_closed(unraisable):
    """抑制 aiomysql 连接在事件循环关闭后的垃圾回收警告"""
    if unraisable.exc_type is RuntimeError and "Event loop is closed" in str(unraisable.exc_value):
        return  # 忽略这个特定的警告
    # 其他异常交给默认处理
    sys.__unraisablehook__(unraisable)


async def create_test_user():
    # 创建独立的引擎和会话
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    try:
        # 创建新的测试用户
        test_user = UserAccount(
            id=1001,
            username="test1",
            hashed_password=pwd_context.hash("test"),
            role="student"
        )
        
        async with async_session() as session:
            # 1. 检查用户是否已存在，避免重复创建报错
            stmt = select(UserAccount).where(UserAccount.username == test_user.username)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"用户 'test' 已存在，ID: {existing_user.id}")
                return

            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)

            print(f"测试用户创建成功！")
    finally:
        # 确保在事件循环关闭前正确清理
        await engine.dispose()


if __name__ == "__main__":
    # 设置自定义 hook 来抑制 aiomysql 的垃圾回收警告
    sys.unraisablehook = _suppress_event_loop_closed
    
    asyncio.run(create_test_user())
