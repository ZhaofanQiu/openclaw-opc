"""
Budget Fuse API routes.

Endpoints for handling budget fuse events and post-fuse actions.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.fuse_service import FuseService, FuseAction, FuseEventStatus
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/fuse", tags=["Budget Fuse"])


# Schemas

class FuseEventResponse(BaseModel):
    """Fuse event response."""
    id: str
    agent_id: str
    agent_name: str
    task_id: Optional[str]
    fuse_type: str
    threshold_percentage: float
    budget_used: float
    budget_total: float
    status: str
    created_at: str
    resolved_action: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_note: Optional[str] = None


class AddBudgetRequest(BaseModel):
    """Request to add budget."""
    additional_budget: float = Field(..., gt=0, description="Amount to add to budget")
    reason: str = Field(..., min_length=1, description="Reason for adding budget")


class ReassignRequest(BaseModel):
    """Request to reassign task."""
    new_agent_id: str = Field(..., description="New agent ID to assign")
    reason: str = Field(..., min_length=1, description="Reason for reassignment")


class SubTaskDef(BaseModel):
    """Sub-task definition."""
    description: str
    estimated_cost: float


class SplitTaskRequest(BaseModel):
    """Request to split task."""
    sub_tasks: List[SubTaskDef] = Field(..., min_items=2, description="Sub-task definitions")
    reason: str = Field(..., min_length=1, description="Reason for splitting")


class ResolveRequest(BaseModel):
    """Generic resolve request."""
    action: str = Field(..., description="Action taken: add_budget, split_task, reassign, pause")
    note: Optional[str] = Field(None, description="Optional resolution note")


# Routes

@router.get("/events", response_model=List[FuseEventResponse])
async def get_fuse_events(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get fuse events.
    
    Filter by agent_id and/or status.
    """
    service = FuseService(db)
    
    if status in ["pending", "triggered"]:
        events = service.get_pending_events(agent_id=agent_id)
    else:
        # Get all events for agent
        from src.models import BudgetFuseEvent
        query = db.query(BudgetFuseEvent)
        if agent_id:
            query = query.filter(BudgetFuseEvent.agent_id == agent_id)
        events = query.order_by(BudgetFuseEvent.created_at.desc()).all()
    
    # Enrich with agent names
    from src.models import Agent
    result = []
    for event in events:
        agent = db.query(Agent).filter(Agent.id == event.agent_id).first()
        result.append(FuseEventResponse(
            id=event.id,
            agent_id=event.agent_id,
            agent_name=agent.name if agent else "Unknown",
            task_id=event.task_id,
            fuse_type=event.fuse_type,
            threshold_percentage=event.threshold_percentage,
            budget_used=event.budget_used,
            budget_total=event.budget_total,
            status=event.status,
            created_at=event.created_at.isoformat() if event.created_at else None,
            resolved_action=event.resolved_action,
            resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
            resolution_note=event.resolution_note,
        ))
    
    return result


@router.get("/events/pending")
async def get_pending_fuse_events(
    db: Session = Depends(get_db),
):
    """
    Get all pending fuse events that need user action.
    
    Returns events with status 'triggered' or 'pending'.
    """
    service = FuseService(db)
    events = service.get_pending_events()
    
    from src.models import Agent
    result = []
    for event in events:
        agent = db.query(Agent).filter(Agent.id == event.agent_id).first()
        result.append({
            "id": event.id,
            "agent_id": event.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "agent_emoji": agent.emoji if agent else "🤖",
            "task_id": event.task_id,
            "fuse_type": event.fuse_type,
            "threshold_percentage": event.threshold_percentage,
            "budget_used": event.budget_used,
            "budget_total": event.budget_total,
            "remaining_budget": event.budget_total - event.budget_used,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "actions_available": [
                {"action": "add_budget", "label": "💰 追加预算", "description": "为该员工增加月度预算"},
                {"action": "split_task", "label": "✂️ 拆分任务", "description": "将当前任务拆分为多个小任务"},
                {"action": "reassign", "label": "🔄 换人重做", "description": "将任务分配给其他员工"},
                {"action": "pause", "label": "⏸️ 暂停", "description": "保持暂停状态，稍后处理"},
            ],
        })
    
    return result


@router.get("/events/{event_id}")
async def get_fuse_event(
    event_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific fuse event."""
    service = FuseService(db)
    event = service.get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Fuse event not found")
    
    from src.models import Agent
    agent = db.query(Agent).filter(Agent.id == event.agent_id).first()
    
    return {
        "id": event.id,
        "agent_id": event.agent_id,
        "agent_name": agent.name if agent else "Unknown",
        "agent_emoji": agent.emoji if agent else "🤖",
        "task_id": event.task_id,
        "fuse_type": event.fuse_type,
        "threshold_percentage": event.threshold_percentage,
        "budget_used": event.budget_used,
        "budget_total": event.budget_total,
        "remaining_budget": event.budget_total - event.budget_used,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "resolved_action": event.resolved_action,
        "resolved_by": event.resolved_by,
        "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
        "resolution_note": event.resolution_note,
        "actions_available": [
            {"action": "add_budget", "label": "💰 追加预算", "description": "为该员工增加月度预算"},
            {"action": "split_task", "label": "✂️ 拆分任务", "description": "将当前任务拆分为多个小任务"},
            {"action": "reassign", "label": "🔄 换人重做", "description": "将任务分配给其他员工"},
            {"action": "pause", "label": "⏸️ 暂停", "description": "保持暂停状态，稍后处理"},
        ] if event.status in [FuseEventStatus.TRIGGERED.value, FuseEventStatus.PENDING.value] else [],
    }


@router.post("/events/{event_id}/resolve/add-budget")
@limiter.limit(RATE_LIMITS["create"])
async def resolve_add_budget(
    request: Request,
    event_id: str,
    data: AddBudgetRequest,
    db: Session = Depends(get_db),
):
    """
    Resolve fuse event by adding budget.
    
    Increases the agent's monthly budget by the specified amount.
    """
    service = FuseService(db)
    
    # TODO: Get actual employee ID from auth
    resolved_by = "system"
    
    result = service.add_budget_resolution(
        event_id=event_id,
        additional_budget=data.additional_budget,
        reason=data.reason,
        resolved_by=resolved_by,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Fuse event not found")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "message": f"已为 {result['agent_name']} 追加 {data.additional_budget} OC币预算",
        "result": result,
    }


@router.post("/events/{event_id}/resolve/reassign")
@limiter.limit(RATE_LIMITS["create"])
async def resolve_reassign(
    request: Request,
    event_id: str,
    data: ReassignRequest,
    db: Session = Depends(get_db),
):
    """
    Resolve fuse event by reassigning task.
    
    Moves the task to another agent.
    """
    service = FuseService(db)
    
    resolved_by = "system"
    
    result = service.reassign_resolution(
        event_id=event_id,
        new_agent_id=data.new_agent_id,
        reason=data.reason,
        resolved_by=resolved_by,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Fuse event not found")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "message": f"任务已重新分配给 {result['new_agent']}",
        "result": result,
    }


@router.post("/events/{event_id}/resolve/split-task")
@limiter.limit(RATE_LIMITS["create"])
async def resolve_split_task(
    request: Request,
    event_id: str,
    data: SplitTaskRequest,
    db: Session = Depends(get_db),
):
    """
    Resolve fuse event by splitting task.
    
    Creates sub-tasks from the original task.
    """
    service = FuseService(db)
    
    resolved_by = "system"
    
    # Convert Pydantic models to dicts
    sub_tasks = [{"description": st.description, "estimated_cost": st.estimated_cost} for st in data.sub_tasks]
    
    result = service.split_task_resolution(
        event_id=event_id,
        sub_tasks=sub_tasks,
        reason=data.reason,
        resolved_by=resolved_by,
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Fuse event not found")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "message": f"任务已拆分为 {result['sub_task_count']} 个子任务",
        "result": result,
    }


@router.post("/events/{event_id}/resolve/pause")
async def resolve_pause(
    event_id: str,
    note: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Resolve fuse event by pausing (no immediate action).
    
    Marks the event as acknowledged but keeps the task paused.
    """
    service = FuseService(db)
    
    resolved_by = "system"
    
    event = service.resolve_event(
        event_id=event_id,
        action=FuseAction.PAUSE.value,
        resolved_by=resolved_by,
        resolution_note=note or "用户选择暂停，稍后处理",
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Fuse event not found")
    
    return {
        "success": True,
        "message": "已标记为暂停状态，您可以稍后处理",
        "event_id": event.id,
        "status": event.status,
    }


@router.get("/stats")
async def get_fuse_stats(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """
    Get fuse event statistics.
    
    Shows summary of fuse events and resolution patterns.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    service = FuseService(db)
    return service.get_fuse_stats(days=days)
