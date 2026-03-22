"""
Workflow Engine v0.5.2 - 纯串行执行

核心设计：
1. 所有步骤严格串行执行
2. 复杂任务的"并行"拆解为多个串行子流程
3. 简化模型，专注返工预算机制
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from src.database import Base


class StepType(str, PyEnum):
    """工作流步骤类型"""
    PLAN = "plan"           # 规划
    EXECUTE = "execute"     # 执行
    REVIEW = "review"       # 评审
    APPROVE = "approve"     # 审批
    TEST = "test"           # 测试
    VERIFY = "verify"       # 验证
    DELIVER = "deliver"     # 交付


class WorkflowStatus(str, PyEnum):
    """工作流实例状态"""
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REWORK = "rework"
    BUDGET_FUSED = "budget_fused"  # 返工预算熔断
    REWORK_FUSED = "rework_fused"  # 返工次数熔断
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StepStatus(str, PyEnum):
    """步骤实例状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REWORK = "rework"


class WorkflowTemplate(Base):
    """工作流模板"""
    
    __tablename__ = "workflow_templates"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="general")
    
    # 步骤定义（纯串行）
    steps_config = Column(JSON, default=list)
    
    # 预算分配比例
    budget_allocation = Column(JSON, default=list)
    
    # 返工预算比例
    rework_budget_ratio = Column(Float, default=0.2)
    
    # 默认返工上限
    default_rework_limit = Column(Integer, default=3)
    
    is_active = Column(String, default="true")
    created_by = Column(String, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowInstance(Base):
    """工作流实例"""
    
    __tablename__ = "workflow_instances"
    
    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("workflow_templates.id"), nullable=True)
    
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    
    status = Column(String, default=WorkflowStatus.PENDING.value)
    current_step_index = Column(Integer, default=-1)  # 当前步骤序号
    
    # ===== 预算系统 =====
    total_budget = Column(Float, default=0.0)
    base_budget = Column(Float, default=0.0)
    rework_budget = Column(Float, default=0.0)
    
    used_base_budget = Column(Float, default=0.0)
    used_rework_budget = Column(Float, default=0.0)
    remaining_budget = Column(Float, default=0.0)
    
    rework_budget_threshold = Column(Float, default=0.1)
    
    created_by = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # 规划结果
    plan_result = Column(JSON, default=dict)
    
    # 上下文
    context = Column(JSON, default=dict)
    
    # 统计
    total_rework_count = Column(Integer, default=0)
    total_rework_cost = Column(Float, default=0.0)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    template = relationship("WorkflowTemplate")
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    creator = relationship("Agent", foreign_keys=[created_by])


class WorkflowStep(Base):
    """工作流步骤实例"""
    
    __tablename__ = "workflow_steps"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    
    step_id = Column(String, nullable=False)
    step_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)
    
    assignee_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    status = Column(String, default=StepStatus.PENDING.value)
    
    # 预算
    base_budget = Column(Float, default=0.0)
    rework_reserve = Column(Float, default=0.0)
    used_budget = Column(Float, default=0.0)
    rework_cost = Column(Float, default=0.0)
    
    estimated_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    
    handbook = Column(Text, default="")
    
    result = Column(JSON, default=dict)
    review_scores = Column(JSON, default=dict)
    
    # 返工信息
    is_rework = Column(String, default="false")
    rework_from_step_id = Column(String, nullable=True)
    rework_count = Column(Integer, default=0)
    rework_limit = Column(Integer, default=3)
    
    # 时间戳
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    workflow = relationship("WorkflowInstance", back_populates="steps")
    assignee = relationship("Agent", foreign_keys=[assignee_id])


class WorkflowHistory(Base):
    """工作流历史"""
    
    __tablename__ = "workflow_history"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    step_id = Column(String, nullable=True)
    
    action = Column(String, nullable=False)
    actor_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    
    details = Column(JSON, default=dict)
    comment = Column(Text, default="")
    budget_impact = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowReworkRecord(Base):
    """返工记录"""
    
    __tablename__ = "workflow_rework_records"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    
    from_step_id = Column(String, nullable=False)
    to_step_id = Column(String, nullable=False)
    
    triggered_by = Column(String, ForeignKey("agents.id"), nullable=True)
    reason = Column(Text, default="")
    review_scores = Column(JSON, default=dict)
    
    cost = Column(Float, default=0.0)
    rework_budget_before = Column(Float, default=0.0)
    rework_budget_after = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
