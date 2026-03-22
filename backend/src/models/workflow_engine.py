"""
Workflow Engine v0.5.1 - 并行执行与返工预算

核心改进：
1. 支持并行步骤（如前端+后端同时开发）
2. 返工预算机制：总预算中预留返工预算池
3. 双熔断：返工预算耗尽 + 返工次数超限
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from src.database import Base


class StepType(str, PyEnum):
    """工作流步骤类型"""
    PLAN = "plan"           # 规划
    EXECUTE = "execute"     # 执行（可并行）
    REVIEW = "review"       # 评审
    APPROVE = "approve"     # 审批
    TEST = "test"           # 测试
    VERIFY = "verify"       # 验证
    DELIVER = "deliver"     # 交付
    PARALLEL = "parallel"   # 并行容器（新）
    MERGE = "merge"         # 合并点（新）


class WorkflowStatus(str, PyEnum):
    """工作流实例状态"""
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REWORK = "rework"
    BUDGET_FUSED = "budget_fused"  # 返工预算熔断
    REWORK_FUSED = "rework_fused"  # 返工次数熔断
    WARNING = "warning"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StepStatus(str, PyEnum):
    """步骤实例状态"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"     # 等待并行步骤完成
    COMPLETED = "completed"
    REWORK = "rework"
    SKIPPED = "skipped"


class WorkflowTemplate(Base):
    """工作流模板"""
    
    __tablename__ = "workflow_templates"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="general")
    
    # 步骤定义（支持并行）
    # 示例：
    # [
    #   {"step_id": "plan", "type": "PLAN", "name": "规划", ...},
    #   {"step_id": "dev_parallel", "type": "PARALLEL", "name": "并行开发", 
    #    "parallel_steps": [
    #      {"step_id": "frontend", "type": "EXECUTE", "name": "前端开发", ...},
    #      {"step_id": "backend", "type": "EXECUTE", "name": "后端开发", ...}
    #    ],
    #    "merge_condition": "ALL"  # ALL=全部完成, ANY=任一完成
    #   },
    #   {"step_id": "merge", "type": "MERGE", "name": "合并"},
    #   {"step_id": "review", "type": "REVIEW", "name": "评审", ...},
    #   ...
    # ]
    steps_config = Column(JSON, default=list)
    
    # 预算分配比例
    budget_allocation = Column(JSON, default=list)
    
    # 返工预算比例（默认20%）
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
    current_step_ids = Column(JSON, default=list)  # 当前活跃的步骤ID列表（支持并行）
    
    # ===== 预算系统 =====
    # 主预算
    total_budget = Column(Float, default=0.0)
    base_budget = Column(Float, default=0.0)      # 基础执行预算
    rework_budget = Column(Float, default=0.0)    # 返工预算池
    
    # 预算使用
    used_base_budget = Column(Float, default=0.0)
    used_rework_budget = Column(Float, default=0.0)
    remaining_budget = Column(Float, default=0.0)
    
    # 返工熔断阈值
    rework_budget_threshold = Column(Float, default=0.1)  # 返工预算低于10%熔断
    
    created_by = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # 规划结果
    plan_result = Column(JSON, default=dict)
    
    # 上下文
    context = Column(JSON, default=dict)
    
    # 统计
    total_rework_count = Column(Integer, default=0)
    total_rework_cost = Column(Float, default=0.0)  # 总返工消耗
    
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
    
    # 并行相关
    parent_step_id = Column(String, nullable=True)  # 父步骤ID（PARALLEL类型）
    is_parallel = Column(String, default="false")   # 是否是并行步骤
    parallel_group = Column(String, nullable=True)  # 并行组标识
    merge_condition = Column(String, default="ALL") # ALL/ANY
    
    assignee_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    status = Column(String, default=StepStatus.PENDING.value)
    
    # 预算（不含返工）
    base_budget = Column(Float, default=0.0)      # 基础预算
    rework_reserve = Column(Float, default=0.0)   # 该步骤的返工储备
    used_budget = Column(Float, default=0.0)      # 已使用
    
    # 返工消耗追踪
    rework_cost = Column(Float, default=0.0)      # 该步骤返工总消耗
    
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
    parent_step = relationship("WorkflowStep", remote_side=[id], foreign_keys=[parent_step_id])


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
    
    budget_impact = Column(JSON, default=dict)  # 预算变动
    # {"type": "base|rework", "amount": 100, "remaining_rework_budget": 500}
    
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
    
    # 返工成本
    cost = Column(Float, default=0.0)  # 本次返工消耗
    rework_budget_before = Column(Float, default=0.0)
    rework_budget_after = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
