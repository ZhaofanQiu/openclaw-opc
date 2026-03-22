"""
Simplified Task Model (v2.0)

核心字段，移除冗余功能
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from database import Base


class TaskStatus(str, PyEnum):
    """任务状态"""
    PENDING = "pending"      # 待分配
    ASSIGNED = "assigned"    # 已分配
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


class TaskPriority(str, PyEnum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """任务模型 (简化版 v2.0)"""
    
    __tablename__ = "tasks_v2"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    
    # 分配
    assigned_to = Column(String, ForeignKey("agents.id"), nullable=True)
    assigned_by = Column(String, nullable=True)  # user_id or agent_id
    
    # 状态
    status = Column(String, default=TaskStatus.PENDING.value)
    priority = Column(String, default=TaskPriority.NORMAL.value)
    
    # 预算
    estimated_cost = Column(Float, default=0.0)  # 预估成本 (OC币)
    actual_cost = Column(Float, default=0.0)     # 实际成本
    
    # Token 消耗
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    
    # OpenClaw 会话
    session_key = Column(String, nullable=True)  # OpenClaw session ID
    
    # 时间
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 结果
    result = Column(Text, default="")  # Agent 执行结果
    score = Column(Integer, nullable=True)  # 评分 (1-5)
    feedback = Column(Text, default="")  # 反馈
    
    # 执行上下文 (手册、技能等)
    execution_context = Column(Text, default="")  # JSON 字符串
    
    # 返工计数
    rework_count = Column(Integer, default=0)
    max_rework = Column(Integer, default=3)
    
    @property
    def remaining_budget(self) -> float:
        """剩余预算"""
        return self.estimated_cost - self.actual_cost
    
    def to_dict(self) -> dict:
        """转字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
