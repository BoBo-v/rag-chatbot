# RAG 本地知识库项目 - 完整构建指南

> 适合：Python零基础 + 有前端经验的开发者

---

## 📁 项目目录结构（生产级）

```
rag-chatbot/
├── .env                    # 环境变量配置
├── .gitignore
├── requirements.txt        # Python依赖
├── README.md
│
├── data/                   # 知识库原始文档
│   ├── product_intro.txt
│   ├── faq.md
│   └── ...
│
├── vectorstore/            # 向量数据库持久化存储
│   └── chroma_db/
│
├── chat_history/           # 聊天记录存储
│   └── sessions/
│
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 配置管理
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py       # API路由
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── rag_engine.py   # RAG核心逻辑
│   │   ├── chat_memory.py  # 对话记忆管理
│   │   └── vector_store.py # 向量库管理
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # 数据模型
│   │
│   └── utils/
│       ├── __init__.py
│       └── text_loader.py  # 文档加载工具
│
└── scripts/
    ├── init_vectorstore.py # 初始化向量库脚本
    └── test_api.py         # 测试脚本
```

---

## 🔧 第一步：环境搭建

### 1.1 安装 Python（推荐3.10+）

```bash
# macOS
brew install python@3.11

# Windows
# 官网下载：https://www.python.org/downloads/
# 安装时勾选 "Add Python to PATH"

# 验证
python --version   # 或 python3 --version
```

### 1.2 创建项目和虚拟环境

```bash
# 创建项目目录
mkdir rag-chatbot
cd rag-chatbot

# 创建虚拟环境（隔离依赖，类似npm的node_modules）
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 激活后命令行会显示 (venv) 前缀
```

### 1.3 安装依赖

创建 `requirements.txt`：
```txt
# Web框架
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9

# LangChain 生态
langchain==0.3.0
langchain-community==0.3.0
langchain-ollama==0.2.0
langchain-text-splitters==0.3.0
langchain-chroma==0.1.4

# 向量数据库
chromadb==0.5.5

# 中文分词
jieba==0.42.1

# 工具
python-dotenv==1.0.1
pydantic==2.9.0
pydantic-settings==2.5.0

# 数据存储
aiosqlite==0.20.0  # 异步SQLite，存聊天记录
```

安装：
```bash
pip install -r requirements.txt
```

### 1.4 安装 Ollama（本地大模型）

```bash
# macOS
brew install ollama

# 或去官网下载：https://ollama.ai

# 启动 Ollama 服务
ollama serve

# 另开终端，下载模型
ollama pull qwen2.5:7b      # 中文对话模型，约4.5GB
ollama pull bge-m3          # 中文向量模型，约2GB

# 验证
ollama list
```

---

## 📝 第二步：创建项目文件

### 2.1 配置文件 `app/config.py`

```python
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
```

### 2.2 数据模型 `app/models/schemas.py`

```python
"""
Pydantic 数据模型
类比JS：类似于 TypeScript 的 interface/type
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ========== 请求模型 ==========
class ChatRequest(BaseModel):
    """聊天请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID，用于连续对话")


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    user_id: Optional[str] = None
    metadata: Optional[dict] = None


# ========== 响应模型 ==========
class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str
    session_id: str
    sources: list[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    created_at: datetime
    message_count: int
    last_message_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    llm_model: str
    embedding_model: str
    chunks_count: int
    sessions_count: int
```

### 2.3 对话记忆管理 `app/core/chat_memory.py`

```python
"""
对话记忆管理 - 实现连续对话和聊天存储
这是你需要的核心功能！
"""
import json
import uuid
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "human" or "ai"
    content: str
    timestamp: str
    

class ChatMemoryManager:
    """
    聊天记忆管理器
    - 管理多个会话
    - 持久化存储聊天记录
    - 支持上下文窗口控制
    """
    
    def __init__(self, db_path: str, max_history: int = 10):
        self.db_path = db_path
        self.max_history = max_history
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            # 会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    metadata TEXT
                )
            """)
            # 消息表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            # 索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages(session_id)
            """)
            await db.commit()
    
    async def create_session(
        self, 
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO sessions 
                   (session_id, user_id, created_at, updated_at, metadata) 
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, user_id, now, now, json.dumps(metadata or {}))
            )
            await db.commit()
        
        return session_id
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ):
        """添加消息到会话"""
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # 添加消息
            await db.execute(
                """INSERT INTO messages (session_id, role, content, timestamp) 
                   VALUES (?, ?, ?, ?)""",
                (session_id, role, content, now)
            )
            # 更新会话时间
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id)
            )
            await db.commit()
    
    async def get_history(
        self, 
        session_id: str,
        limit: Optional[int] = None
    ) -> list[ChatMessage]:
        """获取会话历史"""
        limit = limit or self.max_history
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT role, content, timestamp FROM messages 
                   WHERE session_id = ? 
                   ORDER BY id DESC LIMIT ?""",
                (session_id, limit * 2)  # 每轮2条消息
            )
            rows = await cursor.fetchall()
        
        # 反转顺序（从旧到新）
        messages = [
            ChatMessage(role=row["role"], content=row["content"], timestamp=row["timestamp"])
            for row in reversed(rows)
        ]
        return messages
    
    async def get_langchain_history(self, session_id: str) -> list[BaseMessage]:
        """获取LangChain格式的历史消息（用于传给LLM）"""
        messages = await self.get_history(session_id)
        
        lc_messages = []
        for msg in messages:
            if msg.role == "human":
                lc_messages.append(HumanMessage(content=msg.content))
            else:
                lc_messages.append(AIMessage(content=msg.content))
        
        return lc_messages
    
    async def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            return await cursor.fetchone() is not None
    
    async def get_session_count(self) -> int:
        """获取会话总数"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM sessions")
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def get_all_sessions(self) -> list[dict]:
        """获取所有会话列表"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT s.session_id, s.created_at, s.updated_at,
                          COUNT(m.id) as message_count
                   FROM sessions s
                   LEFT JOIN messages m ON s.session_id = m.session_id
                   GROUP BY s.session_id
                   ORDER BY s.updated_at DESC"""
            )
            rows = await cursor.fetchall()
        
        return [dict(row) for row in rows]


# ========== 上下文格式化工具 ==========
def format_history_for_prompt(messages: list[ChatMessage], max_chars: int = 2000) -> str:
    """
    将历史消息格式化为prompt字符串
    控制长度避免超出上下文窗口
    """
    if not messages:
        return ""
    
    lines = []
    total_chars = 0
    
    # 从最近的消息开始，倒序添加
    for msg in reversed(messages):
        role_name = "用户" if msg.role == "human" else "助手"
        line = f"{role_name}: {msg.content}"
        
        if total_chars + len(line) > max_chars:
            break
        
        lines.insert(0, line)
        total_chars += len(line)
    
    return "\n".join(lines)
```

### 2.4 向量库管理 `app/core/vector_store.py`

```python
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
```

### 2.5 RAG引擎 `app/core/rag_engine.py`

```python
"""
RAG 核心引擎
整合：向量检索 + 对话历史 + LLM生成
"""
from typing import AsyncGenerator, Optional

from langchain_ollama import OllamaLLM

from app.config import settings
from app.core.vector_store import vector_manager
from app.core.chat_memory import ChatMemoryManager, format_history_for_prompt


class RAGEngine:
    """RAG 问答引擎"""
    
    def __init__(self, memory_manager: ChatMemoryManager):
        self.memory = memory_manager
        self.llm = OllamaLLM(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.7,
            num_predict=1024
        )
        self.retriever = vector_manager.get_retriever()
    
    def _build_prompt(
        self, 
        question: str, 
        context: str, 
        history: str = ""
    ) -> str:
        """构建完整的 Prompt"""
        
        history_section = ""
        if history:
            history_section = f"""
历史对话（用于理解上下文）:
{history}
"""
        
        prompt = f"""你是"{settings.BOT_NAME}"，一个专业友好的AI助手，由{settings.BOT_COMPANY}开发。

身份规则：
- 你的名字是：{settings.BOT_NAME}
- 你的开发者是：{settings.BOT_COMPANY}
- 当被问到身份相关问题时，使用上述信息回答

回答规则：
1. 根据【知识库内容】回答问题
2. 如果知识库没有相关信息，诚实说"我不太清楚这个问题"
3. 保持友好、专业的语气
4. 回答要简洁明了
{history_section}
【知识库内容】:
{context}

【用户问题】: {question}

【回答】:"""
        
        return prompt
    
    async def ask(
        self, 
        question: str, 
        session_id: str
    ) -> tuple[str, list[str]]:
        """
        处理问题（非流式）
        返回：(答案, 来源列表)
        """
        # 1. 获取历史对话
        history_messages = await self.memory.get_history(session_id)
        history_text = format_history_for_prompt(history_messages)
        
        # 2. 检索相关文档
        docs = self.retriever.invoke(question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        # 3. 构建 prompt
        prompt = self._build_prompt(question, context, history_text)
        
        # 4. 调用 LLM
        answer = self.llm.invoke(prompt)
        
        # 5. 保存对话
        await self.memory.add_message(session_id, "human", question)
        await self.memory.add_message(session_id, "ai", answer)
        
        # 6. 提取来源
        sources = [
            f"[{doc.metadata.get('source', '未知')}] {doc.page_content[:80]}..."
            for doc in docs[:3]
        ]
        
        return answer, sources
    
    async def ask_stream(
        self, 
        question: str, 
        session_id: str
    ) -> AsyncGenerator[str, None]:
        """
        流式问答
        """
        # 1. 获取历史对话
        history_messages = await self.memory.get_history(session_id)
        history_text = format_history_for_prompt(history_messages)
        
        # 2. 检索相关文档
        docs = self.retriever.invoke(question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        # 3. 构建 prompt
        prompt = self._build_prompt(question, context, history_text)
        
        # 4. 流式生成
        full_answer = ""
        for chunk in self.llm.stream(prompt):
            full_answer += chunk
            yield chunk
        
        # 5. 保存完整对话
        await self.memory.add_message(session_id, "human", question)
        await self.memory.add_message(session_id, "ai", full_answer)
```

### 2.6 API 路由 `app/api/routes.py`

```python
"""
API 路由定义
"""
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest, ChatResponse, 
    CreateSessionRequest, SessionInfo, HealthResponse
)
from app.core.rag_engine import RAGEngine
from app.core.chat_memory import ChatMemoryManager
from app.core.vector_store import vector_manager
from app.config import settings


router = APIRouter()

# 初始化组件（会在main.py中调用）
memory_manager: ChatMemoryManager = None
rag_engine: RAGEngine = None


async def init_components():
    """初始化所有组件"""
    global memory_manager, rag_engine
    
    # 初始化记忆管理器
    db_path = str(settings.CHAT_HISTORY_DIR / "chat.db")
    memory_manager = ChatMemoryManager(db_path, max_history=settings.MAX_HISTORY_TURNS)
    await memory_manager.init_db()
    
    # 加载向量库
    try:
        vector_manager.load_vectorstore()
    except FileNotFoundError:
        print("⚠️ 向量库不存在，正在创建...")
        docs = vector_manager.load_documents(settings.DATA_DIR)
        if docs:
            chunks = vector_manager.split_documents(docs)
            vector_manager.create_vectorstore(chunks)
        else:
            print("⚠️ 没有找到知识库文档")
    
    # 初始化 RAG 引擎
    rag_engine = RAGEngine(memory_manager)
    
    print("✅ 所有组件初始化完成")


# ========== 会话管理 ==========

@router.post("/sessions", response_model=SessionInfo)
async def create_session(request: CreateSessionRequest = None):
    """创建新会话"""
    request = request or CreateSessionRequest()
    session_id = await memory_manager.create_session(
        user_id=request.user_id,
        metadata=request.metadata
    )
    return SessionInfo(
        session_id=session_id,
        created_at=__import__('datetime').datetime.now(),
        message_count=0
    )


@router.get("/sessions")
async def list_sessions():
    """获取所有会话"""
    sessions = await memory_manager.get_all_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史"""
    if not await memory_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    
    messages = await memory_manager.get_history(session_id, limit=50)
    return {
        "session_id": session_id,
        "messages": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in messages
        ]
    }


# ========== 聊天接口 ==========

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口（非流式）
    
    - 如果不传 session_id，会自动创建新会话
    - 传入 session_id 则继续之前的对话
    """
    # 处理会话
    session_id = request.session_id
    if not session_id:
        session_id = await memory_manager.create_session()
    elif not await memory_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    
    try:
        answer, sources = await rag_engine.ask(request.question, session_id)
        return ChatResponse(
            answer=answer,
            session_id=session_id,
            sources=sources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口
    返回 SSE (Server-Sent Events)
    """
    # 处理会话
    session_id = request.session_id
    if not session_id:
        session_id = await memory_manager.create_session()
    elif not await memory_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    
    async def generate():
        # 先发送 session_id
        yield f"data: {{'type': 'session', 'session_id': '{session_id}'}}\n\n"
        
        try:
            async for chunk in rag_engine.ask_stream(request.question, session_id):
                # 转义特殊字符
                escaped = chunk.replace('\n', '\\n').replace('"', '\\"')
                yield f"data: {{'type': 'content', 'text': \"{escaped}\"}}\n\n"
                await asyncio.sleep(0.01)
            
            yield "data: {\"type\": \"done\"}\n\n"
        except Exception as e:
            yield f"data: {{'type': 'error', 'message': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ========== 系统接口 ==========

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    session_count = await memory_manager.get_session_count()
    return HealthResponse(
        status="healthy",
        llm_model=settings.LLM_MODEL,
        embedding_model=settings.EMBEDDING_MODEL,
        chunks_count=vector_manager.chunks_count,
        sessions_count=session_count
    )
```

### 2.7 主入口 `app/main.py`

```python
"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, init_components
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 正在启动 RAG 系统...")
    await init_components()
    print(f"✅ {settings.BOT_NAME} 准备就绪!")
    
    yield
    
    # 关闭时
    print("👋 系统关闭")


# 创建应用
app = FastAPI(
    title=f"{settings.BOT_NAME} API",
    description="本地知识库智能问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router, prefix="/api")


# 根路径
@app.get("/")
def root():
    return {
        "name": settings.BOT_NAME,
        "company": settings.BOT_COMPANY,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 开发模式，代码修改自动重启
    )
```

---

## 🚀 第三步：运行项目

### 3.1 准备知识库文档

在 `data/` 目录下放入你的知识文档：

```bash
mkdir -p data
echo "这是产品介绍文档..." > data/product.txt
echo "Q: 你们的服务时间？\nA: 周一到周五 9:00-18:00" > data/faq.md
```

### 3.2 创建必要目录

```bash
mkdir -p vectorstore chat_history app/api app/core app/models app/utils scripts

# 创建 __init__.py 文件（Python包标识）
touch app/__init__.py
touch app/api/__init__.py
touch app/core/__init__.py
touch app/models/__init__.py
touch app/utils/__init__.py
```

### 3.3 启动服务

```bash
# 确保 Ollama 在运行
ollama serve

# 启动 API 服务
python -m app.main

# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.4 测试接口

```bash
# 健康检查
curl http://localhost:8000/api/health

# 创建会话
curl -X POST http://localhost:8000/api/sessions

# 发送消息（带上session_id实现连续对话）
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "你好，你是谁？", "session_id": "你的session_id"}'

# 查看历史
curl http://localhost:8000/api/sessions/{session_id}/history
```

---

## 📊 API 接口文档

启动后访问：`http://localhost:8000/docs`（Swagger UI自动生成）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sessions` | POST | 创建新会话 |
| `/api/sessions` | GET | 获取所有会话 |
| `/api/sessions/{id}/history` | GET | 获取会话历史 |
| `/api/chat` | POST | 发送消息（非流式） |
| `/api/chat/stream` | POST | 发送消息（流式） |
| `/api/health` | GET | 健康检查 |

---

## 🎯 前端对接示例（你熟悉的JS）

```javascript
// 创建会话
async function createSession() {
  const res = await fetch('http://localhost:8000/api/sessions', {
    method: 'POST'
  });
  const data = await res.json();
  return data.session_id;
}

// 发送消息
async function sendMessage(sessionId, question) {
  const res = await fetch('http://localhost:8000/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId })
  });
  return await res.json();
}

// 流式接收
async function streamChat(sessionId, question, onChunk) {
  const res = await fetch('http://localhost:8000/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId })
  });
  
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const text = decoder.decode(value);
    const lines = text.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'content') {
            onChunk(data.text);
          }
        } catch (e) {}
      }
    }
  }
}
```

---

## 🔧 后期维护与扩展

### 扩展1: 添加用户认证
```python
# 使用 fastapi-users 或 JWT
pip install python-jose[cryptography] passlib[bcrypt]
```

### 扩展2: 知识库管理接口
```python
# 添加上传文档、删除文档的API
@router.post("/knowledge/upload")
async def upload_document(file: UploadFile):
    ...
```

### 扩展3: 多租户支持
```python
# 在 session 表中添加 tenant_id
# 向量库使用不同的 collection
```

### 扩展4: 监控与日志
```python
pip install loguru prometheus-fastapi-instrumentator
```

---
