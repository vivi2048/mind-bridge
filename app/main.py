import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.agents.graph import MindBridgeGraph
from app.db.session import async_engine
from app.services.task_queue import task_queue, global_redis_client
from app.core.config import settings
from app.api import chat

# 用于在 lifespan 外部持有 worker 任务的引用，以便优雅关闭
worker_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    FastAPI 生命周期管理器。
    用于在应用启动时初始化资源，在关闭时清理资源。
    """
    global worker_task

    # 将异步 Worker 放入后台任务中运行，避免阻塞 FastAPI 启动

    app.state.graph = MindBridgeGraph()
    worker_task = asyncio.create_task(task_queue.start_worker())

    yield  # 应用运行中...

    # 优雅地停止 Worker：取消后台任务
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass  # 任务被正常取消，忽略该异常
    await global_redis_client.close()
    await async_engine.dispose()


# 初始化 FastAPI 应用
app = FastAPI(
    title=settings.project_name,
    description="基于 RAG 和异步任务队列的心理健康评估平台",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """
    健康检查接口。
    用于负载均衡器或监控系统探活。
    """
    return {"status": "ok", "message": "MindBridge is running!"}


app.include_router(chat.router, prefix="/api")
