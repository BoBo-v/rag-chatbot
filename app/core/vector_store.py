"""
向量数据库管理
负责：文档加载、分块、向量化、检索
"""
from pathlib import Path
from typing import Optional

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import settings


class VectorStoreManager:
    """向量库管理器"""

    def __init__(self):
        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        self.vectordb: Optional[Chroma] = None
        self.chunks_count = 0

    def load_documents(self, data_dir: Path) -> list[Document]:
        """从目录加载文档"""
        documents = []

        for file_path in data_dir.glob("*"):
            if file_path.suffix in [".txt", ".md"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": file_path.name,
                            "file_type": file_path.suffix
                        }
                    )
                    documents.append(doc)
                    print(f"  ✓ 加载: {file_path.name}")
                except Exception as e:
                    print(f"  ✗ 加载失败 {file_path.name}: {e}")

        return documents

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """文档分块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        return chunks

    def create_vectorstore(self, chunks: list[Document], persist: bool = True):
        """创建向量数据库"""
        persist_dir = str(settings.VECTOR_DB_DIR) if persist else None

        self.vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=persist_dir,
            collection_name="knowledge_base"
        )
        self.chunks_count = len(chunks)
        print(f"✅ 向量库创建完成，共 {self.chunks_count} 个文档块")

    def load_vectorstore(self):
        """加载已有的向量数据库"""
        persist_dir = str(settings.VECTOR_DB_DIR)

        if not Path(persist_dir).exists():
            raise FileNotFoundError(f"向量库不存在: {persist_dir}")

        self.vectordb = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings,
            collection_name="knowledge_base"
        )
        # 获取文档数量
        self.chunks_count = self.vectordb._collection.count()
        print(f"✅ 向量库加载完成，共 {self.chunks_count} 个文档块")

    def get_retriever(self):
        """获取检索器"""
        if not self.vectordb:
            raise RuntimeError("向量库未初始化")

        return self.vectordb.as_retriever(
            search_type="mmr",  # 最大边际相关性，平衡相关性和多样性
            search_kwargs={
                "k": settings.RETRIEVER_K,
                "fetch_k": 20,
                "lambda_mult": 0.7
            }
        )

    def search(self, query: str, k: int = 5) -> list[Document]:
        """直接搜索"""
        if not self.vectordb:
            raise RuntimeError("向量库未初始化")
        return self.vectordb.similarity_search(query, k=k)


# 全局单例
vector_manager = VectorStoreManager()