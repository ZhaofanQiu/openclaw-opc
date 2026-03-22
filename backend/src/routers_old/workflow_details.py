"""
Workflow Detail Router v0.5.8

工作流详情API - 提供完整的工作流操作接口
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.services.workflow_detail_service import WorkflowDetailService
from src.services.workflow_execution_service import WorkflowExecutionService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflow-details", tags=["workflow-details"])


class CompleteStepRequest(BaseModel):
    agent_id: str
    result: dict = Field(default_factory=dict)
    actual_hours: Optional[float] = None
    comment: Optional[str] = None


class ReviewStepRequest(BaseModel):
    agent_id: str
    action: str = Field(..., pattern="^(PASS|REWORK)$")
    comment: Optional[str] = None
    review_scores: Optional[dict] = None


class StartWorkflowRequest(BaseModel):
    agent_id: str


class FuseActionRequest(BaseModel):
    agent_id: str
    action: str = Field(..., pattern="^(FORCE_PASS|ADD_BUDGET|CANCEL|RESTART)$")
    budget_amount: Optional[float] = None


class CancelWorkflowRequest(BaseModel):
    agent_id: str
    reason: Optional[str] = None


@router.get("/{workflow_id}")
async def get_workflow_detail(
    workflow_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    获取工作流详情
    
    包含：
    - 工作流基本信息
    - 所有步骤列表
    - 历史记录
    - 返工记录
    - 当前可操作的动作
    """
    service = WorkflowDetailService(db)
    try:
        return service.get_workflow_detail(workflow_id, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/step/{step_id}")
async def get_step_detail(
    step_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取步骤详情"""
    service = WorkflowDetailService(db)
    try:
        return service.get_step_detail(step_id, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{workflow_id}/start")
async def start_workflow(
    workflow_id: str,
    data: StartWorkflowRequest,
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
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/{step_id}/complete")
async def complete_step(
    step_id: str,
    data: CompleteStepRequest,
    db: Session = Depends(get_db),
):
    """
    完成执行步骤
    
    用于 EXECUTE/DOCUMENT/TEST 类型的步骤
    """
    service = WorkflowExecutionService(db)
    
    result = {
        **data.result,
        "actual_hours": data.actual_hours,
        "comment": data.comment,
    }
    
    try:
        response = service.complete_step(
            step_id=step_id,
            action="PASS",
            result=result,
            actor_id=data.agent_id,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/{step_id}/review")
async def review_step(
    step_id: str,
    data: ReviewStepRequest,
    db: Session = Depends(get_db),
):
    """
    评审步骤
    
    - action: PASS 通过
    - action: REWORK 返工
    """
    service = WorkflowExecutionService(db)
    
    result = {
        "comment": data.comment,
        "review_scores": data.review_scores or {},
    }
    
    try:
        response = service.complete_step(
            step_id=step_id,
            action=data.action,
            result=result,
            actor_id=data.agent_id,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/fuse-action")
async def handle_fuse_action(
    workflow_id: str,
    data: FuseActionRequest,
    db: Session = Depends(get_db),
):
    """
    处理熔断后操作
    
    - FORCE_PASS: 强行通过
    - ADD_BUDGET: 追加预算
    - CANCEL: 取消工作流
    - RESTART: 重新启动
    """
    from src.services.fuse_service import FuseService
    
    service = FuseService(db)
    
    try:
        if data.action == "FORCE_PASS":
            result = service.force_pass(workflow_id, data.agent_id)
        elif data.action == "ADD_BUDGET":
            if not data.budget_amount:
                raise HTTPException(status_code=400, detail="追加预算需要提供金额")
            result = service.add_budget(workflow_id, data.budget_amount, data.agent_id)
        elif data.action == "CANCEL":
            result = service.cancel_workflow(workflow_id, data.agent_id)
        elif data.action == "RESTART":
            result = service.restart_workflow(workflow_id, data.agent_id)
        else:
            raise HTTPException(status_code=400, detail="无效的操作")
        
        return {"success": True, "action": data.action, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    data: CancelWorkflowRequest,
    db: Session = Depends(get_db),
):
    """取消工作流"""
    from src.services.fuse_service import FuseService
    
    service = FuseService(db)
    
    try:
        result = service.cancel_workflow(workflow_id, data.agent_id, data.reason)
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/timeline")
async def get_workflow_timeline(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """
    获取工作流时间线
    
    按时间顺序展示所有事件
    """
    from src.models import WorkflowHistory, WorkflowReworkRecord
    
    # 获取历史记录
    history = db.query(WorkflowHistory).filter(
        WorkflowHistory.workflow_id == workflow_id
    ).order_by(WorkflowHistory.created_at).all()
    
    # 获取返工记录
    reworks = db.query(WorkflowReworkRecord).filter(
        WorkflowReworkRecord.workflow_id == workflow_id
    ).order_by(WorkflowReworkRecord.created_at).all()
    
    # 合并并按时间排序
    events = []
    
    for h in history:
        events.append({
            "type": "history",
            "time": h.created_at.isoformat() if h.created_at else None,
            "action": h.action,
            "actor_id": h.actor_id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "details": h.details,
        })
    
    for r in reworks:
        events.append({
            "type": "rework",
            "time": r.created_at.isoformat() if r.created_at else None,
            "from_step_id": r.from_step_id,
            "to_step_id": r.to_step_id,
            "triggered_by": r.triggered_by,
            "reason": r.reason,
            "cost": r.cost,
        })
    
    # 按时间排序
    events.sort(key=lambda x: x["time"] or "")
    
    return {"events": events, "count": len(events)}
