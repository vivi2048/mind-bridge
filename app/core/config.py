import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# 计算项目根目录（假设 config.py 在 app/core/ 下，往上推两级即为根目录）
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # 项目基础配置
    project_name: str = "MindBridge 心理测评与智能问答系统"
    debug: bool = False

    # --- 通用 API 配置 ---
    api_key: str = ""
    base_url: str = ""

    # --- 模型配置 ---
    llm_model_id: str = ""
    embedding_model_id: str = ""
    embedding_timeout_seconds: int = 30

    # --- 数据库与缓存 ---
    database_url: str = ""
    redis_url: str = ""

    # --- 其他配置 ---
    alert_email_delivery_mode: str = "log"
    excel_path: str = "./data/excel_ledger/risk_ledger.xlsx"
    worker_poll_interval: int = 5
    max_task_attempts: int = 3

    # --- 向量数据库 ---
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "mindbridge_knowledge"

    model_config = SettingsConfigDict(
        # 使用绝对路径指向项目根目录下的 .env 文件
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()