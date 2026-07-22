"""
Embedding 工厂模块:根据配置创建不同的向量模型后端.

支持两种模式:
- local: 本地加载 HuggingFace 模型(默认,零成本)
- api:   通过 OpenAI 兼容 API 调用远程服务(DashScope / OpenAI 等)

使用方式:
    from app.core.embeddings import create_embeddings
    embeddings = create_embeddings()
"""
import os
import logging
from langchain_core.embeddings import Embeddings
from app.core.config import settings

logger = logging.getLogger(__name__)


def create_embeddings() -> Embeddings:
    """
    根据 settings.embedding_backend 创建对应的 Embeddings 实例.

    Returns:
        langchain_core.embeddings.Embeddings 实例
    """
    backend = settings.embedding_backend.lower()

    if backend == "local":
        return _create_local_embeddings()
    elif backend == "api":
        return _create_api_embeddings()
    else:
        raise ValueError(
            f"不支持的 EMBEDDING_BACKEND: {backend!r},"
            f"可选值: local, api"
        )


def _create_local_embeddings() -> Embeddings:
    """本地加载 HuggingFace / SentenceTransformer 模型"""
    from langchain_community.embeddings import HuggingFaceEmbeddings

    # 设置模型缓存目录
    if settings.embedding_cache_dir:
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = settings.embedding_cache_dir

    model_path = settings.embedding_model_id
    logger.debug(f"[Embeddings] 加载本地模型: {model_path}")

    return HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _create_api_embeddings() -> Embeddings:
    """通过 OpenAI 兼容 API 调用远程 Embedding 服务"""
    from langchain_openai import OpenAIEmbeddings

    logger.debug(
        f"[Embeddings] 使用 API 模式: "
        f"model={settings.embedding_model_id}, "
        f"base_url={settings.embedding_base_url}"
    )

    return OpenAIEmbeddings(
        model=settings.embedding_model_id,
        openai_api_key=settings.embedding_api_key,
        openai_api_base=settings.embedding_base_url,
    )
