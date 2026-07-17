import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CHROMA_PERSIST_DIR = Path(settings.chroma_persist_dir)


def check_chroma_exists() -> bool:
    """检查 ChromaDB 是否已存在且有数据"""
    if not CHROMA_PERSIST_DIR.exists():
        return False
    # 检查是否有实际的数据库文件
    chroma_files = list(CHROMA_PERSIST_DIR.glob("**/*"))
    return len(chroma_files) > 0


def load_markdown_files(directory: Path) -> list[Document]:
    """简单加载目录下所有 Markdown 文件"""
    documents = []
    for md_file in directory.glob("**/*.md"):
        content = md_file.read_text(encoding="utf-8")
        documents.append(Document(
            page_content=content,
            metadata={"source": str(md_file.relative_to(directory))}
        ))
    return documents


def ingest_documents(force: bool = False):
    """
    导入知识文档到向量数据库
    
    Args:
        force: 是否强制重建（即使已存在）
    """
    # 检查是否已存在
    if not force and check_chroma_exists():
        print(f"知识库已存在: {CHROMA_PERSIST_DIR}")
        print("如需重建，请运行: python -m scripts.ingest_knowledge --force")
        return
    
    if force:
        print("强制重建知识库...")
    
    if not KNOWLEDGE_DIR.exists():
        print(f"知识库目录不存在: {KNOWLEDGE_DIR}")
        print("请确保项目根目录下已创建 'knowledge' 文件夹并放入了 .md 文件。")
        return

    # 1. 加载 knowledge 目录下的所有 .md 文件
    documents = load_markdown_files(KNOWLEDGE_DIR)
    print(f"成功加载 {len(documents)} 个知识文档")

    # 2. 文本切分
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)
    print(f"文本切分完成，共生成 {len(chunks)} 个知识块")

    # 3. 初始化通义 Embedding 模型
    embeddings = DashScopeEmbeddings(
        model=settings.embedding_model_id,
        dashscope_api_key=settings.api_key
    )

    # 4. 批量入库到 Chroma 向量数据库
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR)
    )
    print(f"知识库构建完成！数据已持久化到 {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    # 支持 --force 参数强制重建
    force_rebuild = "--force" in sys.argv
    ingest_documents(force=force_rebuild)
