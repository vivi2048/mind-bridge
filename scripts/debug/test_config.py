import pymysql
import redis
import httpx
from sqlalchemy.engine import make_url
from app.core.config import settings


def test_mysql():
    print("\n[1/4] 正在测试 MySQL 数据库连接...")
    try:
        # 使用 SQLAlchemy 的 URL 解析器
        url = make_url(settings.database_url)
        
        conn = pymysql.connect(
            host=url.host,
            port=url.port or 3306,
            user=url.username,
            password=url.password,
            database=url.database
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()
        conn.close()
        if version:
            print(f"MySQL 连接成功，数据库版本: {version[0]}")
        else:
            print("MySQL 连接成功，但未能获取到版本号")
    except Exception as e:
        print(f"MySQL 连接失败: {e}")


def test_redis():
    print("\n[2/4] 正在测试 Redis 缓存连接...")
    try:
        if not settings.redis_url:
            print("Redis 连接失败: REDIS_URL 环境变量未设置")
            return
            
        r = redis.from_url(settings.redis_url, decode_responses=True)
        pong = r.ping()
        info = r.info("server")
        r.close()
        if pong:
            print(f"Redis 连接成功，Redis 版本: {info.get('redis_version')}")
        else:
            print("Redis 连接失败: PING 未返回 True")
    except Exception as e:
        print(f"Redis 连接失败: {e}")


def test_llm():
    print("\n[3/4] 正在测试大语言模型 (LLM) API...")
    try:
        payload = {
            # 注意：这里改成了 settings.llm_model_id
            "model": settings.llm_model_id,
            "messages": [{"role": "user", "content": "Hello, are you Qwen?"}],
            "max_tokens": 10
        }
        # 注意：这里改成了通用的 settings.api_key 和 settings.base_url
        headers = {"Authorization": f"Bearer {settings.api_key}"}

        response = httpx.post(
            f"{settings.base_url}/chat/completions",
            headers=headers, json=payload, timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        print(f"LLM API 连通成功，模型响应: {content}")
    except Exception as e:
        print(f"LLM API 调用失败: {e}")


def test_embedding():
    print("\n[4/4] 正在测试向量化模型 (Embedding) API...")
    try:
        payload = {
            # 注意：这里改成了 settings.embedding_model_id
            "model": settings.embedding_model_id,
            "input": "MindBridge 心理测评系统连通性测试"
        }
        # 注意：这里改成了通用的 settings.api_key 和 settings.base_url
        headers = {"Authorization": f"Bearer {settings.api_key}"}

        response = httpx.post(
            f"{settings.base_url}/embeddings",
            headers=headers, json=payload, timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        vector_dim = len(data["data"][0]["embedding"])
        print(f"Embedding API 连通成功，向量维度: {vector_dim}")
    except Exception as e:
        print(f"Embedding API 调用失败: {e}")


if __name__ == "__main__":
    print("开始执行 MindBridge 系统基础配置连通性测试...")
    test_mysql()
    test_redis()
    test_llm()
    test_embedding()
    print("\n连通性测试执行完毕！")