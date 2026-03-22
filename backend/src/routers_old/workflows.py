"""
Workflow Engine Router v0.5.2 - 纯串行执行
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.workflow_engine_service import WorkflowEngineService
from services.workflow_execution_service import WorkflowExecutionService
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ============== Request/Response Models ==============

class WorkflowCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    total_budget: float = Field(..., gt=0)
    template_id: Optional[str] = Field(default=None)
    rework_budget_ratio: float = Field(default=0.2, ge=0.1, le=0.5)


class StepComplete(BaseModel):
    action: str = Field(..., description="PASS/REWORK")
    comment: str = Field(default="")
    artifacts: List[str] = Field(default=[])
    actual_hours: float = Field(default=0)
    budget_used: float = Field(default=0)
    review_scores: Optional[Dict[str, int]] = Field(default=None)


class FuseHandle(BaseModel):
    action: str = Field(..., description="ADD_BUDGET/FORCE_PASS/RESTART/CANCEL")
    reason: str = Field(default="")
    params: Dict = Field(default={})


# ============== API Endpoints ==============

@router.post("")
async def create_workflow(
    data: WorkflowCreate,
    created_by: str,
    db: Session = Depends(get_db),
):
    """创建工作流（串行执行）"""
    service = WorkflowEngineService(db)
    try:
        workflow = service.create_workflow(
            title=data.title,
            description=data.description,
            total_budget=data.total_budget,
            created_by=created_by,
            template_id=data.template_id,
            rework_budget_ratio=data.rework_budget_ratio,
        )
        
        plan_result = service.auto_plan_workflow(workflow.id)
        
        return {
            "success": True,
            "workflow": {
                "id": workflow.id,
                "title": workflow.title,
                "status": workflow.status,
                "budget": {
                    "total": workflow.total_budget,
                    "base": workflow.base_budget,
                    "rework_reserve": workflow.rework_budget,
                }
            },
            "plan": plan_result,
            "next_action": "启动工作流",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/start")
async def start_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """启动工作流"""
    service = WorkflowExecutionService(db)
    try:
        workflow = service.start_workflow(workflow_id)
        return {
            "success": True,
            "workflow_id": workflow.id,
            "status": workflow.status,
            "current_step": _get_current_step_info(db, workflow_id),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流详情"""
    from models import WorkflowInstance
    
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return _format_workflow_response(workflow)


@router.post("/{workflow_id}/steps/current/complete")
async def complete_current_step(
    workflow_id: str,
    data: StepComplete,
    actor_id: str,
    db: Session = Depends(get_db),
):
    """完成当前步骤"""
    service = WorkflowExecutionService(db)
    
    from models import WorkflowInstance, WorkflowStep
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.current_step_index < 0:
        raise HTTPException(status_code=400, detail="No current step")
    
    current_step = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id,
        WorkflowStep.sequence == workflow.current_step_index
    ).first()
    
    if not current_step:
        raise HTTPException(status_code=400, detail="Current step not found")
    
    result = {
        "action": data.action,
        "comment": data.comment,
        "artifacts": data.artifacts,
        "actual_hours": data.actual_hours,
        "budget_used": data.budget_used,
        "review_scores": data.review_scores,
    }
    
    try:
        outcome = service.complete_step(
            step_id=current_step.id,
            action=data.action,
            result=result,
            actor_id=actor_id,
        )
        return outcome
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/fuse/handle")
async def handle_fuse(
    workflow_id: str,
    data: FuseHandle,
    actor_id: str,
    db: Session = Depends(get_db),
):
    """处理熔断"""
    service = WorkflowExecutionService(db)
    try:
        outcome = service.handle_fuse(
            workflow_id=workflow_id,
            action=data.action,
            actor_id=actor_id,
            params=data.params,
        )
        return outcome
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/steps")
async def get_workflow_steps(workflow_id: str, db: Session = Depends(get_db)):
    """获取工作流所有步骤"""
    from models import WorkflowStep
    
    steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id
    ).order_by(WorkflowStep.sequence).all()
    
    return [_format_step_response(s) for s in steps]


@router.get("/{workflow_id}/history")
async def get_workflow_history(workflow_id: str, db: Session = Depends(get_db)):
    """获取工作流历史"""
    from models.workflow_engine import WorkflowHistory
    
    history = db.query(WorkflowHistory).filter(
        WorkflowHistory.workflow_id == workflow_id
    ).order_by(WorkflowHistory.created_at.desc()).all()
    
    return [
        {
            "id": h.id,
            "action": h.action,
            "step_id": h.step_id,
            "actor_id": h.actor_id,
            "details": h.details,
            "budget_impact": h.budget_impact,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in history
    ]


@router.get("/{workflow_id}/budget")
async def get_workflow_budget(workflow_id: str, db: Session = Depends(get_db)):
    """获取预算详情"""
    from models import WorkflowInstance
    
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "total": workflow.total_budget,
        "base": {
            "allocated": workflow.base_budget,
            "used": workflow.used_base_budget,
            "remaining": workflow.base_budget - workflow.used_base_budget,
        },
        "rework": {
            "allocated": workflow.rework_budget,
            "used": workflow.used_rework_budget,
            "remaining": workflow.rework_budget - workflow.used_rework_budget,
        },
        "total_remaining": workflow.remaining_budget,
    }


@router.get("/agent/{agent_id}/pending")
async def get_agent_pending_workflows(agent_id: str, db: Session = Depends(get_db)):
    """获取员工的待办工作流"""
    from models import WorkflowStep, WorkflowInstance
    
    steps = db.query(WorkflowStep).join(WorkflowInstance).filter(
        WorkflowStep.assignee_id == agent_id,
        WorkflowStep.status.in_(["assigned", "in_progress", "rework"]),
        WorkflowInstance.status.in_(["in_progress", "rework"])
    ).all()
    
    return [
        {
            "step": _format_step_response(s),
            "workflow": {
                "id": s.workflow.id,
                "title": s.workflow.title,
                "status": s.workflow.status,
            }
        }
        for s in steps
    ]


# ============== Helper Functions ==============

def _get_current_step_info(db: Session, workflow_id: str) -> Optional[Dict]:
    """获取当前步骤信息"""
    from models import WorkflowInstance, WorkflowStep
    
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow or workflow.current_step_index < 0:
        return None
    
    step = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id,
        WorkflowStep.sequence == workflow.current_step_index
    ).first()
    
    return _format_step_response(step) if step else None


def _format_workflow_response(workflow) -> Dict:
    """格式化工作流响应"""
    return {
        "id": workflow.id,
        "title": workflow.title,
        "description": workflow.description,
        "status": workflow.status,
        "budget": {
            "total": workflow.total_budget,
            "base": workflow.base_budget,
            "rework_reserve": workflow.rework_budget,
            "used": workflow.used_base_budget + workflow.used_rework_budget,
            "remaining": workflow.remaining_budget,
        },
        "rework_stats": {
            "total_count": workflow.total_rework_count,
            "total_cost": workflow.total_rework_cost,
        },
        "current_step_index": workflow.current_step_index,
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
    }


def _format_step_response(step) -> Dict:
    """格式化步骤响应"""
    return {
        "id": step.id,
        "step_id": step.step_id,
        "name": step.name,
        "type": step.step_type,
        "sequence": step.sequence,
        "status": step.status,
        "assignee": {
            "id": step.assignee.id if step.assignee else None,
            "name": step.assignee.name if step.assignee else None,
        },
        "budget": {
            "base": step.base_budget,
            "rework_reserve": step.rework_reserve,
            "used": step.used_budget,
            "rework_cost": step.rework_cost,
        },
        "hours": {
            "estimated": step.estimated_hours,
            "actual": step.actual_hours,
        },
        "rework": {
            "count": step.rework_count,
            "limit": step.rework_limit,
            "is_rework": step.is_rework == "true",
        },
        "result": step.result,
        "review_scores": step.review_scores,
    }
