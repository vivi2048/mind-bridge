"""
统一日志配置模块.
主应用和测试脚本都从这里获取日志配置.
"""
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 北京时间 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))


class BeijingTimeFormatter(logging.Formatter):
    """自定义日志格式器，使用北京时间"""
    
    def formatTime(self, record, datefmt=None):
        """使用北京时间格式化时间戳"""
        # 将 UTC 时间戳转换为北京时间
        dt = datetime.fromtimestamp(record.created, BEIJING_TZ)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]  # 毫秒精度


_initialized = False


def setup_logging(console_output=True):
    """
    初始化日志:写入 logs/app.log,可选是否输出到控制台.
    
    Args:
        console_output: 是否输出到控制台,默认为 True.
                       测试脚本应设置为 False,避免干扰进度条显示.
    多次调用安全,只会初始化一次.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    # 创建自定义格式器
    formatter = BeijingTimeFormatter(FORMAT)
    
    handlers = [logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")]
    
    if console_output:
        handlers.append(logging.StreamHandler())
    
    # 为所有 handler 设置自定义格式器
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
    )
