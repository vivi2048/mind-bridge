"""
统一日志配置模块.
主应用和测试脚本都从这里获取日志配置.
"""
import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

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

    handlers = [logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")]
    
    if console_output:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.INFO,
        format=FORMAT,
        handlers=handlers,
    )
