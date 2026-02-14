"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager #Python提供的 异步生命周期管理器
from fastapi import FastAPI  #创建 FastAPI 应用核心类
from fastapi.middleware.cors import CORSMiddleware #CORS 中间件 解决跨域访问的问题

from app.api.routes import router, init_components
from app.api.auth_routes import router as auth_router, init_auth
from app.api.agent_routes import router as agent_router  # 新增
from app.config import settings


@asynccontextmanager #这是 FastAPI 官方推荐的生命周期写法
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("🚀 正在启动系统...")

    # 初始化认证模块 读取用户数据库路径
    # 初始化用户表
    auth_db_path = str(settings.CHAT_HISTORY_DIR / "users.db")
    await init_auth(auth_db_path)

    # 初始化 RAG 组件
    await init_components()

    # 打印已注册的工具
    from app.tools.registry import tool_registry
    print(f"🔧 已注册 {len(tool_registry.list_tools())} 个工具")

    print(f"✅ {settings.BOT_NAME} 准备就绪!")
    print(f"📖 API文档: http://localhost:8001/docs")

    yield

    print("👋 系统关闭")


#激活临时环境 venv\Scripts\activate
#创建临时环境 python -m venv venv
#启动项目 python -m app.main
#启动  uvicorn app.main:app --reload

# 创建应用
app = FastAPI(
    title=f"{settings.BOT_NAME} API",
    description="RAG + Agent 智能问答系统",
    version="2.0.0",
    lifespan=lifespan
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api")   # 认证路由
app.include_router(router, prefix="/api")         # RAG 路由
app.include_router(agent_router, prefix="/api")   # Agent 路由（新增）


@app.get("/")
def root():
    return {
        "name": settings.BOT_NAME,
        "company": settings.BOT_COMPANY,
        "status": "running",
        "docs": "/docs",
        "version": "2.0.0",
        "features": ["RAG", "Agent", "多轮对话", "工具调用"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)