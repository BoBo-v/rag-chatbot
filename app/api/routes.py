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