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