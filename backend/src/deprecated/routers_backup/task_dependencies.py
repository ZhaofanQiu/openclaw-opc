"""
Task Dependency Router for v0.4.0

API endpoints for task dependency management
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import TaskDependency, TaskDependencyStatus
from src.services.task_dependency_service import TaskDependencyService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/dependencies", tags=["task-dependencies"])


# ============== Request/Response Models ==============

class DependencyCreate(BaseModel):
    """Create dependency request."""
    upstream_task_id: str = Field(..., description="上游任务ID（完成后触发）")
    downstream_task_template: dict = Field(..., description="下游任务模板配置")
    trigger_condition: str = Field(default="completed", description="触发条件: completed/failed/any")
    delay_minutes: int = Field(default=0, ge=0, description="延迟触发分钟数")


class DependencyResponse(BaseModel):
    """Dependency response model."""
    id: str
    upstream_task_id: str
    downstream_task_id: Optional[str]
    downstream_task_template: dict
    trigger_condition: str
    delay_minutes: int
    status: str
    created_at: str
    triggered_at: Optional[str]
    
    class Config:
        from_attributes = True


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""
    root_task_id: str
    total_tasks: int
    completed: int
    failed: int
    in_progress: int
    pending: int
    progress_percentage: float
    is_complete: bool
    has_failures: bool
    chain: List[dict]


# ============== API Endpoints ==============

@router.post("", response_model=DependencyResponse)
async def create_dependency(
    data: DependencyCreate,
    db: Session = Depends(get_db),
):
    """创建任务依赖关系。"""
    service = TaskDependencyService(db)
    try:
        dependency = service.create_dependency(
            upstream_task_id=data.upstream_task_id,
            downstream_task_template=data.downstream_task_template,
            trigger_condition=data.trigger_condition,
            delay_minutes=data.delay_minutes,
        )
        return _dependency_to_response(dependency)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[DependencyResponse])
async def list_dependencies(
    task_id: Optional[str] = None,
    upstream_only: bool = False,
    downstream_only: bool = False,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """列取依赖关系。"""
    service = TaskDependencyService(db)
    dependencies = service.get_dependencies(
        task_id=task_id,
        upstream_only=upstream_only,
        downstream_only=downstream_only,
        status=status,
    )
    return [_dependency_to_response(d) for d in dependencies]


@router.get("/{dependency_id}", response_model=DependencyResponse)
async def get_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
):
    """获取单个依赖关系。"""
    service = TaskDependencyService(db)
    dependency = service.get_dependency(dependency_id)
    if not dependency:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return _dependency_to_response(dependency)


@router.post("/{dependency_id}/cancel")
async def cancel_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
):
    """取消活跃的依赖关系。"""
    service = TaskDependencyService(db)
    try:
        dependency = service.cancel_dependency(dependency_id)
        return {
            "success": True,
            "dependency": _dependency_to_response(dependency),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dependency_id}")
async def delete_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
):
    """删除依赖关系。"""
    service = TaskDependencyService(db)
    try:
        service.delete_dependency(dependency_id)
        return {"success": True, "message": "Dependency deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/chain/{task_id}")
async def get_dependency_chain(
    task_id: str,
    direction: str = "downstream",
    db: Session = Depends(get_db),
):
    """
    获取任务依赖链。
    
    - direction=downstream: 此任务完成后会触发哪些任务
    - direction=upstream: 哪些任务完成后会触发此任务
    """
    if direction not in ["downstream", "upstream"]:
        raise HTTPException(status_code=400, detail="direction must be 'downstream' or 'upstream'")
    
    service = TaskDependencyService(db)
    chain = service.get_dependency_chain(task_id, direction=direction)
    return {
        "task_id": task_id,
        "direction": direction,
        "chain_length": len(chain),
        "chain": chain,
    }


@router.get("/workflow/{root_task_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    root_task_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流状态（从根任务开始的完整依赖链）。"""
    service = TaskDependencyService(db)
    status = service.get_workflow_status(root_task_id)
    return WorkflowStatusResponse(**status)


# ============== Integration Endpoint ==============

@router.post("/trigger/{task_id}")
async def trigger_dependencies(
    task_id: str,
    status: str,
    db: Session = Depends(get_db),
):
    """
    手动触发任务的依赖（通常由任务状态变更自动调用）。
    
    此端点用于：
    - 手动触发依赖
    - 测试依赖链
    - 重试失败的触发
    """
    service = TaskDependencyService(db)
    triggered = service.check_and_trigger_dependencies(task_id, status)
    
    return {
        "success": True,
        "upstream_task_id": task_id,
        "triggered_count": len(triggered),
        "triggered_tasks": [{"id": t.id, "title": t.title} for t in triggered],
    }


# ============== Helper Functions ==============

def _dependency_to_response(dependency: TaskDependency) -> dict:
    """Convert TaskDependency model to response dict."""
    import json
    
    try:
        template = json.loads(dependency.downstream_task_template or "{}")
    except json.JSONDecodeError:
        template = {}
    
    return {
        "id": dependency.id,
        "upstream_task_id": dependency.upstream_task_id,
        "downstream_task_id": dependency.downstream_task_id,
        "downstream_task_template": template,
        "trigger_condition": dependency.trigger_condition,
        "delay_minutes": dependency.delay_minutes,
        "status": dependency.status,
        "created_at": dependency.created_at.isoformat() if dependency.created_at else None,
        "triggered_at": dependency.triggered_at.isoformat() if dependency.triggered_at else None,
    }
