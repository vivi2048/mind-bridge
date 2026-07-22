import json
import asyncio
import logging
from redis.asyncio import Redis
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.entities import AsyncTask, TaskStatus
from app.services.risk_tools import RISK_TOOL_REGISTRY
from app.core.config import settings

logger = logging.getLogger(__name__)

REDIS_QUEUE_KEY = "mindbridge:task_queue"
MAX_RETRIES = 3


class TaskQueue:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def enqueue(self, task_type: str, payload: dict):
        """
        将任务推入 Redis 队列,并在数据库创建初始记录.
        (由 RiskGuardianAgent 调用)
        """
        async with async_session_factory() as session:
            # 写入 MySql
            task = AsyncTask(task_type=task_type, payload=payload, status=TaskStatus.PENDING)
            session.add(task)
            await session.commit()
            await session.refresh(task)

            # 将数据库 ID 作为消息推入队列
            await self.redis.rpush(REDIS_QUEUE_KEY, json.dumps({"task_id": task.id}))
            logger.info(f"[TaskQueue] 任务 {task.id} ({task_type}) 已入队")

    async def process_task(self, task_id: int):
        """
        执行单个任务,包含状态更新和重试逻辑.
        """
        async with async_session_factory() as session:
            # 1. 获取任务记录
            result = await session.execute(select(AsyncTask).where(AsyncTask.id == task_id))
            task = result.scalar_one_or_none()

            if not task or task.status == TaskStatus.SUCCESS:
                return  # 任务不存在或已成功,跳过

            # 2. 更新状态为执行中
            # task.status = TaskStatus.RUNNING
            # await session.commit()

            try:
                # 3. 查找并执行风险工具
                tool_func = RISK_TOOL_REGISTRY.get(task.task_type)
                if not tool_func:
                    raise ValueError(f"未知的风险工具类型: {task.task_type}")

                await tool_func(task.payload)

                # 4. 执行成功,更新状态
                task.status = TaskStatus.SUCCESS
                task.error_message = None
                logger.debug(f"[TaskQueue] 任务 {task_id} 执行成功")

            except Exception as ex:
                # 5. 执行失败,处理重试或死信
                task.retry_count += 1
                task.error_message = str(ex)

                if task.retry_count >= MAX_RETRIES:
                    task.status = TaskStatus.DEAD_LETTER
                    logger.error(f"[TaskQueue] 任务 {task_id} 达到最大重试次数,进入死信队列!")
                else:
                    task.status = TaskStatus.FAILED
                    # 重新入队
                    await self.redis.rpush(REDIS_QUEUE_KEY, json.dumps({"task_id": task.id}))
                    logger.warning(f"[TaskQueue] 任务 {task_id} 失败 (重试 {task.retry_count}/{MAX_RETRIES})")

            await session.commit()

    async def start_worker(self):
        """
        启动后台 Worker,持续监听 Redis 队列.
        """
        logger.debug("[Worker] 异步任务 Worker 已启动")
        while True:
            # 阻塞等待,超时设为 1 秒
            message = await self.redis.blpop(REDIS_QUEUE_KEY, timeout=1)
            if message:
                _, data = message
                task_data = json.loads(data)
                # 异步处理任务,不阻塞队列监听
                asyncio.create_task(self.process_task(task_data["task_id"]))
            else:
                await asyncio.sleep(0.1)  # 短暂休眠,避免 CPU 空转


global_redis_client = Redis.from_url(settings.redis_url)
task_queue = TaskQueue(global_redis_client)
