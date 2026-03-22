"""
当前用户获取工具

在服务层使用，替代硬编码的 "system" 用户 ID
"""

from typing import Optional, Dict, Any

# 导入上下文获取函数
from src.middleware.context import get_current_user_context, get_current_user_id


__all__ = [
    "get_current_user",
    "get_current_user_id",
    "get_user_id_safe",
    "require_user",
]


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    获取当前登录用户
    
    Returns:
        用户字典，包含 id, type, name 等
        如果没有认证用户返回 None
    """
    return get_current_user_context()


def get_user_id_safe(fallback: str = "system") -> str:
    """
    安全地获取用户 ID
    
    如果有认证用户返回用户 ID，否则返回 fallback 值
    
    Args:
        fallback: 没有用户时的默认值，默认 "system"
    
    Returns:
        用户 ID 或 fallback
    """
    user = get_current_user_context()
    if user and user.get("id") and user.get("id") != "anonymous":
        return user["id"]
    return fallback


def require_user() -> Dict[str, Any]:
    """
    要求必须有登录用户
    
    Raises:
        RuntimeError: 如果没有登录用户
    
    Returns:
        用户字典
    """
    user = get_current_user_context()
    if not user:
        raise RuntimeError("Authentication required: no current user found")
    if user.get("id") == "anonymous":
        raise RuntimeError("Authentication required: anonymous user not allowed")
    return user


# 便捷属性获取函数
def get_current_user_name() -> str:
    """获取当前用户名"""
    user = get_current_user_context()
    if user:
        return user.get("name") or user.get("id") or "Unknown"
    return "System"


def get_current_user_type() -> str:
    """获取当前用户类型 (user/agent/api_key/anonymous)"""
    user = get_current_user_context()
    if user:
        return user.get("type", "unknown")
    return "system"


def is_current_user_admin() -> bool:
    """检查当前用户是否是管理员"""
    user = get_current_user_context()
    if user:
        return user.get("is_admin", False)
    return False
