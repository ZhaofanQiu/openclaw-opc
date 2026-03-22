"""
Agent (Employee) models.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from src.database import Base


class AgentStatus(str, PyEnum):
    """Agent status enum."""
    IDLE = "idle"
    WORKING = "working"
    RESTING = "resting"


class PositionLevel(int, PyEnum):
    """Position level enum."""
    INTERN = 1
    SPECIALIST = 2
    SENIOR = 3
    EXPERT = 4
    PARTNER = 5


class Agent(Base):
    """Agent (Employee) model."""
    
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    emoji = Column(String, default="🧑‍💻")
    
    # Position
    position_level = Column(Integer, default=PositionLevel.INTERN.value)
    position_title = Column(String, default="实习生")
    
    # OpenClaw mapping
    agent_id = Column(String, unique=True, nullable=True)  # OpenClaw agent ID (optional for unbound employees)
    is_bound = Column(String, default="false")  # "true" if bound to OpenClaw agent, "false" if virtual employee
    
    # Budget
    monthly_budget = Column(Float, default=2000.0)  # OC币
    used_budget = Column(Float, default=0.0)
    
    # Status
    status = Column(String, default=AgentStatus.IDLE.value)
    current_task_id = Column(String, nullable=True)
    
    # Growth
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    
    # SOUL.md content
    soul_md = Column(Text, default="")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Health monitoring (for Partner)
    last_heartbeat = Column(DateTime, nullable=True)
    is_online = Column(String, default="unknown")  # online, offline, unknown
    
    # Avatar URL (stored path or external URL)
    avatar_url = Column(String, nullable=True)
    avatar_source = Column(String, default="system")  # system, uploaded, ai
    
    # Relationships
    skills = relationship("Skill", secondary="agent_skills", back_populates="agents")
    sub_tasks = relationship("SubTask", back_populates="agent")  # v0.4.0 - Sub-task support
    approval_requests_sent = relationship("ApprovalRequest", foreign_keys="ApprovalRequest.agent_id", back_populates="agent")  # v0.4.0
    approval_requests_handled = relationship("ApprovalRequest", foreign_keys="ApprovalRequest.approver_id", back_populates="approver")  # v0.4.0
    skill_growth = relationship("AgentSkillGrowth", back_populates="agent", cascade="all, delete-orphan")  # v0.4.0
    task_steps = relationship("TaskStep", back_populates="executor")  # v0.5.0 - Chat-based collaboration
    skill_growth_history = relationship("SkillGrowthHistory", back_populates="agent", cascade="all, delete-orphan")  # v0.4.0
    shared_memories = relationship("SharedMemory", back_populates="agent", cascade="all, delete-orphan")  # v0.4.0
    memory_access_logs = relationship("MemoryAccessLog", back_populates="agent", cascade="all, delete-orphan")  # v0.4.0
    
    @property
    def remaining_budget(self) -> float:
        """Calculate remaining budget."""
        return self.monthly_budget - self.used_budget
    
    @property
    def total_budget(self) -> float:
        """Total budget (alias for monthly_budget)."""
        return self.monthly_budget
    
    @property
    def mood_percentage(self) -> float:
        """Calculate mood as percentage of remaining budget."""
        if self.monthly_budget <= 0:
            return 0.0
        return (self.remaining_budget / self.monthly_budget) * 100
    
    @property
    def mood_emoji(self) -> str:
        """Get mood emoji based on budget."""
        pct = self.mood_percentage
        if pct > 60:
            return "😊"
        elif pct > 30:
            return "😐"
        elif pct > 10:
            return "😔"
        else:
            return "🚨"
