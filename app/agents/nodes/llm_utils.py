"""节点共享工具函数"""
from langchain_core.runnables import RunnableSerializable
from app.core.rate_limiter import rate_limit_retry

# LLM 调用失败时的兜底回复
FALLBACK_MESSAGE = "抱歉,我这边暂时遇到了一点技术问题,我们可以稍后再聊."


@rate_limit_retry()
async def invoke_with_retry(chain: RunnableSerializable, **kwargs):
    """
    通用 LLM 调用:带限流 + 429 重试.
    替代各节点中重复的 _call_*_llm 包装函数.
    """
    return await chain.ainvoke(kwargs)
