"""
请求上下文中间件

在请求生命周期内存储和传递当前用户上下文
"""

from contextvars import ContextVar
from typing import Optional, Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# 上下文变量
user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("user_context", default=None)
request_context: ContextVar[Optional[Request]] = ContextVar("request_context", default=None)


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    用户上下文中间件
    
    在每个请求开始时设置用户上下文，请求结束时清理
    """
    
    async def dispatch(self, request: Request, call_next):
        # 尝试从请求中获取用户身份
        user = await self._extract_user_from_request(request)
        
        # 设置上下文
        token = user_context.set(user)
        req_token = request_context.set(request)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # 清理上下文
            user_context.reset(token)
            request_context.reset(req_token)
    
    async def _extract_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        从请求中提取用户信息
        
        尝试多种认证方式：
        1. JWT Bearer Token
        2. API Key
        3. Share Link
        """
        # 从请求状态中获取（由依赖项设置）
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user
        
        # 尝试从 Authorization header 解析 JWT
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            from utils.jwt_auth import decode_token
            token = auth_header[7:]  # Remove "Bearer "
            payload = decode_token(token)
            if payload:
                return {
                    "id": payload.get("sub", "unknown"),
                    "type": payload.get("type", "user"),
                    "name": payload.get("name", payload.get("sub", "unknown")),
                    "email": payload.get("email"),
                    "is_admin": payload.get("is_admin", False),
                    "auth_method": "jwt",
                }
        
        # 尝试 API Key（简化版，完整逻辑在 api_auth.py）
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key:
            # 这里只是标记，详细验证在依赖项中
            return {
                "id": f"api_key_{api_key[:8]}",
                "type": "api_key",
                "name": "API Key User",
                "auth_method": "api_key",
            }
        
        # 匿名用户
        return {
            "id": "anonymous",
            "type": "anonymous",
            "name": "Anonymous",
            "auth_method": "none",
        }


def get_current_user_context() -> Optional[Dict[str, Any]]:
    """
    获取当前用户上下文
    
    在服务层任何地方调用此函数获取当前用户
    
    Returns:
        用户字典或 None
    """
    return user_context.get()


def get_current_user_id() -> str:
    """
    获取当前用户 ID
    
    在服务层使用，替代硬编码的 "system"
    
    Returns:
        用户 ID，如果没有则返回 "system"
    """
    user = user_context.get()
    if user:
        return user.get("id", "system")
    return "system"


def get_current_request() -> Optional[Request]:
    """
    获取当前请求对象
    
    Returns:
        当前请求或 None
    """
    return request_context.get()


class RequestStateUserMiddleware(BaseHTTPMiddleware):
    """
    备选中间件：使用 request.state 存储用户
    
    如果上下文变量方式有问题，可以使用此中间件
    """
    
    async def dispatch(self, request: Request, call_next):
        # 初始化 user
        request.state.user = None
        request.state.auth = None
        
        response = await call_next(request)
        return response
