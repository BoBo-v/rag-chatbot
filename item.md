# RAG 智能客服系统 - 代码架构详解

> 适合读者：有前端经验、Python零基础的开发者
> 项目定位：本地知识库问答系统，支持用户认证、连续对话、流式输出

---

## 📁 项目结构总览

```
rag-chatbot/
│
├── app/                        # 🔥 核心应用代码
│   ├── __init__.py            # 包标识文件
│   ├── config.py              # 配置管理
│   ├── main.py                # 应用入口
│   │
│   ├── api/                   # API 路由层
│   │   ├── __init__.py
│   │   ├── auth_routes.py     # 认证相关接口
│   │   └── routes.py          # 业务接口（聊天、会话）
│   │
│   ├── core/                  # 核心业务逻辑
│   │   ├── __init__.py
│   │   ├── auth.py            # 用户认证逻辑
│   │   ├── chat_memory.py     # 对话记忆管理
│   │   ├── rag_engine.py      # RAG 问答引擎
│   │   └── vector_store.py    # 向量数据库管理
│   │
│   └── models/                # 数据模型
│       ├── __init__.py
│       └── schemas.py         # Pydantic 模型定义
│
├── chat_history/              # 💾 数据存储
│   ├── chat.db               # 聊天记录数据库
│   └── users.db              # 用户数据库
│
├── data/                      # 📚 知识库文档
│   └── *.txt, *.md           # 原始文档文件
│
├── vectorstore/               # 🔢 向量数据库
│   └── chroma_db/            # Chroma 持久化存储
│       └── chroma.sqlite3    # 向量索引
│
├── .env                       # 环境变量配置
├── requirements.txt           # Python 依赖
└── venv/                      # 虚拟环境
```

---

## 🏗️ 整体架构设计

### 分层架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端 (Vue.js)                            │
│                   AuthView.vue / ChatView.vue                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP 请求
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API 路由层 (api/)                          │
│              auth_routes.py    routes.py                        │
│         ┌─────────────────┬─────────────────┐                   │
│         │  /auth/login    │   /chat         │                   │
│         │  /auth/register │   /sessions     │                   │
│         └─────────────────┴─────────────────┘                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ 调用
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      核心业务层 (core/)                         │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐            │
│  │ auth.py  │  │ rag_engine.py│  │ chat_memory.py │            │
│  │ 用户认证  │  │  RAG 引擎    │  │   对话记忆     │            │
│  └──────────┘  └──────┬───────┘  └───────┬────────┘            │
│                       │                   │                     │
│                       ▼                   │                     │
│              ┌────────────────┐           │                     │
│              │vector_store.py │           │                     │
│              │   向量检索     │           │                     │
│              └────────────────┘           │                     │
└─────────────────────┬─────────────────────┼─────────────────────┘
                      │                     │
                      ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据存储层                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ Chroma DB  │  │  SQLite    │  │   Ollama   │                │
│  │  向量库    │  │ 聊天/用户  │  │  LLM 服务  │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### 为什么这样分层？

| 层级 | 职责 | 类比前端 |
|------|------|----------|
| API 路由层 | 接收请求、参数验证、返回响应 | Express 路由 / Vue Router |
| 核心业务层 | 业务逻辑处理 | Vuex actions / 业务 hooks |
| 数据存储层 | 数据持久化 | localStorage / IndexedDB |

**好处：**
- 每层职责单一，易于维护
- 可以独立测试每一层
- 替换某一层不影响其他层（如换数据库）

---

## 📄 各模块详解

### 1. config.py - 配置管理

```python
"""
作用：集中管理所有配置，支持环境变量覆盖
类比JS：类似于 .env + config.js
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # 机器人配置
    BOT_NAME: str = "小智"              # 默认值
    BOT_COMPANY: str = "XXX科技"
    
    # 模型配置
    LLM_MODEL: str = "qwen2.5:7b"       # 对话模型
    EMBEDDING_MODEL: str = "bge-m3"     # 向量模型
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # 路径配置（使用 Path 对象，跨平台兼容）
    BASE_DIR: Path = Path(__file__).parent.parent  # 项目根目录
    DATA_DIR: Path = BASE_DIR / "data"             # 知识库目录
    VECTOR_DB_DIR: Path = BASE_DIR / "vectorstore" / "chroma_db"
    CHAT_HISTORY_DIR: Path = BASE_DIR / "chat_history"
    
    # JWT 认证配置
    SECRET_KEY: str = "your-secret-key"  # 生产环境必须改！
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    class Config:
        env_file = ".env"  # 从 .env 文件读取配置


# 创建全局配置实例（单例模式）
settings = Settings()
```

**为什么用 Pydantic Settings？**
- 自动类型验证（确保配置值类型正确）
- 支持从环境变量读取（部署时不用改代码）
- 提供默认值（开发时零配置启动）

**类比 JavaScript：**
```javascript
// JS 中的类似实现
const settings = {
  botName: process.env.BOT_NAME || '小智',
  secretKey: process.env.SECRET_KEY || 'default-key'
}
```

---

### 2. main.py - 应用入口

```python
"""
作用：FastAPI 应用的入口点，负责：
1. 创建 FastAPI 应用实例
2. 配置中间件（CORS 等）
3. 注册路由
4. 管理应用生命周期（启动/关闭）

类比JS：类似于 Express 的 app.js 或 Vue 的 main.js
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, init_components
from app.api.auth_routes import router as auth_router, init_auth
from app.config import settings


# ========== 生命周期管理 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动和关闭时执行的代码
    类比：Vue 的 onMounted / onUnmounted
    """
    # ----- 启动时执行 -----
    print("🚀 正在启动 RAG 系统...")
    
    # 初始化用户认证
    auth_db_path = str(settings.CHAT_HISTORY_DIR / "users.db")
    await init_auth(auth_db_path)
    
    # 初始化 RAG 组件（向量库、记忆管理等）
    await init_components()
    
    print(f"✅ {settings.BOT_NAME} 准备就绪!")
    
    yield  # 应用运行中...
    
    # ----- 关闭时执行 -----
    print("👋 系统关闭")


# ========== 创建应用 ==========
app = FastAPI(
    title=f"{settings.BOT_NAME} API",
    description="本地知识库智能问答系统",
    version="2.0.0",
    lifespan=lifespan  # 绑定生命周期
)


# ========== 中间件配置 ==========
# CORS：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 生产环境改成具体域名
    allow_credentials=True,
    allow_methods=["*"],       # 允许所有 HTTP 方法
    allow_headers=["*"],       # 允许所有请求头
)


# ========== 注册路由 ==========
app.include_router(auth_router, prefix="/api")  # /api/auth/...
app.include_router(router, prefix="/api")        # /api/chat/...


# ========== 根路径 ==========
@app.get("/")
def root():
    return {
        "name": settings.BOT_NAME,
        "status": "running",
        "docs": "/docs"  # Swagger 文档地址
    }


# ========== 直接运行入口 ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",   # 模块路径:应用实例
        host="0.0.0.0",   # 监听所有网络接口
        port=8000,
        reload=True       # 开发模式：代码改动自动重启
    )
```

**类比 Express.js：**
```javascript
const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());
app.use('/api/auth', authRouter);
app.use('/api', chatRouter);

app.listen(8000);
```

---

### 3. models/schemas.py - 数据模型

```python
"""
作用：定义请求和响应的数据结构
类比JS：TypeScript 的 interface / type

为什么需要？
1. 自动验证请求参数
2. 自动生成 API 文档
3. IDE 智能提示
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ========== 请求模型 ==========
class ChatRequest(BaseModel):
    """聊天请求"""
    question: str = Field(..., min_length=1, description="用户问题")
    # Field(...) 中的 ... 表示必填
    # min_length=1 表示至少1个字符
    
    session_id: Optional[str] = Field(None, description="会话ID")
    # Optional[str] 表示可以是 str 或 None
    # Field(None) 表示默认值是 None


class UserLogin(BaseModel):
    """登录请求"""
    username: str
    password: str


# ========== 响应模型 ==========
class ChatResponse(BaseModel):
    """聊天响应"""
    answer: str
    session_id: str
    sources: list[str] = []  # 默认空列表
    timestamp: datetime = Field(default_factory=datetime.now)
    # default_factory 表示每次创建实例时调用这个函数


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: Optional[str] = None
    created_at: str
```

**类比 TypeScript：**
```typescript
interface ChatRequest {
  question: string;
  session_id?: string;
}

interface ChatResponse {
  answer: string;
  session_id: string;
  sources: string[];
  timestamp: Date;
}
```

**FastAPI 如何使用这些模型：**
```python
@router.post("/chat", response_model=ChatResponse)  # 响应模型
async def chat(request: ChatRequest):                # 请求模型
    # FastAPI 自动：
    # 1. 验证 request 的字段
    # 2. 验证返回值符合 ChatResponse
    # 3. 生成 Swagger 文档
    pass
```

---

### 4. core/auth.py - 用户认证

```python
"""
作用：处理用户注册、登录、密码加密、Token 生成
核心概念：
1. 密码加密：不存储明文密码
2. JWT Token：无状态认证
"""
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite
import hashlib
import secrets
from jose import jwt
from app.config import settings


# ========== 密码加密 ==========
def hash_password(password: str) -> str:
    """
    为什么要加密？
    - 数据库泄露时，攻击者无法直接获取密码
    - 即使看到哈希值，也无法反推原密码
    
    使用 PBKDF2-SHA256 算法：
    - 加盐（salt）：防止彩虹表攻击
    - 多次迭代（100000次）：增加破解难度
    """
    salt = secrets.token_hex(16)  # 生成随机盐
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',                   # 哈希算法
        password.encode('utf-8'),   # 原始密码
        salt.encode('utf-8'),       # 盐
        100000                      # 迭代次数
    )
    return f"{salt}:{pw_hash.hex()}"  # 返回格式：盐:哈希值


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    salt, pw_hash = hashed_password.split(':')
    new_hash = hashlib.pbkdf2_hmac(
        'sha256',
        plain_password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return new_hash.hex() == pw_hash  # 比较哈希值


# ========== JWT Token ==========
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT (JSON Web Token) 工作原理：
    
    Token 结构：header.payload.signature
    
    header:  {"alg": "HS256", "typ": "JWT"}
    payload: {"sub": "user_id", "exp": 过期时间}
    signature: HMAC-SHA256(header + payload, SECRET_KEY)
    
    为什么用 JWT？
    - 无状态：服务端不需要存储 session
    - 可扩展：多服务器可以共享验证
    - 安全：签名保证不被篡改
    """
    to_encode = data.copy()
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    # 生成 Token
    encoded_jwt = jwt.encode(
        to_encode,              # 载荷数据
        settings.SECRET_KEY,    # 密钥（必须保密！）
        algorithm=settings.ALGORITHM  # 签名算法
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解析并验证 Token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except:
        return None  # Token 无效或过期


# ========== 用户管理器 ==========
class UserManager:
    """
    用户数据库操作封装
    使用 SQLite + aiosqlite（异步）
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init_db(self):
        """创建用户表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    created_at TEXT
                )
            """)
            await db.commit()
    
    async def create_user(self, username: str, password: str) -> Optional[dict]:
        """创建用户"""
        password_hash = hash_password(password)
        now = datetime.now().isoformat()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, password_hash, now)
                )
                await db.commit()
                return {"id": cursor.lastrowid, "username": username}
        except:
            return None  # 用户名已存在
    
    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """验证用户登录"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            user = await cursor.fetchone()
        
        if not user:
            return None
        
        # user 是元组：(id, username, password_hash, email, created_at)
        if not verify_password(password, user[2]):
            return None
        
        return {"id": user[0], "username": user[1]}
```

**认证流程图：**
```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  注册    │ →  │ 加密密码 │ →  │ 存数据库 │
└──────────┘    └──────────┘    └──────────┘

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  登录    │ →  │ 验证密码 │ →  │ 生成JWT  │ →  │ 返回前端 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 请求API  │ →  │携带Token │ →  │ 验证JWT  │ →  │ 返回数据 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

---

### 5. core/chat_memory.py - 对话记忆管理

```python
"""
作用：管理多轮对话的上下文
解决问题：LLM 本身无记忆，每次请求都是独立的

实现方案：
1. 每个用户有多个会话（session）
2. 每个会话存储聊天历史
3. 发送请求时，把历史消息一起发给 LLM
"""
import uuid
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """单条消息"""
    role: str      # "human" 或 "ai"
    content: str   # 消息内容
    timestamp: str # 时间戳


class ChatMemoryManager:
    """
    聊天记忆管理器
    
    数据结构：
    sessions 表：存储会话信息
    messages 表：存储聊天消息
    
    关系：一个 session 有多个 messages（一对多）
    """
    
    def __init__(self, db_path: str, max_history: int = 10):
        self.db_path = db_path
        self.max_history = max_history  # 最多保留多少轮对话
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            # 会话表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            # 消息表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,           -- 'human' 或 'ai'
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            # 创建索引，加速按 session_id 查询
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages(session_id)
            """)
            await db.commit()
    
    async def create_session(self, user_id: Optional[str] = None) -> str:
        """
        创建新会话
        返回：session_id（UUID格式）
        """
        session_id = str(uuid.uuid4())  # 生成唯一ID
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (session_id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, user_id, now, now)
            )
            await db.commit()
        
        return session_id
    
    async def add_message(self, session_id: str, role: str, content: str):
        """
        添加消息到会话
        
        为什么同时存用户消息和AI回复？
        - 下次请求时，需要把完整对话历史发给LLM
        - LLM 才能理解上下文
        """
        now = datetime.now().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now)
            )
            await db.commit()
    
    async def get_history(self, session_id: str, limit: Optional[int] = None) -> list[ChatMessage]:
        """
        获取会话历史
        
        limit：限制返回条数（避免上下文过长）
        
        为什么要限制？
        - LLM 有上下文长度限制（如 4096 tokens）
        - 太长的历史会导致响应变慢
        - 太早的对话可能不相关
        """
        limit = limit or self.max_history
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT role, content, timestamp FROM messages 
                   WHERE session_id = ? 
                   ORDER BY id DESC LIMIT ?""",
                (session_id, limit * 2)  # *2 因为一轮对话有2条消息
            )
            rows = await cursor.fetchall()
        
        # 反转顺序（从旧到新）
        messages = [
            ChatMessage(role=row[0], content=row[1], timestamp=row[2])
            for row in reversed(rows)
        ]
        return messages


def format_history_for_prompt(messages: list[ChatMessage]) -> str:
    """
    将历史消息格式化为字符串，用于放入 prompt
    
    示例输出：
    用户: 你好
    助手: 你好！有什么可以帮助你的吗？
    用户: RAG是什么？
    """
    if not messages:
        return ""
    
    lines = []
    for msg in messages:
        role_name = "用户" if msg.role == "human" else "助手"
        lines.append(f"{role_name}: {msg.content}")
    
    return "\n".join(lines)
```

**对话记忆工作流程：**
```
第一轮对话：
用户: "你好"
→ 发给LLM: "你好"
← LLM回复: "你好！"
→ 存储: [用户:你好, AI:你好！]

第二轮对话：
用户: "RAG是什么？"
→ 发给LLM: 
  "历史对话:
   用户: 你好
   助手: 你好！
   
   当前问题: RAG是什么？"
← LLM回复: "RAG是..."（LLM能理解上下文）
```

---

### 6. core/vector_store.py - 向量数据库管理

```python
"""
作用：管理知识库的向量化和检索
核心概念：
1. Embedding：将文本转换为向量（数字列表）
2. 向量相似度：通过计算向量距离找相关文档
3. 语义搜索：比关键词搜索更智能

工作原理：
文本 → Embedding模型 → 向量 [0.1, 0.3, -0.2, ...] → 存入向量库
查询 → Embedding模型 → 向量 → 在向量库中找最相似的向量 → 返回原文
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
        # 初始化 Embedding 模型（用于将文本转向量）
        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,  # bge-m3
            base_url=settings.OLLAMA_BASE_URL
        )
        self.vectordb: Optional[Chroma] = None
        self.chunks_count = 0
    
    def load_documents(self, data_dir: Path) -> list[Document]:
        """
        从目录加载文档
        
        支持格式：.txt, .md
        返回：Document 列表（包含内容和元数据）
        """
        documents = []
        
        for file_path in data_dir.glob("*"):
            if file_path.suffix in [".txt", ".md"]:
                content = file_path.read_text(encoding="utf-8")
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": file_path.name,  # 记录来源
                        "file_type": file_path.suffix
                    }
                )
                documents.append(doc)
                print(f"  ✓ 加载: {file_path.name}")
        
        return documents
    
    def split_documents(self, documents: list[Document]) -> list[Document]:
        """
        文档分块
        
        为什么要分块？
        1. LLM 上下文长度有限
        2. 检索粒度更细，更精准
        3. 避免无关内容干扰
        
        分块策略：
        - chunk_size=500: 每块约500字符
        - chunk_overlap=100: 块之间重叠100字符（避免切断句子）
        - separators: 优先在段落、句子边界切分
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
            # 优先级从高到低：段落 > 换行 > 句号 > 其他标点 > 空格 > 字符
        )
        chunks = splitter.split_documents(documents)
        return chunks
    
    def create_vectorstore(self, chunks: list[Document], persist: bool = True):
        """
        创建向量数据库
        
        过程：
        1. 将每个 chunk 的文本通过 Embedding 模型转为向量
        2. 将向量和原文一起存入 Chroma 数据库
        3. 持久化到磁盘（下次启动不用重建）
        """
        persist_dir = str(settings.VECTOR_DB_DIR) if persist else None
        
        self.vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=persist_dir,  # 持久化目录
            collection_name="knowledge_base"
        )
        self.chunks_count = len(chunks)
        print(f"✅ 向量库创建完成，共 {self.chunks_count} 个文档块")
    
    def load_vectorstore(self):
        """加载已有的向量数据库（启动时调用）"""
        persist_dir = str(settings.VECTOR_DB_DIR)
        
        if not Path(persist_dir).exists():
            raise FileNotFoundError(f"向量库不存在: {persist_dir}")
        
        self.vectordb = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings,
            collection_name="knowledge_base"
        )
        self.chunks_count = self.vectordb._collection.count()
        print(f"✅ 向量库加载完成，共 {self.chunks_count} 个文档块")
    
    def get_retriever(self):
        """
        获取检索器
        
        search_type="mmr": 最大边际相关性
        - 平衡相关性和多样性
        - 避免返回内容重复的文档
        
        参数说明：
        - k=5: 最终返回5个文档
        - fetch_k=20: 先检索20个候选
        - lambda_mult=0.7: 相关性权重（越大越注重相关性）
        """
        return self.vectordb.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 5,
                "fetch_k": 20,
                "lambda_mult": 0.7
            }
        )


# 全局单例
vector_manager = VectorStoreManager()
```

**向量检索原理图：**
```
知识库构建：
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 原始文档    │ →  │   分块      │ →  │  向量化     │
│ product.txt │    │ chunk1      │    │ [0.1, 0.3,  │
│             │    │ chunk2      │    │  -0.2, ...] │
│             │    │ ...         │    │             │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                                             ▼
                                    ┌─────────────┐
                                    │ Chroma DB   │
                                    │ 向量数据库   │
                                    └─────────────┘

检索过程：
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 用户问题    │ →  │  向量化     │ →  │ 相似度搜索  │
│ "RAG是什么" │    │ [0.2, 0.1,  │    │ 找最近的向量 │
│             │    │  -0.1, ...] │    │             │
└─────────────┘    └─────────────┘    └──────┬──────┘
                                             │
                                             ▼
                                    ┌─────────────┐
                                    │ 返回相关文档 │
                                    │ chunk1      │
                                    │ chunk3      │
                                    └─────────────┘
```

---

### 7. core/rag_engine.py - RAG 问答引擎

```python
"""
作用：整合所有组件，实现 RAG 问答
RAG = Retrieval-Augmented Generation（检索增强生成）

核心思想：
1. 先从知识库检索相关内容
2. 把检索结果作为上下文
3. 让 LLM 基于上下文回答问题

优势：
- LLM 有了专业知识（知识库提供）
- 减少幻觉（有据可依）
- 可更新（改知识库即可）
"""
from typing import AsyncGenerator
from langchain_ollama import OllamaLLM

from app.config import settings
from app.core.vector_store import vector_manager
from app.core.chat_memory import ChatMemoryManager, format_history_for_prompt


class RAGEngine:
    """RAG 问答引擎"""
    
    def __init__(self, memory_manager: ChatMemoryManager):
        self.memory = memory_manager
        
        # 初始化 LLM
        self.llm = OllamaLLM(
            model=settings.LLM_MODEL,       # qwen2.5:7b
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.7,  # 控制随机性（0=确定性，1=创造性）
            num_predict=1024  # 最大生成长度
        )
        
        # 获取检索器
        self.retriever = vector_manager.get_retriever()
    
    def _build_prompt(self, question: str, context: str, history: str = "") -> str:
        """
        构建 Prompt（提示词）
        
        Prompt Engineering 核心：
        1. 明确角色身份
        2. 提供知识上下文
        3. 给出回答规则
        4. 包含历史对话（连续对话）
        """
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
    
    async def ask(self, question: str, session_id: str) -> tuple[str, list[str]]:
        """
        处理问题（非流式）
        
        流程：
        1. 获取历史对话
        2. 检索相关文档
        3. 构建 Prompt
        4. 调用 LLM
        5. 保存对话
        """
        # 1. 获取历史对话
        history_messages = await self.memory.get_history(session_id)
        history_text = format_history_for_prompt(history_messages)
        
        # 2. 检索相关文档
        docs = self.retriever.invoke(question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        # 3. 构建 Prompt
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
    
    async def ask_stream(self, question: str, session_id: str) -> AsyncGenerator[str, None]:
        """
        流式问答
        
        为什么需要流式？
        - 用户体验更好（打字机效果）
        - 不用等待完整响应
        - 感觉更快
        
        实现原理：
        - LLM 生成是逐 token 的
        - 每生成一个 token 就 yield 出去
        - 前端收到后立即显示
        """
        # 1-3. 同上
        history_messages = await self.memory.get_history(session_id)
        history_text = format_history_for_prompt(history_messages)
        
        docs = self.retriever.invoke(question)
        context = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        prompt = self._build_prompt(question, context, history_text)
        
        # 4. 流式生成
        full_answer = ""
        for chunk in self.llm.stream(prompt):  # 逐块生成
            full_answer += chunk
            yield chunk  # 立即返回给前端
        
        # 5. 保存完整对话
        await self.memory.add_message(session_id, "human", question)
        await self.memory.add_message(session_id, "ai", full_answer)
```

**RAG 完整流程图：**
```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG 问答流程                            │
└─────────────────────────────────────────────────────────────────┘

用户输入: "RAG是什么？"
           │
           ▼
┌─────────────────────┐
│ 1. 获取历史对话     │  ← chat_memory.py
│    用户: 你好       │
│    AI: 你好！       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. 检索相关文档     │  ← vector_store.py
│    "RAG是什么" →   │
│    [doc1, doc2...] │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. 构建 Prompt      │
│                     │
│  系统提示 +         │
│  历史对话 +         │
│  知识库内容 +       │
│  用户问题           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 4. 调用 LLM         │  ← Ollama (qwen2.5:7b)
│    生成回答         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. 保存对话         │  ← chat_memory.py
│    存入数据库       │
└──────────┬──────────┘
           │
           ▼
返回: "RAG是检索增强生成技术..."
```

---

### 8. api/routes.py - 业务路由

```python
"""
作用：定义 API 接口
类比：Express 的路由文件
"""
import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.core.rag_engine import RAGEngine
from app.core.chat_memory import ChatMemoryManager
from app.core.vector_store import vector_manager
from app.config import settings

router = APIRouter()

# 全局组件（在 init_components 中初始化）
memory_manager: ChatMemoryManager = None
rag_engine: RAGEngine = None


async def init_components():
    """初始化所有组件（main.py 启动时调用）"""
    global memory_manager, rag_engine
    
    # 初始化记忆管理器
    db_path = str(settings.CHAT_HISTORY_DIR / "chat.db")
    memory_manager = ChatMemoryManager(db_path)
    await memory_manager.init_db()
    
    # 加载向量库
    try:
        vector_manager.load_vectorstore()
    except FileNotFoundError:
        # 向量库不存在，创建新的
        docs = vector_manager.load_documents(settings.DATA_DIR)
        if docs:
            chunks = vector_manager.split_documents(docs)
            vector_manager.create_vectorstore(chunks)
    
    # 初始化 RAG 引擎
    rag_engine = RAGEngine(memory_manager)


# ========== 会话管理接口 ==========

@router.post("/sessions")
async def create_session():
    """
    创建新会话
    
    POST /api/sessions
    返回: {"session_id": "uuid-xxx"}
    """
    session_id = await memory_manager.create_session()
    return {"session_id": session_id}


@router.get("/sessions")
async def list_sessions():
    """获取所有会话列表"""
    sessions = await memory_manager.get_all_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史记录"""
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
    
    POST /api/chat
    请求: {"question": "你好", "session_id": "可选"}
    返回: {"answer": "...", "session_id": "...", "sources": [...]}
    """
    # 处理会话
    session_id = request.session_id
    if not session_id:
        session_id = await memory_manager.create_session()
    elif not await memory_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 调用 RAG 引擎
    answer, sources = await rag_engine.ask(request.question, session_id)
    
    return ChatResponse(
        answer=answer,
        session_id=session_id,
        sources=sources
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口
    
    使用 SSE (Server-Sent Events) 协议
    返回格式：
    data: {"type": "session", "session_id": "xxx"}
    data: {"type": "content", "text": "你"}
    data: {"type": "content", "text": "好"}
    data: {"type": "done"}
    """
    session_id = request.session_id
    if not session_id:
        session_id = await memory_manager.create_session()
    elif not await memory_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    async def generate():
        # 发送 session_id
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        try:
            # 流式生成
            async for chunk in rag_engine.ask_stream(request.question, session_id):
                yield f"data: {json.dumps({'type': 'content', 'text': chunk})}\n\n"
                await asyncio.sleep(0.01)  # 小延迟，让前端有时间渲染

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",  # SSE 媒体类型
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

## 🔄 数据流总结

### 用户注册/登录流程

```
前端                     后端                          数据库
  │                       │                             │
  │  POST /auth/register  │                             │
  │ ───────────────────→  │                             │
  │  {username, password} │                             │
  │                       │  hash(password)             │
  │                       │ ─────────────────────────→  │
  │                       │  INSERT INTO users          │
  │                       │ ←─────────────────────────  │
  │                       │  user_id                    │
  │                       │                             │
  │                       │  create_jwt_token()         │
  │  {token, user}        │                             │
  │ ←───────────────────  │                             │
  │                       │                             │
```

### 聊天流程

```
前端                     后端                          外部服务
  │                       │                             │
  │  POST /chat/stream    │                             │
  │ ───────────────────→  │                             │
  │  {question, session}  │                             │
  │                       │                             │
  │                       │  get_history(session)       │
  │                       │ ───→ SQLite ───→            │
  │                       │                             │
  │                       │  retrieve(question)         │
  │                       │ ───→ ChromaDB ───→          │
  │                       │ ←─── [doc1, doc2] ←───      │
  │                       │                             │
  │                       │  build_prompt()             │
  │                       │                             │
  │                       │  llm.stream(prompt)         │
  │                       │ ───→ Ollama ───→            │
  │  data: {text: "你"}   │ ←─── "你" ←───              │
  │ ←───────────────────  │                             │
  │  data: {text: "好"}   │ ←─── "好" ←───              │
  │ ←───────────────────  │                             │
  │  ...                  │                             │
  │                       │  save_message()             │
  │                       │ ───→ SQLite ───→            │
  │  data: {type: done}   │                             │
  │ ←───────────────────  │                             │
```

---

## 📝 关键设计决策

### 1. 为什么用 SQLite 而不是 MySQL/PostgreSQL？

| 考虑因素 | SQLite | MySQL |
|----------|--------|-------|
| 部署复杂度 | 零配置，单文件 | 需要安装服务 |
| 性能 | 小规模够用 | 大规模更好 |
| 并发 | 写入会锁表 | 支持高并发 |
| 适用场景 | 单机、小团队 | 企业级 |

**结论**：本地知识库场景，SQLite 足够，简单优先。

### 2. 为什么用 Chroma 而不是 Pinecone/Milvus？

| 考虑因素 | Chroma | Pinecone |
|----------|--------|----------|
| 部署 | 本地嵌入式 | 云服务 |
| 成本 | 免费 | 按量付费 |
| 性能 | 中小规模够用 | 大规模更好 |
| 隐私 | 数据本地 | 数据在云端 |

**结论**：本地部署要求，Chroma 最合适。

### 3. 为什么用 Ollama 而不是 OpenAI API？

| 考虑因素 | Ollama | OpenAI |
|----------|--------|--------|
| 成本 | 免费 | 按 token 付费 |
| 隐私 | 完全本地 | 数据发送到云端 |
| 网络 | 无需联网 | 需要稳定网络 |
| 模型选择 | 多种开源模型 | GPT系列 |
| 响应速度 | 取决于硬件 | 较快 |

**结论**：本地部署 + 数据隐私要求，Ollama 是最佳选择。

---

## 🚀 扩展建议

### 短期优化
1. 添加消息搜索功能
2. 支持导出聊天记录
3. 添加对话标题自动生成

### 中期功能
1. 支持多种文档格式（PDF、Word）
2. 添加知识库管理后台
3. 支持多用户隔离

### 长期演进
1. 添加 Agent 能力（调用外部工具）
2. 支持多模态（图片、语音）
3. 分布式部署支持

---

## 📚 学习资源

- FastAPI 官方文档：https://fastapi.tiangolo.com/zh/
- LangChain 文档：https://python.langchain.com/
- Ollama 官网：https://ollama.ai/
- Chroma 文档：https://docs.trychroma.com/

---

*文档版本：v2.0 | 更新时间：2024年*