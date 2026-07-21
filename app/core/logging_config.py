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


def setup_logging():
    """
    初始化日志:同时写入 logs/app.log 和控制台.
    多次调用安全,只会初始化一次.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    logging.basicConfig(
        level=logging.INFO,
        format=FORMAT,
        handlers=[
            logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
