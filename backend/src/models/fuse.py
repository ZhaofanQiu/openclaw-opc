"""
Fuse Event Models

Budget fuse events and post-fuse actions.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Float, Text

from src.database import Base


class FuseAction(str, PyEnum):
    """Post-fuse action types."""
    ADD_BUDGET = "add_budget"  # Add more budget
    SPLIT_TASK = "split_task"  # Split into smaller tasks
    REASSIGN = "reassign"      # Reassign to another agent
    PAUSE = "pause"            # Pause and wait


class FuseEventStatus(str, PyEnum):
    """Fuse event status."""
    TRIGGERED = "triggered"    # Fuse just triggered
    PENDING = "pending"        # Waiting for user action
    RESOLVED = "resolved"      # Action taken
    IGNORED = "ignored"        # User ignored


class BudgetFuseEvent(Base):
    """Budget fuse event log."""
    __tablename__ = "budget_fuse_events"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=True, index=True)
    
    # Fuse details
    fuse_type = Column(String, nullable=False)  # warning (80%), pause (100%), fuse (150%)
    threshold_percentage = Column(Float, nullable=False)
    budget_used = Column(Float, nullable=False)
    budget_total = Column(Float, nullable=False)
    
    # Status
    status = Column(String, default=FuseEventStatus.PENDING.value)
    
    # Resolution
    resolved_action = Column(String, nullable=True)  # FuseAction value
    resolved_by = Column(String, nullable=True)  # Employee ID
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)
    
    # Additional data (JSON)
    additional_data = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
