"""
opc-database: 任务模型

定义任务相关的数据模型

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#TaskModel
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .employee import Employee


class TaskStatus(str, PyEnum):
    """任务状态枚举"""

    PENDING = "pending"  # 待分配
    ASSIGNED = "assigned"  # 已分配
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class TaskPriority(str, PyEnum):
    """任务优先级枚举"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """
    任务模型

    表示需要Agent执行的工作单元

    Attributes:
        id: 任务唯一标识
        title: 任务标题
        description: 任务描述
        assigned_to: 分配给哪个员工
        assigned_by: 分配者ID
        status: 任务状态
        priority: 优先级
        estimated_cost: 预估成本
        actual_cost: 实际成本
        result: 执行结果
    """

    __tablename__ = "tasks"

    # 主键
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # 基本信息
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # 分配信息
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("employees.id"), nullable=True
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String, default=TaskStatus.PENDING.value)
    priority: Mapped[str] = mapped_column(String, default=TaskPriority.NORMAL.value)

    # 预算
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    actual_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Token消耗
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)

    # OpenClaw会话
    session_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # 时间戳
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 结果
    result: Mapped[str] = mapped_column(Text, default="")
    result_files: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON数组
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="")

    # 执行上下文 (手册、技能等JSON)
    execution_context: Mapped[str] = mapped_column(Text, default="{}")

    # 返工控制
    rework_count: Mapped[int] = mapped_column(Integer, default=0)
    max_rework: Mapped[int] = mapped_column(Integer, default=3)

    # 关联关系
    assignee: Mapped[Optional["Employee"]] = relationship(
        "Employee", back_populates="tasks", foreign_keys=[assigned_to]
    )
    messages: Mapped[List["TaskMessage"]] = relationship(
        "TaskMessage", back_populates="task", order_by="TaskMessage.created_at"
    )

    @property
    def remaining_budget(self) -> float:
        """剩余预算"""
        return self.estimated_cost - self.actual_cost

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.status == TaskStatus.COMPLETED.value

    @property
    def total_tokens(self) -> int:
        """总Token消耗"""
        return self.tokens_input + self.tokens_output

    def can_rework(self) -> bool:
        """是否可以返工"""
        return self.rework_count < self.max_rework

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base = super().to_dict()
        base.update(
            {
                "id": self.id,
                "title": self.title,
                "description": self.description,
                "status": self.status,
                "priority": self.priority,
                "assigned_to": self.assigned_to,
                "assigned_by": self.assigned_by,
                "estimated_cost": self.estimated_cost,
                "actual_cost": self.actual_cost,
                "remaining_budget": self.remaining_budget,
                "tokens_input": self.tokens_input,
                "tokens_output": self.tokens_output,
                "total_tokens": self.total_tokens,
                "session_key": self.session_key,
                "assigned_at": (
                    self.assigned_at.isoformat() if self.assigned_at else None
                ),
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": (
                    self.completed_at.isoformat() if self.completed_at else None
                ),
                "result": self.result,
                "score": self.score,
                "rework_count": self.rework_count,
                "max_rework": self.max_rework,
            }
        )
        return base


class TaskMessage(Base):
    """
    任务消息模型

    记录任务执行过程中的消息往来
    """

    __tablename__ = "task_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_id: Mapped[str] = mapped_column(String, ForeignKey("tasks.id"), nullable=False)

    # 消息来源
    sender_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # "user" | "agent" | "system"
    sender_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # 消息内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(
        String, default="text"
    )  # "text" | "file" | "action"

    # 元数据 (JSON)
    extra_data: Mapped[str] = mapped_column(Text, default="{}")

    # 关联关系
    task: Mapped["Task"] = relationship("Task", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base = super().to_dict()
        base.update(
            {
                "id": self.id,
                "task_id": self.task_id,
                "sender_type": self.sender_type,
                "sender_id": self.sender_id,
                "content": self.content,
                "message_type": self.message_type,
                "extra_data": self.extra_data,
            }
        )
        return base
