"""
Workflow Engine Router v0.5.1 - 并行执行与返工预算熔断
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
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    total_budget: float = Field(..., gt=0)
    template_id: Optional[str] = Field(default=None)
    rework_budget_ratio: float = Field(default=0.2, ge=0.1, le=0.5)  # 返工预算比例


class StepComplete(BaseModel):
    """完成步骤请求"""
    action: str = Field(..., description="PASS/REWORK")
    comment: str = Field(default="")
    artifacts: List[str] = Field(default=[])
    actual_hours: float = Field(default=0)
    budget_used: float = Field(default=0)
    review_scores: Optional[Dict[str, int]] = Field(default=None)


class FuseHandle(BaseModel):
    """处理熔断请求"""
    action: str = Field(..., description="ADD_BUDGET/FORCE_PASS/RESTART/CANCEL")
    reason: str = Field(default="")
    params: Dict = Field(default={})  # ADD_BUDGET时: {"amount": 500}


# ============== API Endpoints ==============

@router.post("")
async def create_workflow(
    data: WorkflowCreate,
    created_by: str,
    db: Session = Depends(get_db),
):
    """
    创建工作流
    
    总预算自动分配：
    - 基础预算 = 总预算 × (1 - rework_budget_ratio)
    - 返工预算池 = 总预算 × rework_budget_ratio (默认20%)
    """
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
        
        # 自动规划
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
            "is_complex": plan_result.get("is_complex", False),
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
            "current_steps": _get_current_steps_info(db, workflow_id),
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
    
    预算扣除规则：
    - 首次执行：从基础预算扣除
    - 返工：从返工储备扣除，储备耗尽触发熔断
    """
    service = WorkflowExecutionService(db)
    
    from src.models import WorkflowInstance
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if not workflow.current_step_ids:
        raise HTTPException(status_code=400, detail="No current step")
    
    # 支持同时完成多个并行步骤
    results = []
    for step_id in workflow.current_step_ids:
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
                step_id=step_id,
                action=data.action,
                result=result,
                actor_id=actor_id,
            )
            results.append(outcome)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    # 返回汇总结果
    fused_results = [r for r in results if r.get("fused")]
    if fused_results:
        return fused_results[0]  # 返回第一个熔断结果
    
    return results[0] if results else {"success": True}


@router.post("/{workflow_id}/fuse/handle")
async def handle_fuse(
    workflow_id: str,
    data: FuseHandle,
    actor_id: str,
    db: Session = Depends(get_db),
):
    """
    处理熔断
    
    熔断类型：
    - BUDGET_FUSED: 返工预算耗尽
    - REWORK_FUSED: 返工次数超限
    
    处理选项：
    - ADD_BUDGET: 追加预算 (params: {"amount": 500})
    - FORCE_PASS: 强行通过
    - RESTART: 重新规划启动
    - CANCEL: 取消任务
    """
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
async def get_workflow_steps(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流所有步骤（含并行结构）"""
    from src.models import WorkflowStep
    
    steps = db.query(WorkflowStep).filter(
        WorkflowStep.workflow_id == workflow_id
    ).order_by(WorkflowStep.sequence, WorkflowStep.id).all()
    
    return [_format_step_response(s) for s in steps]


@router.get("/{workflow_id}/history")
async def get_workflow_history(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流历史（含预算变动）"""
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
            "budget_impact": h.budget_impact,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in history
    ]


@router.get("/{workflow_id}/budget")
async def get_workflow_budget(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取预算详情"""
    from src.models import WorkflowInstance
    
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
            "threshold": workflow.rework_budget_threshold,
            "fused": workflow.used_rework_budget >= workflow.rework_budget * (1 - workflow.rework_budget_threshold),
        },
        "total_remaining": workflow.remaining_budget,
    }


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

def _get_current_steps_info(db: Session, workflow_id: str) -> List[Dict]:
    """获取当前步骤信息"""
    from src.models import WorkflowInstance, WorkflowStep
    
    workflow = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == workflow_id
    ).first()
    
    if not workflow or not workflow.current_step_ids:
        return []
    
    steps = db.query(WorkflowStep).filter(
        WorkflowStep.id.in_(workflow.current_step_ids)
    ).all()
    
    return [_format_step_response(s) for s in steps]


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
        "current_step_ids": workflow.current_step_ids,
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
        "is_parallel": step.is_parallel == "true",
        "parent_step_id": step.parent_step_id,
        "parallel_group": step.parallel_group,
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
