"""
Task models.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from src.database import Base


class TaskStatus(str, PyEnum):
    """Task status enum."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    FUSED = "fused"  # Budget exceeded


class TaskPriority(str, PyEnum):
    """Task priority enum."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """Task model."""
    
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    
    # Assignment
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # Status
    status = Column(String, default=TaskStatus.PENDING.value)
    priority = Column(String, default=TaskPriority.NORMAL.value)
    
    # Budget
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    
    # Timeline
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)  # When agent actually starts working
    completed_at = Column(DateTime, nullable=True)
    
    # Timeout tracking
    is_overdue = Column(String, default="false")  # "true" or "false"
    overdue_notified_at = Column(DateTime, nullable=True)
    
    # Result
    result_summary = Column(Text, default="")
    
    @property
    def budget_usage_percentage(self) -> float:
        """Calculate budget usage percentage."""
        if self.estimated_cost <= 0:
            return 0.0
        return (self.actual_cost / self.estimated_cost) * 100
