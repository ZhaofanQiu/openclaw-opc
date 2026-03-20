"""
Notification service for user messages.
"""

from datetime import datetime
from typing import List, Optional

from src.database import Base
from src.models import Notification, NotificationType


class NotificationService:
    """Notification service."""
    
    def __init__(self, db):
        self.db = db
    
    def create_notification(
        self,
        type_: str,
        title: str,
        message: str,
        task_id: str = None,
        agent_id: str = None,
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            type=type_,
            title=title,
            message=message,
            task_id=task_id,
            agent_id=agent_id,
            is_read="false",
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
    
    def get_notifications(
        self,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notifications with optional filtering."""
        query = self.db.query(Notification)
        
        if unread_only:
            query = query.filter(Notification.is_read == "false")
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return self.db.query(Notification).filter(
            Notification.is_read == "false"
        ).count()
    
    def mark_as_read(self, notification_id: int) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id
        ).first()
        
        if not notification:
            return False
        
        notification.is_read = "true"
        notification.read_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def mark_all_as_read(self) -> int:
        """Mark all notifications as read. Returns count updated."""
        notifications = self.db.query(Notification).filter(
            Notification.is_read == "false"
        ).all()
        
        count = 0
        for n in notifications:
            n.is_read = "true"
            n.read_at = datetime.utcnow()
            count += 1
        
        self.db.commit()
        return count
    
    # Helper methods for specific notification types
    def notify_task_assigned(self, task_id: str, task_title: str, agent_name: str) -> Notification:
        """Notify when a task is assigned."""
        return self.create_notification(
            type_=NotificationType.TASK_ASSIGNED.value,
            title=f"任务已分配",
            message=f"任务「{task_title}」已分配给 {agent_name}",
            task_id=task_id,
        )
    
    def notify_task_completed(self, task_id: str, task_title: str, agent_name: str) -> Notification:
        """Notify when a task is completed."""
        return self.create_notification(
            type_=NotificationType.TASK_COMPLETED.value,
            title=f"任务已完成",
            message=f"{agent_name} 完成了任务「{task_title}」",
            task_id=task_id,
        )
    
    def notify_task_failed(self, task_id: str, task_title: str, agent_name: str, reason: str = "") -> Notification:
        """Notify when a task fails."""
        msg = f"{agent_name} 执行任务「{task_title}」失败"
        if reason:
            msg += f"：{reason}"
        return self.create_notification(
            type_=NotificationType.TASK_FAILED.value,
            title=f"任务失败",
            message=msg,
            task_id=task_id,
        )
    
    def notify_task_overdue(self, task_id: str, task_title: str, minutes_overdue: int) -> Notification:
        """Notify when a task is overdue."""
        return self.create_notification(
            type_=NotificationType.TASK_OVERDUE.value,
            title=f"任务已超时",
            message=f"任务「{task_title}」已超时 {minutes_overdue} 分钟未开始",
            task_id=task_id,
        )
    
    def notify_budget_warning(self, agent_name: str, remaining_percent: float) -> Notification:
        """Notify when agent budget is low."""
        return self.create_notification(
            type_=NotificationType.BUDGET_WARNING.value,
            title=f"预算警告",
            message=f"{agent_name} 的预算仅剩 {remaining_percent:.1f}%",
        )
    
    def notify_agent_offline(self, agent_name: str) -> Notification:
        """Notify when an agent goes offline."""
        return self.create_notification(
            type_=NotificationType.AGENT_OFFLINE.value,
            title=f"员工离线",
            message=f"{agent_name} 已离线，可能无法接收新任务",
        )
