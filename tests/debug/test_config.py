import logging
import pymysql
import redis
import httpx
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def test_mysql():
    logger.info("\n[1/4] 正在测试 MySQL 数据库连接...")
    try:
        # 使用 SQLAlchemy 的 URL 解析器
        url = make_url(settings.database_url)
        
        conn = pymysql.connect(
            host=str(url.host) if url.host else "localhost",
            port=int(url.port) if url.port else 3306,
            user=str(url.username) if url.username else "root",
            password=str(url.password) if url.password else "",
            database=str(url.database) if url.database else "test"
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()
        conn.close()
        if version:
            logger.info(f"MySQL 连接成功,数据库版本: {version[0]}")
        else:
            logger.warning("MySQL 连接成功,但未能获取到版本号")
    except Exception as ex:
        logger.error(f"MySQL 连接失败: {ex}")


def test_redis():
    logger.info("\n[2/4] 正在测试 Redis 缓存连接...")
    try:
        if not settings.redis_url:
            logger.error("Redis 连接失败: REDIS_URL 环境变量未设置")
            return
            
        r = redis.from_url(settings.redis_url, decode_responses=True)
        pong = r.ping()
        info = r.info("server")
        r.close()
        if pong:
            logger.info(f"Redis 连接成功,Redis 版本: {info.get('redis_version')}")
        else:
            logger.error("Redis 连接失败: PING 未返回 True")
    except Exception as ex:
        logger.error(f"Redis 连接失败: {ex}")


def test_llm():
    logger.info("\n[3/4] 正在测试大语言模型 (LLM) API...")
    try:
        payload = {
            "model": settings.llm_model_id,
            "messages": [{"role": "user", "content": "Hello, are you Qwen?"}],
            "max_tokens": 10
        }
        headers = {"Authorization": f"Bearer {settings.api_key}"}

        response = httpx.post(
            f"{settings.base_url}/chat/completions",
            headers=headers, json=payload, timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        logger.info(f"LLM API 连通成功,模型响应: {content}")
    except Exception as ex:
        logger.error(f"LLM API 调用失败: {ex}")


def test_embedding():
    logger.info("\n[4/4] 正在测试向量化模型 (Embedding)...")
    test_text = "MindBridge 心理测评系统连通性测试"
    
    if settings.embedding_backend.lower() == "local":
        # 本地模式:直接加载模型测试
        try:
            from app.core.embeddings import create_embeddings
            embeddings = create_embeddings()
            vector = embeddings.embed_query(test_text)
            logger.info(f"本地 Embedding 加载成功,向量维度: {len(vector)}, 模型: {settings.embedding_model_id}")
        except Exception as ex:
            logger.error(f"本地 Embedding 加载失败: {ex}")
    else:
        # API 模式:调用远程接口
        try:
            payload = {
                "model": settings.embedding_model_id,
                "input": test_text
            }
            headers = {"Authorization": f"Bearer {settings.embedding_api_key}"}
            response = httpx.post(
                f"{settings.embedding_base_url}/embeddings",
                headers=headers, json=payload, timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            vector_dim = len(data["data"][0]["embedding"])
            logger.info(f"Embedding API 连通成功,向量维度: {vector_dim}")
        except Exception as ex:
            logger.error(f"Embedding API 调用失败: {ex}")


if __name__ == "__main__":
    logger.info("开始执行 MindBridge 系统基础配置连通性测试...")
    test_mysql()
    test_redis()
    test_llm()
    test_embedding()
    logger.info("\n连通性测试执行完毕!")