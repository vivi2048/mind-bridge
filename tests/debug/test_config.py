import pymysql
import redis
import httpx
from sqlalchemy.engine import make_url
from app.core.config import settings


def test_mysql():
    print("\n[1/4] MySQL 数据库连接...")
    try:
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
            print(f"  ✓ MySQL {version[0]}")
        else:
            print("  ⚠ 连接成功,但未获取到版本号")
    except Exception as ex:
        print(f"  ✗ 连接失败: {ex}")


def test_redis():
    print("\n[2/4] Redis 缓存连接...")
    try:
        if not settings.redis_url:
            print("  ✗ REDIS_URL 未设置")
            return
            
        r = redis.from_url(settings.redis_url, decode_responses=True)
        pong = r.ping()
        info = r.info("server")
        r.close()
        if pong:
            print(f"  ✓ Redis {info.get('redis_version')}")
        else:
            print("  ✗ PING 未返回 True")
    except Exception as ex:
        print(f"  ✗ 连接失败: {ex}")


def test_llm():
    print("\n[3/4] LLM API...")
    try:
        payload = {
            "model": settings.llm_model_id,
            "messages": [{"role": "user", "content": "Hello"}],
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
        print(f"  ✓ 模型响应: {content}")
    except Exception as ex:
        print(f"  ✗ 调用失败: {ex}")


def test_embedding():
    print("\n[4/4] Embedding 向量化模型...")
    test_text = "MindBridge 测试"
    
    if settings.embedding_backend.lower() == "local":
        try:
            from app.core.embeddings import create_embeddings
            embeddings = create_embeddings()
            vector = embeddings.embed_query(test_text)
            print(f"  ✓ 本地模型, 维度: {len(vector)}")
        except Exception as ex:
            print(f"  ✗ 加载失败: {ex}")
    else:
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
            print(f"  ✓ API 连通, 维度: {vector_dim}")
        except Exception as ex:
            print(f"  ✗ 调用失败: {ex}")


if __name__ == "__main__":
    print("MindBridge 系统连通性测试")
    test_mysql()
    test_redis()
    test_llm()
    test_embedding()
    print("\n测试完成")
