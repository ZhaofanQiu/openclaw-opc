"""
任务步骤模型 - 离线聊天协作系统的核心
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship

from src.database import Base


class TaskStepStatus(str, PyEnum):
    """任务步骤状态"""
    PENDING = "pending"           # 待分配
    ASSIGNED = "assigned"         # 已分配，等待员工开始
    IN_PROGRESS = "in_progress"   # 员工正在执行
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    REWORK = "rework"             # 返工中（从completed回退）
    WAITING_REWORK = "waiting_rework"  # 等待上一步返工完成


class TaskMessageType(str, PyEnum):
    """消息类型"""
    ASSIGNMENT = "assignment"     # 任务分配（第一条消息）
    REPLY = "reply"               # 员工回复
    FEEDBACK = "feedback"         # 发布者反馈/追问
    REWORK_NOTICE = "rework_notice"  # 返工通知（系统）
    PROGRESS = "progress"         # 进度更新
    SYSTEM = "system"             # 系统消息
    COMPLETION = "completion"     # 完成通知
    FAILURE = "failure"           # 失败通知


class TaskStep(Base):
    """任务步骤 - 聊天会话容器"""
    
    __tablename__ = "task_steps"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    
    # 步骤信息
    step_index = Column(Integer, nullable=False, default=0)
    step_name = Column(String, nullable=False, default="执行任务")
    step_description = Column(Text, default="")
    
    # 参与者
    assigner_id = Column(String, nullable=False)           # 分配者ID
    assigner_type = Column(String, nullable=False)         # "user" | "agent"
    assigner_name = Column(String, default="")
    executor_id = Column(String, ForeignKey("agents.id"), nullable=False, index=True)  # 执行员工
    
    # 状态
    status = Column(String, default=TaskStepStatus.PENDING.value)
    
    # 流转控制
    next_step_id = Column(String, ForeignKey("task_steps.id"), nullable=True)
    prev_step_id = Column(String, ForeignKey("task_steps.id"), nullable=True)
    rework_count = Column(Integer, default=0)
    max_rework = Column(Integer, default=3)
    
    # 输入输出
    input_context = Column(Text, default="")      # JSON字符串
    output_result = Column(Text, default="")      # JSON字符串
    
    # Token 预算和消耗
    budget_tokens = Column(Integer, default=1000)
    budget_estimated = Column(Boolean, default=True)
    actual_tokens = Column(Integer, default=0)
    cost_estimated = Column(Boolean, default=True)
    
    # 评价
    score = Column(Integer, nullable=True)        # 1-5分
    feedback = Column(Text, default="")
    settled = Column(Boolean, default=False)
    settled_at = Column(DateTime, nullable=True)
    settled_by = Column(String, nullable=True)    # 谁结算的
    
    # 时间戳
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    messages = relationship("TaskStepMessage", back_populates="step", order_by="TaskStepMessage.created_at")
    task = relationship("Task", back_populates="steps")
    executor = relationship("Agent", back_populates="task_steps")
    
    def to_dict(self, include_messages: bool = False) -> dict:
        """转换为字典"""
        import json
        
        result = {
            "id": self.id,
            "task_id": self.task_id,
            "step_index": self.step_index,
            "step_name": self.step_name,
            "step_description": self.step_description,
            "assigner_id": self.assigner_id,
            "assigner_type": self.assigner_type,
            "assigner_name": self.assigner_name,
            "executor_id": self.executor_id,
            "status": self.status,
            "next_step_id": self.next_step_id,
            "prev_step_id": self.prev_step_id,
            "rework_count": self.rework_count,
            "max_rework": self.max_rework,
            "input_context": json.loads(self.input_context) if self.input_context else {},
            "output_result": json.loads(self.output_result) if self.output_result else {},
            "budget_tokens": self.budget_tokens,
            "budget_estimated": self.budget_estimated,
            "actual_tokens": self.actual_tokens,
            "cost_estimated": self.cost_estimated,
            "score": self.score,
            "feedback": self.feedback,
            "settled": self.settled,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "settled_by": self.settled_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_messages:
            result["messages"] = [m.to_dict() for m in self.messages]
        
        return result


class TaskStepMessage(Base):
    """任务步骤消息 - 聊天记录"""
    
    __tablename__ = "task_step_messages"
    
    id = Column(String, primary_key=True)
    step_id = Column(String, ForeignKey("task_steps.id"), nullable=False, index=True)
    
    # 发送者
    sender_id = Column(String, nullable=False)
    sender_type = Column(String, nullable=False)      # "user" | "agent" | "system"
    sender_name = Column(String, default="")
    sender_avatar = Column(String, nullable=True)     # 头像URL
    
    # 内容
    content = Column(Text, nullable=False)
    message_type = Column(String, default=TaskMessageType.REPLY.value)
    
    # 附件（JSON字符串）
    attachments = Column(Text, default="[]")          # [{"type": "file", "name": "...", "path": "..."}]
    
    # 状态
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    step = relationship("TaskStep", back_populates="messages")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        import json
        
        return {
            "id": self.id,
            "step_id": self.step_id,
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "sender_name": self.sender_name,
            "sender_avatar": self.sender_avatar,
            "content": self.content,
            "message_type": self.message_type,
            "attachments": json.loads(self.attachments) if self.attachments else [],
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
