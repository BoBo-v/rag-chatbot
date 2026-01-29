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
                             CREATE TABLE IF NOT EXISTS sessions
                             (
                                 session_id
                                 TEXT
                                 PRIMARY
                                 KEY,
                                 user_id
                                 TEXT,
                                 created_at
                                 TEXT,
                                 updated_at
                                 TEXT,
                                 metadata
                                 TEXT
                             )
                             """)
            # 消息表
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS messages
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 session_id
                                 TEXT,
                                 role
                                 TEXT,
                                 content
                                 TEXT,
                                 timestamp
                                 TEXT,
                                 FOREIGN
                                 KEY
                             (
                                 session_id
                             ) REFERENCES sessions
                             (
                                 session_id
                             )
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
                """SELECT role, content, timestamp
                   FROM messages
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
                """SELECT s.session_id,
                          s.created_at,
                          s.updated_at,
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