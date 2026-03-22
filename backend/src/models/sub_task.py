"""
Sub-task models for v0.4.0

支持复杂任务拆分为多个子任务，实现多Agent协作
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from database import Base


class SubTaskStatus(str, PyEnum):
    """Sub-task status enum."""
    PENDING = "pending"           # 待分配
    ASSIGNED = "assigned"         # 已分配
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    BLOCKED = "blocked"           # 被阻塞（等待依赖）


class SubTask(Base):
    """
    Sub-task model for v0.4.0
    
    子任务依附于父任务，每个子任务可以分配给不同员工
    子任务可以设置依赖关系（必须先完成依赖的子任务）
    """
    
    __tablename__ = "sub_tasks"
    
    id = Column(String, primary_key=True)
    
    # 关联父任务
    parent_task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    
    # 关联员工（可选，未分配时为None）
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # 基本信息
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    
    # 顺序（用于确定执行顺序，数字小的先执行）
    sequence_order = Column(Integer, default=0)
    
    # 状态
    status = Column(String, default=SubTaskStatus.PENDING.value)
    
    # 预算
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    
    # 依赖关系（存储依赖的子任务ID列表，JSON格式）
    depends_on = Column(Text, default="[]")  # JSON list of sub_task_ids
    
    # 时间线
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 结果
    result_summary = Column(Text, default="")
    
    # 是否是关键路径上的任务
    is_critical = Column(String, default="false")  # "true" or "false"
    
    # 关联关系
    parent_task = relationship("Task", back_populates="sub_tasks")
    agent = relationship("Agent", back_populates="sub_tasks")
    
    def __repr__(self):
        return f"<SubTask(id={self.id}, title={self.title}, status={self.status})>"
    
    @property
    def is_completed(self) -> bool:
        """Check if sub-task is completed."""
        return self.status == SubTaskStatus.COMPLETED.value
    
    @property
    def is_blocked(self) -> bool:
        """Check if sub-task is blocked by dependencies."""
        return self.status == SubTaskStatus.BLOCKED.value


# 更新 Task 模型，添加子任务关系
# 需要在 Task 模型中添加：
# sub_tasks = relationship("SubTask", back_populates="parent_task", cascade="all, delete-orphan")
