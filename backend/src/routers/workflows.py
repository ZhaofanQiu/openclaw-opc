"""
Workflow Engine Router for v0.5.0

统一工作流引擎API路由
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.workflow_engine_service import WorkflowEngineService
from src.services.workflow_execution_service import WorkflowExecutionService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# ============== Request/Response Models ==============

class WorkflowCreate(BaseModel):
    """创建工作流请求"""
    title: str = Field(..., min_length=1, max_length=200, description="任务主题")
    description: str = Field(..., min_length=1, description="任务描述")
    total_budget: float = Field(..., gt=0, description="总预算（OC币）")
    template_id: Optional[str] = Field(default=None, description="可选：使用模板")


class WorkflowPlanResult(BaseModel):
    """规划结果"""
    analysis: str
    selected_steps: List[str]
    step_plans: Dict
    handbook: str
    total_estimated_hours: float


class StepComplete(BaseModel):
    """完成步骤请求"""
    action: str = Field(..., description="PASS/REWORK")
    comment: str = Field(default="", description="评语")
    artifacts: List[str] = Field(default=[], description="产出物链接")
    actual_hours: float = Field(default=0, description="实际工时")
    budget_used: float = Field(default=0, description="实际使用预算")
    review_scores: Optional[Dict[str, int]] = Field(default=None, description="评审评分")


class ReworkWarningHandle(BaseModel):
    """处理返工预警"""
    action: str = Field(..., description="FORCE_PASS/RESTART/ESCALATE")
    reason: str = Field(default="", description="处理原因")


# ============== API Endpoints ==============

@router.post("")
async def create_workflow(
    data: WorkflowCreate,
    created_by: str,  # Partner ID
    db: Session = Depends(get_db),
):
    """
    创建工作流
    
    用户只需提供：主题、描述、总预算
    系统会自动进入"规划中"状态，等待Partner规划
    """
    service = WorkflowEngineService(db)
    try:
        workflow = service.create_workflow(
            title=data.title,
            description=data.description,
            total_budget=data.total_budget,
            created_by=created_by,
            template_id=data.template_id,
        )
        
        # 自动规划
        plan_result = service.auto_plan_workflow(workflow.id)
        
        return {
            "success": True,
            "workflow": {
                "id": workflow.id,
                "title": workflow.title,
                "status": workflow.status,
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
    from src.models import WorkflowInstance
    
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
    """
    完成当前步骤
    
    支持动作：
    - PASS: 通过，进入下一步
    - REWORK: 返工，回到最近的EXECUTE步骤
    """
    service = WorkflowExecutionService(db)
    
    # 获取当前步骤
    from src.models import WorkflowInstance, WorkflowStep
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    current_step = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id,
        WorkflowStep.sequence == workflow.current_step_index
    ).first()
    
    if not current_step:
        raise HTTPException(status_code=400, detail="No current step")
    
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


@router.post("/{workflow_id}/rework-warning/handle")
async def handle_rework_warning(
    workflow_id: str,
    data: ReworkWarningHandle,
    actor_id: str,
    db: Session = Depends(get_db),
):
    """
    处理返工超限预警
    
    选项：
    - FORCE_PASS: 强行通过当前环节
    - RESTART: 编辑任务后重新启动
    - ESCALATE: 升级给Partner处理
    """
    service = WorkflowExecutionService(db)
    try:
        outcome = service.handle_rework_warning(
            workflow_id=workflow_id,
            action=data.action,
            actor_id=actor_id,
            reason=data.reason,
        )
        return outcome
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/steps")
async def get_workflow_steps(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流所有步骤"""
    from src.models import WorkflowStep
    
    steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id
    ).order_by(WorkflowStep.sequence).all()
    
    return [_format_step_response(s) for s in steps]


@router.get("/{workflow_id}/history")
async def get_workflow_history(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流历史记录"""
    from src.models.workflow_engine import WorkflowHistory
    
    history = db.query(WorkflowHistory).filter(
        WorkflowHistory.workflow_id == workflow_id
    ).order_by(WorkflowHistory.created_at.desc()).all()
    
    return [
        {
            "id": h.id,
            "action": h.action,
            "step_id": h.step_id,
            "actor_id": h.actor_id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "details": h.details,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in history
    ]


@router.get("/agent/{agent_id}/pending")
async def get_agent_pending_workflows(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取员工的待办工作流"""
    from src.models import WorkflowStep, WorkflowInstance
    
    steps = db.query(WorkflowStep).join(WorkflowInstance).filter(
        WorkflowStep.assignee_id == agent_id,
        WorkflowStep.status.in_(["assigned", "in_progress", "rework"]),
        WorkflowInstance.status.in_(["in_progress", "rework", "warning"])
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
    from src.models import WorkflowInstance, WorkflowStep
    
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
        "total_budget": workflow.total_budget,
        "used_budget": workflow.used_budget,
        "remaining_budget": workflow.remaining_budget,
        "current_step_index": workflow.current_step_index,
        "total_rework_count": workflow.total_rework_count,
        "plan_result": workflow.plan_result,
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
        "allocated_budget": step.allocated_budget,
        "used_budget": step.used_budget,
        "estimated_hours": step.estimated_hours,
        "actual_hours": step.actual_hours,
        "rework_count": step.rework_count,
        "rework_limit": step.rework_limit,
        "result": step.result,
        "review_scores": step.review_scores,
        "assigned_at": step.assigned_at.isoformat() if step.assigned_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
    }
