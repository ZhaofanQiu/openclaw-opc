"""
Task models.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.database import Base


class TaskStatus(str, PyEnum):
    """Task status enum."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    FUSED = "fused"  # Budget exceeded
    SPLIT = "split"  # Task was split into sub-tasks


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
    
    # Parent task (for sub-tasks created from splitting)
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)

    # Status
    status = Column(String, default=TaskStatus.PENDING.value)
    priority = Column(String, default=TaskPriority.NORMAL.value)

    # Budget (estimated from task complexity)
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)

    # Exact token tracking (from session_status)
    actual_tokens_input = Column(Integer, default=0)  # Actual input tokens
    actual_tokens_output = Column(Integer, default=0)  # Actual output tokens
    is_exact = Column(String, default="false")  # "true" if exact, "false" if estimated
    session_key = Column(String, nullable=True)  # OpenClaw session identifier

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
    
    # Execution tracking (v0.3.0 P0 - Agent execution loop)
    execution_status = Column(String, default="")  # sent, acked, running, completed, failed, timeout
    sent_to_agent_at = Column(DateTime, nullable=True)  # When task was sent to agent
    execution_session_id = Column(String, nullable=True)  # OpenClaw session ID
    token_used = Column(Integer, default=0)  # Actual tokens consumed (reported by agent)

    # v0.4.0 - Sub-task support
    is_parent_task = Column(String, default="false")  # "true" if this task has sub-tasks
    sub_task_count = Column(Integer, default=0)  # Number of sub-tasks
    completed_sub_task_count = Column(Integer, default=0)  # Number of completed sub-tasks

    # Relationships
    skill_requirements = relationship("TaskSkillRequirement", back_populates="task",
                                      cascade="all, delete-orphan")
    sub_tasks = relationship("SubTask", back_populates="parent_task", 
                             cascade="all, delete-orphan", foreign_keys="SubTask.parent_task_id")

    @property
    def budget_usage_percentage(self) -> float:
        """Calculate budget usage percentage."""
        if self.estimated_cost <= 0:
            return 0.0
        return (self.actual_cost / self.estimated_cost) * 100
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens consumed (input + output)."""
        return self.actual_tokens_input + self.actual_tokens_output
