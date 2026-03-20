"""
Task API routes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.task_service import TaskService

router = APIRouter()


class TaskCreate(BaseModel):
    """Create task request."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    priority: str = "normal"
    estimated_cost: float = Field(..., gt=0)


class TaskAssign(BaseModel):
    """Assign task request."""
    agent_id: str


@router.post("")
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
):
    """Create a new task."""
    service = TaskService(db)
    new_task = service.create_task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        estimated_cost=task.estimated_cost,
    )
    return new_task


@router.get("")
async def list_tasks(
    status: str = None,
    agent_id: str = None,
    db: Session = Depends(get_db),
):
    """List tasks with optional filters."""
    service = TaskService(db)
    return service.list_tasks(status=status, agent_id=agent_id)


@router.post("/{task_id}/assign")
async def assign_task(
    task_id: str,
    assign: TaskAssign,
    db: Session = Depends(get_db),
):
    """Assign task to agent."""
    service = TaskService(db)
    try:
        task = service.assign_task(task_id, assign.agent_id)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get task details."""
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
