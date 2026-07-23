"""
统一日志配置模块.
主应用和测试脚本都从这里获取日志配置.
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timezone, timedelta
import queue

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))


class BeijingTimeFormatter(logging.Formatter):
    """自定义日志格式器，使用北京时间"""
    
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """使用北京时间格式化时间戳"""
        # 将 UTC 时间戳转换为北京时间
        dt = datetime.fromtimestamp(record.created, BEIJING_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]  # 毫秒精度


_initialized = False
_queue_listener = None


def setup_logging(console_output: bool = True) -> None:
    """
    初始化日志:写入 logs/app.log,可选是否输出到控制台.
    使用异步队列处理日志,避免 I/O 阻塞主线程.
    
    Args:
        console_output: 是否输出到控制台,默认为 True.
                       测试脚本应设置为 False,避免干扰进度条显示.
    多次调用安全,只会初始化一次.
    """
    global _initialized, _queue_listener
    if _initialized:
        return
    _initialized = True

    # 创建自定义格式器
    formatter = BeijingTimeFormatter(FORMAT)
    
    # 创建实际的文件和控制台 handlers
    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    
    handlers = [file_handler]
    
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # 使用 QueueHandler + QueueListener 实现异步日志
    # 日志记录先放入队列,后台线程负责写入文件,避免阻塞主线程
    log_queue = queue.Queue(-1)  # 无限队列
    queue_handler = logging.handlers.QueueHandler(log_queue)
    
    # 启动后台线程处理日志队列
    _queue_listener = logging.handlers.QueueListener(
        log_queue, *handlers, respect_handler_level=True
    )
    _queue_listener.start()
    
    # 配置根 logger 使用队列 handler
    logging.basicConfig(
        level=logging.INFO,
        handlers=[queue_handler],
    )
