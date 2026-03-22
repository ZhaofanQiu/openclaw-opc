"""
Shared Memory Router for v0.4.0

API endpoints for shared company memory management
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import SharedMemory
from src.models.shared_memory import MemoryCategory, MemoryScope
from src.services.shared_memory_service import SharedMemoryService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/memory", tags=["shared-memory"])


# ============== Request/Response Models ==============

class MemoryCreate(BaseModel):
    """Create memory request."""
    title: str = Field(..., min_length=1, max_length=200, description="记忆标题")
    content: str = Field(..., min_length=1, description="记忆内容")
    category: str = Field(default=MemoryCategory.GENERAL.value, description="分类")
    scope: str = Field(default=MemoryScope.COMPANY.value, description="范围")
    tags: List[str] = Field(default=[], description="标签")
    importance: int = Field(default=3, ge=1, le=5, description="重要性 1-5")
    expires_hours: Optional[int] = Field(default=None, description="过期时间（小时）")


class MemoryUpdate(BaseModel):
    """Update memory request."""
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[int] = Field(default=None, ge=1, le=5)


class MemoryResponse(BaseModel):
    """Memory response model."""
    id: str
    agent_id: Optional[str]
    agent_name: Optional[str]
    title: str
    content: str
    category: str
    scope: str
    tags: List[str]
    importance: int
    access_count: int
    created_at: str
    updated_at: str
    expires_at: Optional[str]
    is_expired: bool
    
    class Config:
        from_attributes = True


class MemorySearchRequest(BaseModel):
    """Memory search request."""
    query: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default=[])
    importance_min: Optional[int] = Field(default=None, ge=1, le=5)


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""
    total_memories: int
    active_memories: int
    expired_memories: int
    category_distribution: dict
    total_access_count: int


class MemoryContextResponse(BaseModel):
    """Memory for agent context."""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    importance: int
    created_at: str


# ============== API Endpoints ==============

@router.post("", response_model=MemoryResponse)
async def create_memory(
    data: MemoryCreate,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """创建新的共享记忆。"""
    service = SharedMemoryService(db)
    try:
        memory = service.create_memory(
            agent_id=agent_id,
            title=data.title,
            content=data.content,
            category=data.category,
            scope=data.scope,
            tags=data.tags,
            importance=data.importance,
            expires_hours=data.expires_hours,
        )
        return _memory_to_response(memory, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    agent_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """列取共享记忆。"""
    service = SharedMemoryService(db)
    memories = service.search_memories(
        category=category,
        tags=[tag] if tag else None,
        agent_id_filter=agent_id,
        limit=limit,
        offset=offset,
    )
    return [_memory_to_response(m, db) for m in memories]


@router.post("/search", response_model=List[MemoryResponse])
async def search_memories(
    data: MemorySearchRequest,
    agent_id: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """搜索共享记忆。"""
    service = SharedMemoryService(db)
    memories = service.search_memories(
        query=data.query,
        category=data.category,
        tags=data.tags,
        agent_id=agent_id,
        importance_min=data.importance_min,
        limit=limit,
    )
    return [_memory_to_response(m, db) for m in memories]


@router.get("/recent", response_model=List[MemoryResponse])
async def get_recent_memories(
    category: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取最近创建的记忆。"""
    service = SharedMemoryService(db)
    memories = service.get_recent_memories(category=category, limit=limit)
    return [_memory_to_response(m, db) for m in memories]


@router.get("/popular", response_model=List[MemoryResponse])
async def get_popular_memories(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取最受欢迎的记忆。"""
    service = SharedMemoryService(db)
    memories = service.get_popular_memories(limit=limit)
    return [_memory_to_response(m, db) for m in memories]


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取单个记忆详情。"""
    service = SharedMemoryService(db)
    memory = service.get_memory(memory_id, agent_id=agent_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found or expired")
    return _memory_to_response(memory, db)


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    data: MemoryUpdate,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """更新记忆。"""
    service = SharedMemoryService(db)
    try:
        memory = service.update_memory(
            memory_id=memory_id,
            agent_id=agent_id,
            title=data.title,
            content=data.content,
            category=data.category,
            tags=data.tags,
            importance=data.importance,
        )
        return _memory_to_response(memory, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """删除记忆。"""
    service = SharedMemoryService(db)
    try:
        service.delete_memory(memory_id, agent_id)
        return {"success": True, "message": "Memory deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats/summary", response_model=MemoryStatsResponse)
async def get_memory_stats(
    db: Session = Depends(get_db),
):
    """获取记忆统计。"""
    service = SharedMemoryService(db)
    stats = service.get_memory_stats()
    return MemoryStatsResponse(**stats)


@router.post("/cleanup/expired")
async def cleanup_expired(
    db: Session = Depends(get_db),
):
    """清理过期的记忆。"""
    service = SharedMemoryService(db)
    count = service.cleanup_expired_memories()
    return {
        "success": True,
        "deleted_count": count,
    }


@router.get("/categories/list")
async def get_categories(
    db: Session = Depends(get_db),
):
    """获取所有可用的记忆分类。"""
    return {
        "categories": [
            {"value": c.value, "label": c.name}
            for c in MemoryCategory
        ]
    }


# ============== Integration Endpoints ==============

@router.get("/context/for-agent/{agent_id}", response_model=List[MemoryContextResponse])
async def get_agent_context(
    agent_id: str,
    task_type: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """
    获取供Agent使用的记忆上下文。
    
    此端点在发送消息给Agent时调用，提供相关背景知识
    """
    service = SharedMemoryService(db)
    memories = service.get_memories_for_agent_context(
        agent_id=agent_id,
        task_type=task_type,
        limit=limit,
    )
    return memories


@router.post("/agent/{agent_id}/remember")
async def agent_remember(
    agent_id: str,
    data: MemoryCreate,
    db: Session = Depends(get_db),
):
    """
    Agent保存记忆。
    
    简化端点供Agent直接调用
    """
    service = SharedMemoryService(db)
    try:
        memory = service.create_memory(
            agent_id=agent_id,
            title=data.title,
            content=data.content,
            category=data.category,
            scope=data.scope,
            tags=data.tags,
            importance=data.importance,
        )
        return {
            "success": True,
            "memory_id": memory.id,
            "message": "Memory saved successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Helper Functions ==============

def _memory_to_response(memory: SharedMemory, db: Session) -> dict:
    """Convert SharedMemory model to response dict."""
    agent_name = None
    if memory.agent_id:
        from src.models import Agent
        agent = db.query(Agent).filter(Agent.id == memory.agent_id).first()
        if agent:
            agent_name = agent.name
    
    return {
        "id": memory.id,
        "agent_id": memory.agent_id,
        "agent_name": agent_name,
        "title": memory.title,
        "content": memory.content,
        "category": memory.category,
        "scope": memory.scope,
        "tags": memory.tag_list,
        "importance": memory.importance,
        "access_count": memory.access_count or 0,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
        "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
        "is_expired": memory.is_expired,
    }
