"""
Task Dependency Router for v0.4.0

API endpoints for task dependency management
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import TaskDependency, TaskDependencyStatus
from src.services.task_dependency_service import TaskDependencyService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/task-dependencies", tags=["task-dependencies"])


# ============== Request/Response Models ==============

class TaskDependencyCreate(BaseModel):
    """Create task dependency request."""
    upstream_task_id: str = Field(..., description="Task that triggers the dependency")
    downstream_task_id: Optional[str] = Field(None, description="Task to be triggered (optional)")
    downstream_task_template: Optional[Dict] = Field(None, description="Template for creating downstream task")
    trigger_condition: str = Field(default="completed", description="completed/failed/any")
    delay_minutes: int = Field(default=0, ge=0, description="Delay before triggering (minutes)")


class TaskDependencyResponse(BaseModel):
    """Task dependency response."""
    id: str
    upstream_task_id: str
    downstream_task_id: Optional[str]
    downstream_task_template: Dict
    trigger_condition: str
    delay_minutes: int
    status: str
    triggered_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class WorkflowResponse(BaseModel):
    """Workflow chain response."""
    task_id: str
    upstream: List[Dict]
    downstream: List[Dict]


# ============== API Endpoints ==============

@router.post("", response_model=TaskDependencyResponse)
async def create_dependency(
    data: TaskDependencyCreate,
    db: Session = Depends(get_db),
):
    """Create a new task dependency."""
    service = TaskDependencyService(db)
    try:
        dep = service.create_dependency(
            upstream_task_id=data.upstream_task_id,
            downstream_task_id=data.downstream_task_id,
            downstream_task_template=data.downstream_task_template,
            trigger_condition=data.trigger_condition,
            delay_minutes=data.delay_minutes,
        )
        return _dependency_to_response(dep)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_dependencies(
    task_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List task dependencies."""
    service = TaskDependencyService(db)
    
    upstream_deps = service.get_dependencies(task_id, status, as_upstream=True)
    downstream_deps = service.get_dependencies(task_id, status, as_upstream=False)
    
    return {
        "upstream": [_dependency_to_response(d) for d in upstream_deps],
        "downstream": [_dependency_to_response(d) for d in downstream_deps],
    }


@router.get("/{dependency_id}", response_model=TaskDependencyResponse)
async def get_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
):
    """Get a single dependency by ID."""
    service = TaskDependencyService(db)
    dep = service.get_dependency(dependency_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return _dependency_to_response(dep)


@router.post("/{dependency_id}/cancel")
async def cancel_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
):
    """Cancel a dependency."""
    service = TaskDependencyService(db)
    try:
        service.cancel_dependency(dependency_id)
        return {"success": True, "message": "Dependency cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{dependency_id}")
async def delete_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
):
    """Delete a dependency."""
    service = TaskDependencyService(db)
    try:
        service.delete_dependency(dependency_id)
        return {"success": True, "message": "Dependency deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/chain/{task_id}", response_model=WorkflowResponse)
async def get_dependency_chain(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get the dependency chain for a task."""
    service = TaskDependencyService(db)
    chain = service.get_dependency_chain(task_id)
    return WorkflowResponse(**chain)


@router.get("/workflow/{start_task_id}")
async def build_workflow(
    start_task_id: str,
    db: Session = Depends(get_db),
):
    """Build a workflow starting from a task."""
    service = TaskDependencyService(db)
    workflow = service.build_workflow(start_task_id)
    return {
        "start_task_id": start_task_id,
        "workflow": workflow,
        "task_count": len(workflow),
    }


# ============== Helper Functions ==============

def _dependency_to_response(dep: TaskDependency) -> dict:
    """Convert TaskDependency to response dict."""
    import json
    
    try:
        template = json.loads(dep.downstream_task_template or "{}")
    except json.JSONDecodeError:
        template = {}
    
    return {
        "id": dep.id,
        "upstream_task_id": dep.upstream_task_id,
        "downstream_task_id": dep.downstream_task_id,
        "downstream_task_template": template,
        "trigger_condition": dep.trigger_condition,
        "delay_minutes": dep.delay_minutes,
        "status": dep.status,
        "triggered_at": dep.triggered_at.isoformat() if dep.triggered_at else None,
        "created_at": dep.created_at.isoformat() if dep.created_at else None,
    }
