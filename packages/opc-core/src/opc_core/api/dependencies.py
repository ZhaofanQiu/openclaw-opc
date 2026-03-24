"""
opc-core: 依赖项和数据库会话

FastAPI 依赖注入配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from opc_database import get_session
from opc_database.repositories import EmployeeRepository, TaskRepository

# 安全认证
security = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator:
    """获取数据库会话（依赖注入用）"""
    async with get_session() as session:
        yield session


async def get_employee_repo(session=Depends(get_db_session)) -> EmployeeRepository:
    """获取员工 Repository"""
    return EmployeeRepository(session)


async def get_task_repo(session=Depends(get_db_session)) -> TaskRepository:
    """获取任务 Repository"""
    return TaskRepository(session)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    验证 API Key
    
    如果配置了 API_KEY 环境变量，则必须提供正确的 key
    未配置或提供正确 key 时通过
    """
    import os
    
    api_key = os.getenv("OPC_API_KEY")
    
    # 如果没有配置 API_KEY，允许通过
    if not api_key:
        return None
    
    # 需要验证
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if credentials.credentials != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return credentials.credentials
