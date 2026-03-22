"""
Simplified Agent Model (v2.0)

核心字段，移除冗余功能
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from database import Base


class AgentStatus(str, PyEnum):
    """员工状态"""
    IDLE = "idle"       # 空闲
    WORKING = "working" # 工作中
    OFFLINE = "offline" # 离线


class PositionLevel(int, PyEnum):
    """职位等级"""
    INTERN = 1      # 实习生
    SPECIALIST = 2  # 专员
    SENIOR = 3      # 资深
    EXPERT = 4      # 专家
    PARTNER = 5     # 合伙人


class Agent(Base):
    """员工模型 (简化版 v2.0)"""
    
    __tablename__ = "agents_v2"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    emoji = Column(String, default="🤖")
    
    # 职位
    position_level = Column(Integer, default=PositionLevel.INTERN.value)
    
    # OpenClaw 绑定
    openclaw_agent_id = Column(String, unique=True, nullable=True)
    is_bound = Column(String, default="false")  # "true" | "false"
    
    # 预算
    monthly_budget = Column(Float, default=1000.0)  # OC币
    used_budget = Column(Float, default=0.0)
    
    # 状态
    status = Column(String, default=AgentStatus.IDLE.value)
    current_task_id = Column(String, nullable=True)
    
    # 统计
    completed_tasks = Column(Integer, default=0)
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def remaining_budget(self) -> float:
        """剩余预算"""
        return self.monthly_budget - self.used_budget
    
    @property
    def budget_percentage(self) -> float:
        """预算剩余百分比"""
        if self.monthly_budget <= 0:
            return 0.0
        return (self.remaining_budget / self.monthly_budget) * 100
    
    @property
    def mood_emoji(self) -> str:
        """心情表情"""
        pct = self.budget_percentage
        if pct > 60:
            return "😊"
        elif pct > 30:
            return "😐"
        elif pct > 10:
            return "😔"
        else:
            return "🚨"
    
    def to_dict(self) -> dict:
        """转字典"""
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "position_level": self.position_level,
            "status": self.status,
            "monthly_budget": self.monthly_budget,
            "used_budget": self.used_budget,
            "remaining_budget": self.remaining_budget,
            "mood": self.mood_emoji,
            "current_task_id": self.current_task_id
        }
