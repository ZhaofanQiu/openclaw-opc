# JWT 认证中间件

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Agent

# 配置
SECRET_KEY = "opc-secret-key-change-in-production"  # 生产环境需要修改
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 安全方案
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
    
    Returns:
        JWT 令牌字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT 令牌
    
    Args:
        token: JWT 令牌
    
    Returns:
        解码后的数据，或 None 如果无效
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取当前用户（从 JWT 令牌）
    
    用于 FastAPI Depends 注入当前用户
    
    Args:
        credentials: HTTP Authorization 凭证
        db: 数据库会话
    
    Returns:
        用户字典，包含 id, type, name 等
    
    Raises:
        HTTPException: 401 如果认证失败
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    user_type: str = payload.get("type", "user")
    
    if user_id is None:
        raise credentials_exception
    
    # 返回用户信息字典
    return {
        "id": user_id,
        "type": user_type,
        "name": payload.get("name", user_id),
        "email": payload.get("email"),
        "is_admin": payload.get("is_admin", False),
    }


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    获取当前用户（可选）
    
    如果认证失败返回 None，不抛出异常
    """
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


class UserContext:
    """
    用户上下文管理器
    
    用于在服务层获取当前用户
    """
    _current_user: Optional[Dict[str, Any]] = None
    
    @classmethod
    def set_current_user(cls, user: Dict[str, Any]):
        """设置当前用户"""
        cls._current_user = user
    
    @classmethod
    def get_current_user(cls) -> Optional[Dict[str, Any]]:
        """获取当前用户"""
        return cls._current_user
    
    @classmethod
    def clear(cls):
        """清除当前用户"""
        cls._current_user = None
    
    @classmethod
    def get_user_id(cls) -> str:
        """获取当前用户 ID，如果没有则返回 system"""
        if cls._current_user:
            return cls._current_user.get("id", "system")
        return "system"


def get_current_user_id() -> str:
    """
    获取当前用户 ID 的快捷函数
    
    在服务层使用，替代硬编码的 "system"
    """
    return UserContext.get_user_id()
