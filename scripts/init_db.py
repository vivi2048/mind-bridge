import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.models.entities import Base


# 自定义 unraisable hook 来抑制 aiomysql 的垃圾回收警告
def _suppress_event_loop_closed(unraisable):
    """抑制 aiomysql 连接在事件循环关闭后的垃圾回收警告"""
    if unraisable.exc_type is RuntimeError and "Event loop is closed" in str(unraisable.exc_value):
        return  # 忽略这个特定的警告
    # 其他异常交给默认处理
    sys.__unraisablehook__(unraisable)


async def init_database():
    """
    异步初始化数据库：
    1. 确保数据库字符集为 utf8mb4（解决中文和 Emoji 存储问题）
    2. 根据 Base 中定义的模型自动创建所有表
    """
    # 创建独立的引擎
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    print("正在连接数据库并初始化表结构...")
    try:
        async with engine.begin() as conn:
            # 1. 强制修改当前数据库的默认字符集（防止新建表时继承旧字符集）
            await conn.execute(text("ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))

            # 2. 创建所有表（如果表已存在则跳过）
            # noinspection PyTypeChecker
            await conn.run_sync(Base.metadata.create_all)

        print("数据库表结构初始化成功！")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
    finally:
        # 确保在事件循环关闭前正确清理
        await engine.dispose()


if __name__ == "__main__":
    # 设置自定义 hook 来抑制 aiomysql 的垃圾回收警告
    sys.unraisablehook = _suppress_event_loop_closed
    
    # 运行异步初始化函数
    asyncio.run(init_database())