import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_chroma import Chroma
from app.core.embeddings import create_embeddings
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
        force: 是否强制重建(即使已存在)
    """
    # 检查是否已存在
    if not force and check_chroma_exists():
        print(f"知识库已存在: {CHROMA_PERSIST_DIR}")
        print("如需重建,请运行: python -m scripts.ingest_knowledge --force")
        return
    
    if force:
        print("强制重建知识库,清除旧数据...")
        # 通过 Chroma API 删除 collection,避免直接删目录导致的文件锁问题
        try:
            from langchain_chroma import Chroma
            from app.core.embeddings import create_embeddings
            embeddings = create_embeddings()
            old_db = Chroma(
                persist_directory=str(CHROMA_PERSIST_DIR),
                embedding_function=embeddings,
                collection_name=settings.chroma_collection_name,
            )
            old_db.delete_collection()
            print(f"  已清除旧 collection: {settings.chroma_collection_name}")
        except Exception as e:
            print(f"  清除旧数据时出错: {e}")
    
    if not KNOWLEDGE_DIR.exists():
        print(f"知识库目录不存在: {KNOWLEDGE_DIR}")
        print("请确保项目根目录下已创建 'knowledge' 文件夹并放入了 .md 文件.")
        return

    # 1. 加载 knowledge 目录下的所有 .md 文件
    documents = load_markdown_files(KNOWLEDGE_DIR)
    print(f"成功加载 {len(documents)} 个知识文档")

    # 2. 按 Markdown 标题切分(每个标题下是一个完整话题)
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "H1"),
            ("##", "H2"),
            ("###", "H3"),
        ]
    )
    
    # 对每个文档按标题切分
    chunks = []
    for doc in documents:
        md_chunks = md_splitter.split_text(doc.page_content)
        for chunk in md_chunks:
            # 保留原始文件来源信息
            chunk.metadata["source"] = doc.metadata.get("source", "unknown")
            # 用标题路径作为前缀,让检索时上下文更清晰
            header_path = " > ".join(
                chunk.metadata.get(k, "") for k in ["H1", "H2", "H3"] if chunk.metadata.get(k)
            )
            if header_path:
                chunk.page_content = f"[{header_path}]\n{chunk.page_content}"
            chunks.append(chunk)
    
    # 3. 合并过小的块 + 拆分过长的块
    # 先合并小碎块(<100 字符)
    min_length = 100
    merged_chunks = []
    for chunk in chunks:
        if merged_chunks and len(chunk.page_content.strip()) < min_length:
            merged_chunks[-1].page_content += "\n" + chunk.page_content
        else:
            merged_chunks.append(chunk)
    
    # 再拆分过长块(>1000 字符,防止超出 embedding 上下文)
    final_chunks = []
    char_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    for chunk in merged_chunks:
        if len(chunk.page_content) > 1000:
            sub_chunks = char_splitter.split_text(chunk.page_content)
            for sub in sub_chunks:
                final_chunks.append(Document(page_content=sub, metadata=chunk.metadata.copy()))
        else:
            final_chunks.append(chunk)
    
    merged_count = len(chunks) - len(merged_chunks)
    split_count = sum(1 for c in merged_chunks if len(c.page_content) > 1000)
    if merged_count > 0:
        print(f"  合并了 {merged_count} 个碎块(<{min_length}字符)")
    if split_count > 0:
        print(f"  拆分了 {split_count} 个长块(>1000字符)")
    
    print(f"文本切分完成,共生成 {len(final_chunks)} 个知识块")

    # 3. 初始化 Embedding 模型(通过工厂函数,自动根据配置选择本地或 API)
    embeddings = create_embeddings()

    # 4. 批量入库到 Chroma 向量数据库
    Chroma.from_documents(
        documents=final_chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
        collection_name=settings.chroma_collection_name,
    )
    print(f"知识库构建完成!数据已持久化到 {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    # 支持 --force 参数强制重建
    force_rebuild = "--force" in sys.argv
    ingest_documents(force=force_rebuild)
