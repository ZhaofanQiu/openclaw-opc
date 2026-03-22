"""
Task Dependency models for v0.4.0

支持任务间的依赖关系，实现工作流自动化
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class TaskDependencyStatus(str, PyEnum):
    """Task dependency status."""
    ACTIVE = "active"       # 依赖关系激活中
    TRIGGERED = "triggered" # 已触发下游任务
    CANCELLED = "cancelled" # 已取消


class TaskDependency(Base):
    """
    Task Dependency model for v0.4.0
    
    定义任务间的依赖关系：上游任务完成后自动触发下游任务
    """
    
    __tablename__ = "task_dependencies"
    
    id = Column(String, primary_key=True)
    
    # 上游任务（完成后触发）
    upstream_task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    
    # 下游任务（被触发的任务）
    downstream_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    
    # 如果下游任务还未创建，可以存储模板配置
    downstream_task_template = Column(Text, default="{}")  # JSON格式
    
    # 触发条件
    trigger_condition = Column(String, default="completed")  # completed/failed/any
    
    # 延迟触发（分钟）
    delay_minutes = Column(Integer, default=0)
    
    # 状态
    status = Column(String, default=TaskDependencyStatus.ACTIVE.value)
    
    # 触发记录
    triggered_at = Column(DateTime, nullable=True)
    
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    upstream_task = relationship("Task", foreign_keys=[upstream_task_id], back_populates="downstream_dependencies")
    downstream_task = relationship("Task", foreign_keys=[downstream_task_id], back_populates="upstream_dependencies")
    
    def __repr__(self):
        return f"<TaskDependency(id={self.id}, upstream={self.upstream_task_id}, downstream={self.downstream_task_id})>"


# 在 Task 模型中添加关系
# downstream_dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.upstream_task_id", back_populates="upstream_task")
# upstream_dependencies = relationship("TaskDependency", foreign_keys="TaskDependency.downstream_task_id", back_populates="downstream_task")
