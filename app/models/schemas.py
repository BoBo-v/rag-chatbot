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