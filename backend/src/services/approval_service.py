"""
Approval Service for v0.4.0

管理高预算任务的审批流程
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import ApprovalRequest, ApprovalStatus, Task, TaskStatus, Agent
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ApprovalService:
    """Service for managing approval workflows."""
    
    # 需要审批的预算阈值（默认 1000 OC币）
    DEFAULT_APPROVAL_THRESHOLD = 1000.0
    
    def __init__(self, db: Session):
        self.db = db
    
    def requires_approval(self, budget: float, task_id: str = None) -> bool:
        """
        Check if a budget amount requires approval.
        
        Args:
            budget: Budget amount to check
            task_id: Optional task ID to check existing approval
        
        Returns:
            True if approval is required
        """
        # Get threshold from config or use default
        from src.models.config import SystemConfig
        config = self.db.query(SystemConfig).first()
        threshold = config.approval_threshold if config and config.approval_threshold else self.DEFAULT_APPROVAL_THRESHOLD
        
        if budget < threshold:
            return False
        
        # If task_id provided, check if already approved
        if task_id:
            existing = self.db.query(ApprovalRequest).filter(
                ApprovalRequest.task_id == task_id,
                ApprovalRequest.status == ApprovalStatus.APPROVED.value
            ).first()
            if existing:
                return False
        
        return True
    
    def create_approval_request(
        self,
        task_id: str,
        agent_id: str,
        requested_budget: float,
        request_reason: str = "",
        expires_hours: int = 24,
    ) -> ApprovalRequest:
        """
        Create an approval request for a high-budget task.
        
        Args:
            task_id: Task requiring approval
            agent_id: Agent requesting approval
            requested_budget: Budget amount requested
            request_reason: Reason for the request
            expires_hours: Hours until request expires
        
        Returns:
            Created approval request
        """
        # Verify task exists
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found")
        
        # Verify agent exists
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Check for existing pending request
        existing = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.task_id == task_id,
            ApprovalRequest.status == ApprovalStatus.PENDING.value
        ).first()
        
        if existing:
            raise ValueError(f"Pending approval request already exists for task '{task_id}'")
        
        # Find Partner (approver)
        from src.models.agent import PositionLevel
        partner = self.db.query(Agent).filter(
            Agent.position_level == PositionLevel.PARTNER.value
        ).first()
        
        if not partner:
            raise ValueError("No Partner found to handle approval")
        
        # Create approval request
        approval = ApprovalRequest(
            id=str(uuid.uuid4())[:8],
            task_id=task_id,
            agent_id=agent_id,
            approver_id=partner.id,
            requested_budget=requested_budget,
            request_reason=request_reason or f"Task '{task.title}' requires budget approval",
            status=ApprovalStatus.PENDING.value,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
        )
        
        self.db.add(approval)
        
        # Update task status to indicate pending approval
        task.status = TaskStatus.PENDING.value  # Keep as pending until approved
        
        self.db.commit()
        self.db.refresh(approval)
        
        logger.info(
            "approval_request_created",
            approval_id=approval.id,
            task_id=task_id,
            agent_id=agent_id,
            requested_budget=requested_budget,
            approver_id=partner.id,
        )
        
        return approval
    
    def approve_request(
        self,
        approval_id: str,
        approver_id: str,
        comment: str = "",
    ) -> ApprovalRequest:
        """
        Approve a pending request.
        
        Args:
            approval_id: Approval request ID
            approver_id: Approver (Partner) ID
            comment: Approval comment
        
        Returns:
            Updated approval request
        """
        approval = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id
        ).first()
        
        if not approval:
            raise ValueError(f"Approval request '{approval_id}' not found")
        
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValueError(f"Cannot approve request with status '{approval.status}'")
        
        if approval.is_expired:
            approval.status = ApprovalStatus.CANCELLED.value
            self.db.commit()
            raise ValueError("Approval request has expired")
        
        # Verify approver is Partner
        approver = self.db.query(Agent).filter(Agent.id == approver_id).first()
        if not approver:
            raise ValueError(f"Approver '{approver_id}' not found")
        
        from src.models.agent import PositionLevel
        if approver.position_level != PositionLevel.PARTNER.value:
            raise ValueError("Only Partner can approve requests")
        
        # Update approval
        approval.status = ApprovalStatus.APPROVED.value
        approval.approval_comment = comment or "Approved"
        approval.responded_at = datetime.utcnow()
        approval.approver_id = approver_id
        
        # Update task to allow assignment
        task = self.db.query(Task).filter(Task.id == approval.task_id).first()
        if task:
            task.status = TaskStatus.PENDING.value  # Ready for assignment
        
        self.db.commit()
        self.db.refresh(approval)
        
        logger.info(
            "approval_request_approved",
            approval_id=approval_id,
            task_id=approval.task_id,
            approver_id=approver_id,
        )
        
        return approval
    
    def reject_request(
        self,
        approval_id: str,
        approver_id: str,
        comment: str = "",
    ) -> ApprovalRequest:
        """
        Reject a pending request.
        
        Args:
            approval_id: Approval request ID
            approver_id: Approver (Partner) ID
            comment: Rejection reason
        
        Returns:
            Updated approval request
        """
        approval = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id
        ).first()
        
        if not approval:
            raise ValueError(f"Approval request '{approval_id}' not found")
        
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValueError(f"Cannot reject request with status '{approval.status}'")
        
        # Verify approver is Partner
        approver = self.db.query(Agent).filter(Agent.id == approver_id).first()
        if not approver:
            raise ValueError(f"Approver '{approver_id}' not found")
        
        from src.models.agent import PositionLevel
        if approver.position_level != PositionLevel.PARTNER.value:
            raise ValueError("Only Partner can reject requests")
        
        # Update approval
        approval.status = ApprovalStatus.REJECTED.value
        approval.approval_comment = comment or "Rejected"
        approval.responded_at = datetime.utcnow()
        approval.approver_id = approver_id
        
        # Mark task as failed (rejected)
        task = self.db.query(Task).filter(Task.id == approval.task_id).first()
        if task:
            task.status = TaskStatus.FAILED.value
            task.result_summary = f"Budget approval rejected: {comment or 'No reason provided'}"
        
        self.db.commit()
        self.db.refresh(approval)
        
        logger.info(
            "approval_request_rejected",
            approval_id=approval_id,
            task_id=approval.task_id,
            approver_id=approver_id,
            reason=comment,
        )
        
        return approval
    
    def get_approval_requests(
        self,
        status: str = None,
        agent_id: str = None,
        approver_id: str = None,
        task_id: str = None,
        include_expired: bool = False,
    ) -> List[ApprovalRequest]:
        """
        Get approval requests with filtering.
        
        Args:
            status: Filter by status
            agent_id: Filter by requesting agent
            approver_id: Filter by approver
            task_id: Filter by task
            include_expired: Include expired requests
        
        Returns:
            List of approval requests
        """
        query = self.db.query(ApprovalRequest)
        
        if status:
            query = query.filter(ApprovalRequest.status == status)
        
        if agent_id:
            query = query.filter(ApprovalRequest.agent_id == agent_id)
        
        if approver_id:
            query = query.filter(ApprovalRequest.approver_id == approver_id)
        
        if task_id:
            query = query.filter(ApprovalRequest.task_id == task_id)
        
        if not include_expired:
            query = query.filter(
                (ApprovalRequest.expires_at == None) |
                (ApprovalRequest.expires_at > datetime.utcnow())
            )
        
        return query.order_by(ApprovalRequest.created_at.desc()).all()
    
    def get_approval_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get a single approval request by ID."""
        return self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id
        ).first()
    
    def get_pending_for_partner(self, partner_id: str) -> List[ApprovalRequest]:
        """
        Get pending approval requests for a Partner.
        
        Args:
            partner_id: Partner agent ID
        
        Returns:
            List of pending approval requests
        """
        return self.get_approval_requests(
            status=ApprovalStatus.PENDING.value,
            approver_id=partner_id,
        )
    
    def cancel_request(self, approval_id: str) -> ApprovalRequest:
        """
        Cancel an approval request (e.g., when task is deleted).
        
        Args:
            approval_id: Approval request ID
        
        Returns:
            Updated approval request
        """
        approval = self.get_approval_request(approval_id)
        if not approval:
            raise ValueError(f"Approval request '{approval_id}' not found")
        
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValueError(f"Cannot cancel request with status '{approval.status}'")
        
        approval.status = ApprovalStatus.CANCELLED.value
        self.db.commit()
        self.db.refresh(approval)
        
        logger.info("approval_request_cancelled", approval_id=approval_id)
        
        return approval
    
    def cleanup_expired_requests(self) -> int:
        """
        Clean up expired pending approval requests.
        
        Returns:
            Number of requests cancelled
        """
        expired = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.status == ApprovalStatus.PENDING.value,
            ApprovalRequest.expires_at < datetime.utcnow()
        ).all()
        
        count = 0
        for approval in expired:
            approval.status = ApprovalStatus.CANCELLED.value
            count += 1
            
            # Update task status
            task = self.db.query(Task).filter(Task.id == approval.task_id).first()
            if task and task.status == TaskStatus.PENDING.value:
                task.status = TaskStatus.FAILED.value
                task.result_summary = "Budget approval request expired"
        
        if count > 0:
            self.db.commit()
            logger.info("expired_approval_requests_cleaned", count=count)
        
        return count
    
    def get_approval_stats(self) -> Dict:
        """
        Get approval statistics.
        
        Returns:
            Statistics dict
        """
        stats = {
            "total": self.db.query(ApprovalRequest).count(),
            "pending": self.db.query(ApprovalRequest).filter(
                ApprovalRequest.status == ApprovalStatus.PENDING.value
            ).count(),
            "approved": self.db.query(ApprovalRequest).filter(
                ApprovalRequest.status == ApprovalStatus.APPROVED.value
            ).count(),
            "rejected": self.db.query(ApprovalRequest).filter(
                ApprovalRequest.status == ApprovalStatus.REJECTED.value
            ).count(),
            "expired": self.db.query(ApprovalRequest).filter(
                ApprovalRequest.status == ApprovalStatus.CANCELLED.value
            ).count(),
        }
        
        # Calculate average response time
        responded = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.responded_at != None
        ).all()
        
        if responded:
            total_hours = sum(
                (r.responded_at - r.created_at).total_seconds() / 3600
                for r in responded
            )
            stats["avg_response_hours"] = round(total_hours / len(responded), 2)
        else:
            stats["avg_response_hours"] = 0
        
        return stats
