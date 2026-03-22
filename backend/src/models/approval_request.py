"""
Approval Workflow models for v0.4.0

高预算任务需要Partner审批才能执行
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ApprovalStatus(str, PyEnum):
    """Approval request status."""
    PENDING = "pending"       # 等待审批
    APPROVED = "approved"     # 已批准
    REJECTED = "rejected"     # 已拒绝
    CANCELLED = "cancelled"   # 已取消（任务被删除等）


class ApprovalRequest(Base):
    """
    Approval request model for v0.4.0
    
    高预算任务需要Partner审批才能执行
    """
    
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True)
    
    # 关联任务
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    
    # 申请员工
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # 审批人（Partner）
    approver_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # 预算信息
    requested_budget = Column(Float, nullable=False)
    
    # 申请理由
    request_reason = Column(Text, default="")
    
    # 状态
    status = Column(String, default=ApprovalStatus.PENDING.value)
    
    # Partner审批意见
    approval_comment = Column(Text, default="")
    
    # 时间线
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    
    # 自动过期（可选）
    expires_at = Column(DateTime, nullable=True)
    
    # 关系
    task = relationship("Task", back_populates="approval_requests")
    agent = relationship("Agent", foreign_keys=[agent_id], back_populates="approval_requests_sent")
    approver = relationship("Agent", foreign_keys=[approver_id], back_populates="approval_requests_handled")
    
    def __repr__(self):
        return f"<ApprovalRequest(id={self.id}, task_id={self.task_id}, status={self.status})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if approval request has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_pending(self) -> bool:
        """Check if approval request is still pending."""
        return self.status == ApprovalStatus.PENDING.value


# 在 Task 模型中添加关系
# approval_requests = relationship("ApprovalRequest", back_populates="task", cascade="all, delete-orphan")
