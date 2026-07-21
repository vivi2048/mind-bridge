#!/usr/bin/env python3
"""
下载本地 Embedding 模型(BAAI/bge-large-zh-v1.5)

用法:
    python scripts/download_embedding_model.py

下载完成后,修改 .env:
    EMBEDDING_BACKEND=local
    EMBEDDING_MODEL_ID=./data/embedding_models/models/BAAI/bge-large-zh-v1.5/snapshots/master
    EMBEDDING_CACHE_DIR=./data/embedding_models
"""

import sys
from pathlib import Path

def main():
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("请先安装 modelscope:")
        print("  pip install modelscope")
        sys.exit(1)
    
    model_id = "BAAI/bge-large-zh-v1.5"
    cache_dir = Path("./data/embedding_models")
    
    print(f"正在下载模型: {model_id}")
    print(f"缓存目录: {cache_dir}")
    print("(首次下载约 1.3GB,请耐心等待...)\n")
    
    try:
        snapshot_download(model_id, cache_dir=str(cache_dir))
        print("\n✓ 模型下载完成!")
        print(f"\n请修改 .env 文件:")
        print(f"  EMBEDDING_BACKEND=local")
        print(f"  EMBEDDING_MODEL_ID=./data/embedding_models/models/BAAI/bge-large-zh-v1.5/snapshots/master")
        print(f"  EMBEDDING_CACHE_DIR=./data/embedding_models")
    except Exception as e:
        print(f"\n✗ 下载失败: {e}")
        print("\n备选方案:使用 HuggingFace 镜像")
        print("  pip install huggingface_hub")
        print("  export HF_ENDPOINT=https://hf-mirror.com")
        print("  huggingface-cli download BAAI/bge-large-zh-v1.5 --local-dir ./data/embedding_models/bge-large-zh")
        sys.exit(1)

if __name__ == "__main__":
    main()
