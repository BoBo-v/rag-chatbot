"""
app/main.py
FastAPI 应用入口（整合用户认证）
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, init_components
from app.api.auth_routes import router as auth_router, init_auth
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 正在启动 RAG 系统...")

    # 初始化用户认证模块
    auth_db_path = str(settings.CHAT_HISTORY_DIR / "users.db")
    await init_auth(auth_db_path)

    # 初始化 RAG 组件
    await init_components()

    print(f"✅ {settings.BOT_NAME} 准备就绪!")
    print(f"📖 API文档: http://localhost:8000/docs")

    yield

    print("👋 系统关闭")


# 创建应用
app = FastAPI(
    title=f"{settings.BOT_NAME} API",
    description="本地知识库智能问答系统（带用户认证）",
    version="1.0.4",
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
app.include_router(auth_router, prefix="/api")  # 认证路由
app.include_router(router, prefix="/api")        # 业务路由


@app.get("/")
def root():
    return {
        "name": settings.BOT_NAME,
        "company": settings.BOT_COMPANY,
        "status": "running",
        "docs": "/docs",
        "version": "1.0.4"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",        port=8000,
        reload=True
    )