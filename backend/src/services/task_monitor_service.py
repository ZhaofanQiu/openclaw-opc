"""
Task monitoring service for detecting timeouts and overdue tasks.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from models import SystemConfig, Task, TaskStatus
from services.config_service import ConfigService


class TaskMonitorService:
    """
    Service for monitoring task status and detecting issues.
    
    - Detects overdue tasks (assigned but not started within timeout)
    - Tracks task progress
    - Generates alerts
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.config_service = ConfigService(db)
    
    def check_overdue_tasks(self) -> List[dict]:
        """
        Check for overdue tasks.
        
        A task is overdue if:
        - Status is ASSIGNED
        - Assigned more than task_timeout_minutes ago
        - Not yet started (no started_at timestamp)
        
        Returns:
            List of overdue task details
        """
        timeout_minutes = self.config_service.get_task_timeout_minutes()
        timeout_delta = timedelta(minutes=timeout_minutes)
        
        # Find tasks that are assigned but not started, and assigned_at is older than timeout
        cutoff_time = datetime.utcnow() - timeout_delta
        
        overdue_tasks = self.db.query(Task).filter(
            Task.status == TaskStatus.ASSIGNED.value,
            Task.started_at.is_(None),  # Not started yet
            Task.assigned_at < cutoff_time,  # Assigned before cutoff
            Task.is_overdue == "false"  # Not already marked as overdue
        ).all()
        
        results = []
        for task in overdue_tasks:
            # Mark as overdue
            task.is_overdue = "true"
            
            # Calculate how long it's been assigned
            assigned_duration = datetime.utcnow() - task.assigned_at
            assigned_minutes = int(assigned_duration.total_seconds() / 60)
            
            # Get agent name for notification
            agent_name = "Unknown"
            if task.agent_id:
                from models import Agent
                agent = self.db.query(Agent).filter(Agent.id == task.agent_id).first()
                if agent:
                    agent_name = agent.name
            
            # Create notification
            from services.notification_service import NotificationService
            notification_service = NotificationService(self.db)
            notification_service.notify_task_overdue(
                task_id=task.id,
                task_title=task.title,
                minutes_overdue=assigned_minutes
            )
            
            results.append({
                "task_id": task.id,
                "title": task.title,
                "assigned_at": task.assigned_at.isoformat() if task.assigned_at else None,
                "assigned_minutes_ago": assigned_minutes,
                "timeout_threshold": timeout_minutes,
                "agent_id": task.agent_id,
                "agent_name": agent_name,
            })
        
        if results:
            self.db.commit()
        
        return results
    
    def get_overdue_tasks(self) -> List[Task]:
        """Get all tasks marked as overdue."""
        return self.db.query(Task).filter(
            Task.is_overdue == "true",
            Task.status.in_([TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value])
        ).all()
    
    def get_task_status_summary(self) -> dict:
        """Get summary of task statuses including overdue count."""
        total = self.db.query(Task).count()
        pending = self.db.query(Task).filter(Task.status == TaskStatus.PENDING.value).count()
        assigned = self.db.query(Task).filter(Task.status == TaskStatus.ASSIGNED.value).count()
        in_progress = self.db.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS.value).count()
        completed = self.db.query(Task).filter(Task.status == TaskStatus.COMPLETED.value).count()
        fused = self.db.query(Task).filter(Task.status == TaskStatus.FUSED.value).count()
        overdue = self.db.query(Task).filter(Task.is_overdue == "true").count()
        
        timeout_minutes = self.config_service.get_task_timeout_minutes()
        
        return {
            "total": total,
            "pending": pending,
            "assigned": assigned,
            "in_progress": in_progress,
            "completed": completed,
            "fused": fused,
            "overdue": overdue,
            "timeout_minutes": timeout_minutes,
        }
    
    def acknowledge_overdue(self, task_id: str) -> bool:
        """
        Acknowledge an overdue task (mark as notified).
        
        Returns:
            True if task was found and updated
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        task.overdue_notified_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def clear_overdue_status(self, task_id: str) -> bool:
        """
        Clear overdue status when task is started or reassigned.
        
        Returns:
            True if task was found and updated
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        task.is_overdue = "false"
        task.overdue_notified_at = None
        self.db.commit()
        return True