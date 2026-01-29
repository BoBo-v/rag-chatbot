"""
app/core/auth.py
用户认证核心模块
"""
from datetime import datetime, timedelta
from typing import Optional
import aiosqlite
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings

# ========== 密码加密 ==========
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


# ========== JWT Token ==========
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解析 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ========== 用户数据模型 ==========
class UserCreate(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: Optional[str] = None


class UserLogin(BaseModel):
    """登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: Optional[str] = None
    created_at: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ========== 用户管理器 ==========
class UserManager:
    """用户数据库管理"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化用户表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS users
                             (
                                 id
                                 INTEGER
                                 PRIMARY
                                 KEY
                                 AUTOINCREMENT,
                                 username
                                 TEXT
                                 UNIQUE
                                 NOT
                                 NULL,
                                 password_hash
                                 TEXT
                                 NOT
                                 NULL,
                                 email
                                 TEXT,
                                 created_at
                                 TEXT,
                                 updated_at
                                 TEXT
                             )
                             """)
            await db.execute("""
                             CREATE INDEX IF NOT EXISTS idx_users_username
                                 ON users(username)
                             """)
            await db.commit()

    async def create_user(self, user: UserCreate) -> Optional[UserResponse]:
        """创建用户"""
        now = datetime.now().isoformat()
        password_hash = hash_password(user.password)

        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """INSERT INTO users (username, password_hash, email, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user.username, password_hash, user.email, now, now)
                )
                await db.commit()
                user_id = cursor.lastrowid

                return UserResponse(
                    id=user_id,
                    username=user.username,
                    email=user.email,
                    created_at=now
                )
        except aiosqlite.IntegrityError:
            return None

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取用户"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """根据ID获取用户"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """验证用户登录"""
        user = await self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user