"""
Task API routes.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.task_service import TaskService
from src.utils.logging_config import get_logger
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter()
logger = get_logger(__name__)


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreate(BaseModel):
    """Create task request with validation."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(default="", max_length=2000, description="Task description")
    priority: Priority = Field(default=Priority.NORMAL, description="Task priority")
    estimated_cost: float = Field(..., gt=0, le=10000, description="Estimated OC coin cost")
    required_skills: List[str] = Field(default=[], max_length=10, description="Required skills")
    due_date: Optional[datetime] = Field(default=None, description="Task deadline")
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('estimated_cost')
    @classmethod
    def cost_reasonable(cls, v: float) -> float:
        """Ensure cost is reasonable."""
        if v > 5000:
            logger.warning("high_estimated_cost", cost=v, title=cls.title)
        return v


class TaskAssign(BaseModel):
    """Assign task request with validation."""
    agent_id: str = Field(..., min_length=1, max_length=50, description="Agent ID to assign")
    
    @field_validator('agent_id')
    @classmethod
    def agent_id_not_empty(cls, v: str) -> str:
        """Ensure agent_id is not empty."""
        if not v.strip():
            raise ValueError('Agent ID cannot be empty')
        return v.strip()


class TaskUpdate(BaseModel):
    """Update task request."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[Priority] = None
    status: Optional[TaskStatus] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip() if v else v


@router.post("")
@limiter.limit(RATE_LIMITS["create"])
async def create_task(
    request: Request,
    task: TaskCreate,
    db: Session = Depends(get_db),
):
    """Create a new task with validation."""
    logger.info("create_task", title=task.title, priority=task.priority)
    
    try:
        service = TaskService(db)
        new_task = service.create_task(
            title=task.title,
            description=task.description,
            priority=task.priority.value,
            estimated_cost=task.estimated_cost,
        )
        logger.info("task_created", task_id=new_task.id, title=task.title)
        return new_task
    except Exception as e:
        logger.error("create_task_failed", error=str(e), title=task.title)
        raise


@router.get("")
@limiter.limit(RATE_LIMITS["default"])
async def list_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List tasks with optional filters."""
    service = TaskService(db)
    tasks = service.list_tasks(
        status=status.value if status else None,
        agent_id=agent_id
    )
    
    # Format response with assigned_to name
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "estimated_cost": task.estimated_cost,
            "actual_cost": task.actual_cost,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "assigned_to": None,
        }
        
        # Get agent name if assigned
        if task.agent_id:
            from src.models import Agent
            agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
            if agent:
                task_dict["assigned_to"] = agent.name
        
        result.append(task_dict)
    
    return result


@router.post("/{task_id}/assign")
@limiter.limit(RATE_LIMITS["create"])
async def assign_task(
    request: Request,
    task_id: str,
    assign: TaskAssign,
    db: Session = Depends(get_db),
):
    """Assign task to agent with validation."""
    logger.info("assign_task", task_id=task_id, agent_id=assign.agent_id)
    
    service = TaskService(db)
    try:
        task = service.assign_task(task_id, assign.agent_id)
        logger.info("task_assigned", task_id=task_id, agent_id=assign.agent_id)
        return task
    except ValueError as e:
        logger.warning("assign_task_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}")
@limiter.limit(RATE_LIMITS["default"])
async def get_task(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get task details."""
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        logger.warning("task_not_found", task_id=task_id)
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}")
@limiter.limit(RATE_LIMITS["create"])
async def update_task(
    request: Request,
    task_id: str,
    update: TaskUpdate,
    db: Session = Depends(get_db),
):
    """Update task details."""
    logger.info("update_task", task_id=task_id)
    
    service = TaskService(db)
    try:
        task = service.update_task(
            task_id=task_id,
            title=update.title,
            description=update.description,
            priority=update.priority.value if update.priority else None,
            status=update.status.value if update.status else None,
        )
        logger.info("task_updated", task_id=task_id)
        return task
    except ValueError as e:
        logger.warning("update_task_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
