"""
LLM 请求限流器
防止高并发下触发上游 API 的速率限制 (429 错误)
"""
import asyncio
import time
import logging
from functools import wraps
from typing import Callable, Any
from openai import RateLimitError

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    令牌桶限流器
    控制 LLM API 调用频率,避免触发 429 错误
    """
    
    def __init__(self, max_calls: int, period: float):
        """
        Args:
            max_calls: 时间窗口内最大调用次数
            period: 时间窗口(秒)
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = 0
        self.reset_time = time.time() + period
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取调用许可,如果超出限流则等待"""
        async with self._lock:
            now = time.time()
            
            # 重置计数器
            if now >= self.reset_time:
                self.calls = 0
                self.reset_time = now + self.period
            
            # 如果超出限制,等待到下一个时间窗口
            if self.calls >= self.max_calls:
                wait_time = self.reset_time - now
                if wait_time > 0:
                    logger.warning(f"[RateLimiter] 触发限流,等待 {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    # 重置
                    self.calls = 0
                    self.reset_time = time.time() + self.period
            
            self.calls += 1


# 全局 LLM 限流器: 80 次/分钟 (留出 47% 缓冲,API 限制 150/分钟)
# 每个用户请求平均 2-3 次 LLM 调用,80 次/分钟 ≈ 26-40 用户请求/分钟
# 留足缓冲防止突发流量触发 429
llm_rate_limiter = RateLimiter(max_calls=80, period=60.0)


def rate_limit_retry(max_retries: int = 3, base_delay: float = 2.0):
    """
    限流重试装饰器
    遇到 429 错误时自动重试,使用指数退避
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟时间(秒)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    # 先获取限流许可
                    await llm_rate_limiter.acquire()
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt < max_retries:
                        # 指数退避: 2s, 4s, 8s
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"[RateLimitRetry] 429 错误, {delay}s 后重试 (第 {attempt + 1}/{max_retries} 次)")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"[RateLimitRetry] 重试 {max_retries} 次后仍失败: {e}")
                        raise
                except Exception as e:
                    # 非限流错误直接抛出
                    raise
        return wrapper
    return decorator
