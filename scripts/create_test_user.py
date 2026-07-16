import asyncio

from passlib.context import CryptContext
from sqlalchemy import select
from app.db.session import async_session_factory, async_engine
from app.models.entities import UserAccount  # 确保路径与你的项目一致

# 配置密码加密上下文（与登录验证时保持一致）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_test_user():
    # 创建新的测试用户
    test_user = UserAccount(
        id=1001,
        username="test1",
        hashed_password=pwd_context.hash("test"),
        role="student"
    )
    async with async_session_factory() as session:
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

    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_user())
