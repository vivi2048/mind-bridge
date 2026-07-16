import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from app.db.session import async_engine
from app.models.entities import Base


async def init_database(engine: AsyncEngine):
    """
    异步初始化数据库：
    1. 确保数据库字符集为 utf8mb4（解决中文和 Emoji 存储问题）
    2. 根据 Base 中定义的模型自动创建所有表
    """
    print("🚀 正在连接数据库并初始化表结构...")
    try:
        async with engine.begin() as conn:
            # 1. 强制修改当前数据库的默认字符集（防止新建表时继承旧字符集）
            await conn.execute(text("ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))

            # 2. 创建所有表（如果表已存在则跳过）
            # noinspection PyTypeChecker
            await conn.run_sync(Base.metadata.create_all)

        print("✅ 数据库表结构初始化成功！")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
    finally:
        # 初始化完成后，关闭数据库引擎，释放连接
        await engine.dispose()


if __name__ == "__main__":
    # 运行异步初始化函数
    asyncio.run(init_database(async_engine))