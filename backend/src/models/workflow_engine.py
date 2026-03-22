"""
Workflow Engine models for v0.5.0

统一工作流引擎：支持多步骤类型、自动返工、多维度评分、预算分解
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from src.database import Base


class StepType(str, PyEnum):
    """工作流步骤类型"""
    PLAN = "plan"           # 规划：分析需求，制定方案
    EXECUTE = "execute"     # 执行：实际完成工作
    REVIEW = "review"       # 评审：对工作成果进行评分
    APPROVE = "approve"     # 审批：预算/方案审批
    TEST = "test"           # 测试：验证功能/质量
    VERIFY = "verify"       # 验证：最终确认
    DELIVER = "deliver"     # 交付：交给用户


class WorkflowStatus(str, PyEnum):
    """工作流实例状态"""
    PENDING = "pending"         # 待启动
    PLANNING = "planning"       # Partner规划中
    IN_PROGRESS = "in_progress" # 进行中
    REWORK = "rework"           # 返工中
    WARNING = "warning"         # 预警状态（返工超上限）
    COMPLETED = "completed"     # 已完成
    CANCELLED = "cancelled"     # 已取消


class StepStatus(str, PyEnum):
    """步骤实例状态"""
    PENDING = "pending"         # 待分配
    ASSIGNED = "assigned"       # 已分配
    IN_PROGRESS = "in_progress" # 进行中
    COMPLETED = "completed"     # 已完成
    REWORK = "rework"           # 返工中


class WorkflowTemplate(Base):
    """工作流模板 - 预定义的流程配置"""
    
    __tablename__ = "workflow_templates"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="general")  # general/dev/design/research
    
    # 步骤定义 (JSON数组)
    steps_config = Column(JSON, default=list)
    # 示例：
    # [
    #   {"step_id": "plan", "type": "PLAN", "name": "需求规划", "estimated_hours": 2, ...},
    #   {"step_id": "execute", "type": "EXECUTE", "name": "开发实现", ...},
    #   {"step_id": "review", "type": "REVIEW", "name": "代码评审", "review_criteria": [...]},
    #   {"step_id": "deliver", "type": "DELIVER", "name": "交付用户", ...}
    # ]
    
    # 预算分配比例 (按步骤顺序)
    budget_allocation = Column(JSON, default=list)  # [0.1, 0.5, 0.2, 0.2]
    
    # 默认返工上限
    default_rework_limit = Column(Integer, default=3)
    
    # 是否启用
    is_active = Column(String, default="true")
    
    # 创建者 (通常是Partner)
    created_by = Column(String, ForeignKey("agents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowInstance(Base):
    """工作流实例 - 实际运行的流程"""
    
    __tablename__ = "workflow_instances"
    
    id = Column(String, primary_key=True)
    
    # 关联模板
    template_id = Column(String, ForeignKey("workflow_templates.id"), nullable=True)
    
    # 任务信息
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    
    # 状态
    status = Column(String, default=WorkflowStatus.PENDING.value)
    current_step_index = Column(Integer, default=-1)  # 当前步骤索引，-1表示未开始
    
    # 预算
    total_budget = Column(Float, default=0.0)       # 总预算
    used_budget = Column(Float, default=0.0)        # 已使用预算
    remaining_budget = Column(Float, default=0.0)   # 剩余预算
    
    # 创建者
    created_by = Column(String, ForeignKey("agents.id"), nullable=False)  # 通常是Partner
    
    # 规划结果 (Partner生成的规划)
    plan_result = Column(JSON, default=dict)
    # {
    #   "analysis": "需求分析...",
    #   "selected_steps": ["plan", "execute", "review", "deliver"],
    #   "step_plans": {
    #     "plan": {"agent_id": "...", "budget": 100, "estimated_hours": 2, "handbook": "..."},
    #     "execute": {...},
    #     ...
    #   },
    #   "handbook": "完整任务手册..."
    # }
    
    # 上下文数据
    context = Column(JSON, default=dict)
    
    # 返工统计
    total_rework_count = Column(Integer, default=0)  # 总返工次数
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    template = relationship("WorkflowTemplate")
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    creator = relationship("Agent", foreign_keys=[created_by])


class WorkflowStep(Base):
    """工作流步骤实例 - 流程中的单个步骤"""
    
    __tablename__ = "workflow_steps"
    
    id = Column(String, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    
    # 步骤定义
    step_id = Column(String, nullable=False)  # 如 "execute"
    step_type = Column(String, nullable=False)  # PLAN/EXECUTE/REVIEW/...
    name = Column(String, nullable=False)
    sequence = Column(Integer, nullable=False)  # 步骤序号
    
    # 分配
    assignee_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # 状态
    status = Column(String, default=StepStatus.PENDING.value)
    
    # 预算
    allocated_budget = Column(Float, default=0.0)  # 分配预算
    used_budget = Column(Float, default=0.0)       # 已使用
    
    # 工时估计
    estimated_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    
    # 任务手册 (Partner为该步骤生成的指导)
    handbook = Column(Text, default="")
    
    # 结果数据
    result = Column(JSON, default=dict)
    # {
    #   "action": "PASS|REJECT|REWORK",
    #   "comment": "完成评语",
    #   "artifacts": ["链接1", "链接2"],
    #   "output": "步骤产出内容"
    # }
    
    # 评审评分 (仅REVIEW类型)
    review_scores = Column(JSON, default=dict)
    # {
    #   "quality": 90,
    #   "performance": 85,
    #   "security": 88,
    #   "maintainability": 82
    # }
    
    # 返工信息
    is_rework = Column(String, default="false")  # 是否返工步骤
    rework_from_step_id = Column(String, nullable=True)  # 从哪步返工而来
    rework_count = Column(Integer, default=0)  # 本步骤返工次数
    rework_limit = Column(Integer, default=3)  # 返工上限
    
    # 时间戳
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    workflow = relationship("WorkflowInstance", back_populates="steps")
    assignee = relationship("Agent", foreign_keys=[assignee_id])


class WorkflowHistory(Base):
    """工作流历史记录"""
    
    __tablename__ = "workflow_history"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    step_id = Column(String, nullable=True)
    
    action = Column(String, nullable=False)  # START_STEP/COMPLETE_STEP/REWORK/ASSIGN/...
    actor_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    
    details = Column(JSON, default=dict)  # 动作详情
    comment = Column(Text, default="")
    
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowReworkRecord(Base):
    """返工记录 - 详细记录每次返工"""
    
    __tablename__ = "workflow_rework_records"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    
    from_step_id = Column(String, nullable=False)  # 从哪步返工
    to_step_id = Column(String, nullable=False)    # 返工到哪步
    
    triggered_by = Column(String, ForeignKey("agents.id"), nullable=True)  # 谁触发的
    reason = Column(Text, default="")  # 返工原因
    review_scores = Column(JSON, default=dict)  # 当时的评分
    
    created_at = Column(DateTime, default=datetime.utcnow)
