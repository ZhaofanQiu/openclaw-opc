"""
Notification model.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Integer, String, Text

from src.database import Base


class NotificationType(str, PyEnum):
    """Notification types."""
    TASK_ASSIGNED = "task_assigned"  # Task assigned to agent
    TASK_COMPLETED = "task_completed"  # Task completed
    TASK_FAILED = "task_failed"  # Task failed
    TASK_OVERDUE = "task_overdue"  # Task overdue (not started in time)
    BUDGET_WARNING = "budget_warning"  # Budget approaching limit
    BUDGET_FUSED = "budget_fused"  # Budget exceeded
    AGENT_OFFLINE = "agent_offline"  # Agent went offline
    SYSTEM = "system"  # General system notification


class Notification(Base):
    """User notification model."""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    
    # Notification content
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Related entities (optional)
    task_id = Column(String, nullable=True)
    agent_id = Column(String, nullable=True)
    
    # Status
    is_read = Column(String, default="false")  # "true" or "false"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
