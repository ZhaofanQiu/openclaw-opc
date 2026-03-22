"""
Approval Router for v0.4.0

API endpoints for approval workflow management
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import ApprovalRequest, ApprovalStatus
from services.approval_service import ApprovalService
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/approvals", tags=["approvals"])


# ============== Request/Response Models ==============

class ApprovalCreate(BaseModel):
    """Create approval request."""
    task_id: str = Field(..., description="任务ID")
    agent_id: str = Field(..., description="申请员工ID")
    requested_budget: float = Field(..., gt=0, description="申请预算")
    request_reason: str = Field(default="", description="申请理由")
    expires_hours: int = Field(default=24, ge=1, le=168, description="过期时间（小时）")


class ApprovalResponse(BaseModel):
    """Approval response action."""
    comment: str = Field(default="", description="审批意见")


class ApprovalUpdateThreshold(BaseModel):
    """Update approval threshold."""
    threshold: float = Field(..., gt=0, description="新的审批阈值")


class ApprovalResponseModel(BaseModel):
    """Approval request response model."""
    id: str
    task_id: str
    agent_id: Optional[str]
    approver_id: Optional[str]
    requested_budget: float
    request_reason: str
    status: str
    approval_comment: str
    created_at: str
    responded_at: Optional[str]
    expires_at: Optional[str]
    is_expired: bool
    
    class Config:
        from_attributes = True


class ApprovalStatsResponse(BaseModel):
    """Approval statistics response."""
    total: int
    pending: int
    approved: int
    rejected: int
    expired: int
    avg_response_hours: float


# ============== API Endpoints ==============

@router.post("", response_model=ApprovalResponseModel)
async def create_approval(
    data: ApprovalCreate,
    db: Session = Depends(get_db),
):
    """创建预算审批请求。"""
    service = ApprovalService(db)
    try:
        approval = service.create_approval_request(
            task_id=data.task_id,
            agent_id=data.agent_id,
            requested_budget=data.requested_budget,
            request_reason=data.request_reason,
            expires_hours=data.expires_hours,
        )
        return _approval_to_response(approval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ApprovalResponseModel])
async def list_approvals(
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    approver_id: Optional[str] = None,
    task_id: Optional[str] = None,
    include_expired: bool = False,
    db: Session = Depends(get_db),
):
    """列取审批请求。"""
    service = ApprovalService(db)
    approvals = service.get_approval_requests(
        status=status,
        agent_id=agent_id,
        approver_id=approver_id,
        task_id=task_id,
        include_expired=include_expired,
    )
    return [_approval_to_response(a) for a in approvals]


@router.get("/pending", response_model=List[ApprovalResponseModel])
async def get_pending_approvals(
    approver_id: str,
    db: Session = Depends(get_db),
):
    """获取Partner的待审批请求。"""
    service = ApprovalService(db)
    approvals = service.get_pending_for_partner(approver_id)
    return [_approval_to_response(a) for a in approvals]


@router.get("/{approval_id}", response_model=ApprovalResponseModel)
async def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
):
    """获取单个审批请求。"""
    service = ApprovalService(db)
    approval = service.get_approval_request(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return _approval_to_response(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalResponseModel)
async def approve_request(
    approval_id: str,
    data: ApprovalResponse,
    approver_id: str,
    db: Session = Depends(get_db),
):
    """批准预算申请。"""
    service = ApprovalService(db)
    try:
        approval = service.approve_request(
            approval_id=approval_id,
            approver_id=approver_id,
            comment=data.comment,
        )
        return _approval_to_response(approval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/reject", response_model=ApprovalResponseModel)
async def reject_request(
    approval_id: str,
    data: ApprovalResponse,
    approver_id: str,
    db: Session = Depends(get_db),
):
    """拒绝预算申请。"""
    service = ApprovalService(db)
    try:
        approval = service.reject_request(
            approval_id=approval_id,
            approver_id=approver_id,
            comment=data.comment,
        )
        return _approval_to_response(approval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/cancel")
async def cancel_approval(
    approval_id: str,
    db: Session = Depends(get_db),
):
    """取消审批请求。"""
    service = ApprovalService(db)
    try:
        approval = service.cancel_request(approval_id)
        return {
            "success": True,
            "approval": _approval_to_response(approval),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cleanup/expired")
async def cleanup_expired(
    db: Session = Depends(get_db),
):
    """清理过期的审批请求。"""
    service = ApprovalService(db)
    count = service.cleanup_expired_requests()
    return {
        "success": True,
        "cancelled_count": count,
    }


@router.get("/stats/summary", response_model=ApprovalStatsResponse)
async def get_approval_stats(
    db: Session = Depends(get_db),
):
    """获取审批统计。"""
    service = ApprovalService(db)
    stats = service.get_approval_stats()
    return ApprovalStatsResponse(**stats)


@router.post("/threshold")
async def update_threshold(
    data: ApprovalUpdateThreshold,
    db: Session = Depends(get_db),
):
    """更新审批阈值。"""
    from models.config import SystemConfig
    
    config = db.query(SystemConfig).first()
    if not config:
        config = SystemConfig(id="default")
        db.add(config)
    
    config.approval_threshold = data.threshold
    db.commit()
    
    return {
        "success": True,
        "threshold": data.threshold,
        "message": f"Approval threshold updated to {data.threshold} OC coins",
    }


@router.get("/threshold/current")
async def get_threshold(
    db: Session = Depends(get_db),
):
    """获取当前审批阈值。"""
    from models.config import SystemConfig
    
    config = db.query(SystemConfig).first()
    threshold = config.approval_threshold if config and config.approval_threshold else 1000.0
    
    return {
        "threshold": threshold,
        "default": 1000.0,
    }


# ============== Integration Endpoint ==============

@router.get("/check/{task_id}")
async def check_approval_required(
    task_id: str,
    budget: float,
    db: Session = Depends(get_db),
):
    """
    检查任务是否需要审批。
    
    此端点用于任务分配前检查
    """
    service = ApprovalService(db)
    requires = service.requires_approval(budget, task_id)
    
    # Check if already approved
    existing = db.query(ApprovalRequest).filter(
        ApprovalRequest.task_id == task_id,
        ApprovalRequest.status == ApprovalStatus.APPROVED.value
    ).first()
    
    return {
        "requires_approval": requires,
        "already_approved": existing is not None,
        "approved_budget": existing.requested_budget if existing else None,
        "threshold": 1000.0,  # Could fetch from config
    }


# ============== Helper Functions ==============

def _approval_to_response(approval: ApprovalRequest) -> dict:
    """Convert ApprovalRequest model to response dict."""
    return {
        "id": approval.id,
        "task_id": approval.task_id,
        "agent_id": approval.agent_id,
        "approver_id": approval.approver_id,
        "requested_budget": approval.requested_budget,
        "request_reason": approval.request_reason,
        "status": approval.status,
        "approval_comment": approval.approval_comment,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "responded_at": approval.responded_at.isoformat() if approval.responded_at else None,
        "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        "is_expired": approval.is_expired,
    }
