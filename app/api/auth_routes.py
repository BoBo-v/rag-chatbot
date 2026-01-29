"""
app/api/auth_routes.py
用户认证 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional

from app.core.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    UserManager, create_access_token, decode_token
)

router = APIRouter(prefix="/auth", tags=["认证"])

# 用户管理器（在 main.py 中初始化后设置）
user_manager: UserManager = None


async def init_auth(db_path: str):
    """初始化认证模块"""
    global user_manager
    user_manager = UserManager(db_path)
    await user_manager.init_db()
    print("✅ 用户认证模块初始化完成")


# ========== 获取当前用户（依赖注入）==========
async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    从请求头获取并验证用户
    使用方式：在需要登录的接口添加 user: dict = Depends(get_current_user)
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="认证格式错误")

    token = parts[1]
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Token无效或已过期")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token无效")

    user = await user_manager.get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user


async def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """可选的用户验证，未登录返回 None"""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


# ========== API 路由 ==========

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """
    用户注册
    """
    if len(user_data.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少3个字符")
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6个字符")

    user = await user_manager.create_user(user_data)
    if not user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """
    用户登录
    """
    user = await user_manager.authenticate(login_data.username, login_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = create_access_token(data={"sub": str(user["id"])})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"]
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """
    获取当前登录用户信息
    """
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        created_at=user["created_at"]
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: dict = Depends(get_current_user)):
    """刷新 Token"""
    access_token = create_access_token(data={"sub": str(user["id"])})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            created_at=user["created_at"]
        )
    )