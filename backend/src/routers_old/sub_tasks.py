"""
Sub-task Router for v0.4.0

API endpoints for sub-task management
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import SubTask, SubTaskStatus, Task
from services.sub_task_service import SubTaskService
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sub-tasks", tags=["sub-tasks"])


# ============== Request/Response Models ==============

class SubTaskCreate(BaseModel):
    """Create sub-task request."""
    parent_task_id: str = Field(..., description="Parent task ID")
    title: str = Field(..., min_length=1, max_length=100, description="Sub-task title")
    description: str = Field(default="", description="Sub-task description")
    estimated_cost: float = Field(default=0.0, ge=0, description="Estimated budget cost")
    sequence_order: int = Field(default=0, ge=0, description="Execution order")
    depends_on: List[str] = Field(default=[], description="List of sub-task IDs this depends on")
    is_critical: bool = Field(default=False, description="Whether this is on critical path")


class SubTaskSplit(BaseModel):
    """Split task into sub-tasks request."""
    sub_tasks: List[dict] = Field(..., description="List of sub-task configurations")


class SubTaskAssign(BaseModel):
    """Assign sub-task request."""
    agent_id: str = Field(..., description="Agent ID to assign to")


class SubTaskStatusUpdate(BaseModel):
    """Update sub-task status request."""
    status: str = Field(..., description="New status")
    result_summary: str = Field(default="", description="Task result description")
    actual_cost: Optional[float] = Field(default=None, description="Actual cost")


class SubTaskResponse(BaseModel):
    """Sub-task response model."""
    id: str
    parent_task_id: str
    agent_id: Optional[str]
    title: str
    description: str
    sequence_order: int
    status: str
    estimated_cost: float
    actual_cost: float
    depends_on: List[str]
    is_critical: bool
    created_at: str
    assigned_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    result_summary: str
    
    class Config:
        from_attributes = True


class SubTaskStatsResponse(BaseModel):
    """Sub-task statistics response."""
    total: int
    pending: int
    assigned: int
    in_progress: int
    completed: int
    failed: int
    blocked: int
    progress_percentage: float


# ============== API Endpoints ==============

@router.post("", response_model=SubTaskResponse)
async def create_sub_task(
    data: SubTaskCreate,
    db: Session = Depends(get_db),
):
    """Create a new sub-task."""
    service = SubTaskService(db)
    try:
        sub_task = service.create_sub_task(
            parent_task_id=data.parent_task_id,
            title=data.title,
            description=data.description,
            estimated_cost=data.estimated_cost,
            sequence_order=data.sequence_order,
            depends_on=data.depends_on,
            is_critical=data.is_critical,
        )
        return _sub_task_to_response(sub_task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/split/{task_id}")
async def split_task(
    task_id: str,
    data: SubTaskSplit,
    db: Session = Depends(get_db),
):
    """Split a task into multiple sub-tasks."""
    service = SubTaskService(db)
    try:
        sub_tasks = service.split_task(task_id, data.sub_tasks)
        return {
            "success": True,
            "task_id": task_id,
            "sub_task_count": len(sub_tasks),
            "sub_tasks": [_sub_task_to_response(st) for st in sub_tasks],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[SubTaskResponse])
async def list_sub_tasks(
    parent_task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List sub-tasks with optional filtering."""
    service = SubTaskService(db)
    sub_tasks = service.get_sub_tasks(
        parent_task_id=parent_task_id,
        agent_id=agent_id,
        status=status,
    )
    return [_sub_task_to_response(st) for st in sub_tasks]


@router.get("/{sub_task_id}", response_model=SubTaskResponse)
async def get_sub_task(
    sub_task_id: str,
    db: Session = Depends(get_db),
):
    """Get a single sub-task by ID."""
    service = SubTaskService(db)
    sub_task = service.get_sub_task(sub_task_id)
    if not sub_task:
        raise HTTPException(status_code=404, detail="Sub-task not found")
    return _sub_task_to_response(sub_task)


@router.post("/{sub_task_id}/assign", response_model=SubTaskResponse)
async def assign_sub_task(
    sub_task_id: str,
    data: SubTaskAssign,
    db: Session = Depends(get_db),
):
    """Assign a sub-task to an agent."""
    service = SubTaskService(db)
    try:
        sub_task = service.assign_sub_task(sub_task_id, data.agent_id)
        return _sub_task_to_response(sub_task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/status", response_model=SubTaskResponse)
async def update_sub_task_status(
    sub_task_id: str,
    data: SubTaskStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update sub-task status."""
    service = SubTaskService(db)
    try:
        sub_task = service.update_sub_task_status(
            sub_task_id=sub_task_id,
            status=data.status,
            result_summary=data.result_summary,
            actual_cost=data.actual_cost,
        )
        return _sub_task_to_response(sub_task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{sub_task_id}")
async def delete_sub_task(
    sub_task_id: str,
    db: Session = Depends(get_db),
):
    """Delete a sub-task."""
    service = SubTaskService(db)
    try:
        service.delete_sub_task(sub_task_id)
        return {"success": True, "message": "Sub-task deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{parent_task_id}/stats", response_model=SubTaskStatsResponse)
async def get_sub_task_stats(
    parent_task_id: str,
    db: Session = Depends(get_db),
):
    """Get sub-task statistics for a parent task."""
    service = SubTaskService(db)
    stats = service.get_sub_task_stats(parent_task_id)
    return SubTaskStatsResponse(**stats)


@router.get("/{parent_task_id}/next")
async def get_next_executable_sub_task(
    parent_task_id: str,
    db: Session = Depends(get_db),
):
    """Get the next sub-task that can be executed (dependencies met)."""
    service = SubTaskService(db)
    sub_task = service.get_next_executable_sub_task(parent_task_id)
    if not sub_task:
        return {"has_task": False, "message": "No executable sub-task available"}
    return {
        "has_task": True,
        "sub_task": _sub_task_to_response(sub_task),
    }


# ============== Helper Functions ==============

def _sub_task_to_response(sub_task: SubTask) -> dict:
    """Convert SubTask model to response dict."""
    import json
    
    try:
        depends_on = json.loads(sub_task.depends_on or "[]")
    except json.JSONDecodeError:
        depends_on = []
    
    return {
        "id": sub_task.id,
        "parent_task_id": sub_task.parent_task_id,
        "agent_id": sub_task.agent_id,
        "title": sub_task.title,
        "description": sub_task.description,
        "sequence_order": sub_task.sequence_order,
        "status": sub_task.status,
        "estimated_cost": sub_task.estimated_cost,
        "actual_cost": sub_task.actual_cost,
        "depends_on": depends_on,
        "is_critical": sub_task.is_critical == "true",
        "created_at": sub_task.created_at.isoformat() if sub_task.created_at else None,
        "assigned_at": sub_task.assigned_at.isoformat() if sub_task.assigned_at else None,
        "started_at": sub_task.started_at.isoformat() if sub_task.started_at else None,
        "completed_at": sub_task.completed_at.isoformat() if sub_task.completed_at else None,
        "result_summary": sub_task.result_summary,
    }
