"""
配置管理
类比JS：类似于 config.js 或 .env 配置
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 机器人配置
    BOT_NAME: str = "小智"
    BOT_COMPANY: str = "XXX科技"

    # 模型配置
    LLM_MODEL: str = "qwen2.5:7b"
    EMBEDDING_MODEL: str = "bge-m3"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # 路径配置
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    VECTOR_DB_DIR: Path = BASE_DIR / "vectorstore" / "chroma_db"
    CHAT_HISTORY_DIR: Path = BASE_DIR / "chat_history"

    # RAG配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    RETRIEVER_K: int = 5

    # 对话配置
    MAX_HISTORY_TURNS: int = 10  # 保留最近10轮对话

    class Config:
        env_file = ".env"


settings = Settings()