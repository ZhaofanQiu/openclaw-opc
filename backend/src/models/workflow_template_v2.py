"""
Workflow Template Management v0.5.4

流程模板管理：
1. 创建/编辑/删除模板
2. 模板分类和标签
3. 模板版本控制
4. 团队共享模板
5. 模板使用统计
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, String, Text, JSON, Integer, ForeignKey
from sqlalchemy.orm import relationship

from src.database import Base


class TemplateCategory(str, PyEnum):
    """模板分类"""
    DEVELOPMENT = "development"      # 开发
    DESIGN = "design"                # 设计
    RESEARCH = "research"            # 研究
    DOCUMENTATION = "documentation"  # 文档
    MARKETING = "marketing"          # 市场
    CUSTOM = "custom"                # 自定义


class TemplateVisibility(str, PyEnum):
    """模板可见性"""
    PRIVATE = "private"      # 私有
    TEAM = "team"            # 团队内可见
    PUBLIC = "public"        # 公开


class WorkflowTemplateV2(Base):
    """工作流模板 v2 - 增强版"""
    
    __tablename__ = "workflow_templates_v2"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    
    # 分类和标签
    category = Column(String, default=TemplateCategory.CUSTOM.value)
    tags = Column(JSON, default=list)  # ["web", "api", "urgent"]
    
    # 可见性
    visibility = Column(String, default=TemplateVisibility.PRIVATE.value)
    team_id = Column(String, nullable=True)  # 团队ID（TEAM可见性时使用）
    
    # 步骤配置
    steps_config = Column(JSON, default=list)
    # {
    #   "steps": [
    #     {"step_id": "plan", "type": "PLAN", "name": "规划", ...},
    #     {"step_id": "execute", "type": "EXECUTE", "name": "开发", ...},
    #     ...
    #   ],
    #   "budget_allocation": [0.1, 0.5, 0.2, 0.2],
    #   "rework_budget_ratio": 0.2,
    # }
    
    # 预算默认配置
    default_budget_ratio = Column(JSON, default=dict)
    # {
    #   "rework_budget_ratio": 0.2,
    #   "default_rework_limit": 3,
    # }
    
    # 版本控制
    version = Column(Integer, default=1)
    parent_template_id = Column(String, nullable=True)  # 父模板ID（fork时使用）
    
    # 使用统计
    usage_count = Column(Integer, default=0)
    avg_completion_time = Column(Integer, default=0)  # 平均完成时间（分钟）
    avg_rework_count = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)  # 成功率（无熔断完成）
    
    # 评分
    rating = Column(Float, default=0.0)  # 1-5星
    rating_count = Column(Integer, default=0)
    
    # 创建者
    created_by = Column(String, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    creator = relationship("Agent")


class WorkflowTemplateFavorite(Base):
    """模板收藏"""
    
    __tablename__ = "workflow_template_favorites"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(String, ForeignKey("workflow_templates_v2.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 联合唯一
    __table_args__ = (
        # UniqueConstraint('template_id', 'agent_id', name='unique_favorite'),
    )


class WorkflowTemplateUsage(Base):
    """模板使用记录"""
    
    __tablename__ = "workflow_template_usage"
    
    id = Column(Integer, primary_key=True)
    template_id = Column(String, ForeignKey("workflow_templates_v2.id"), nullable=False)
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False)  # 使用者
    
    # 使用结果
    status = Column(String, default="in_progress")  # in_progress/completed/cancelled
    completion_time = Column(Integer, nullable=True)  # 完成用时（分钟）
    rework_count = Column(Integer, default=0)
    was_fused = Column(String, default="false")  # 是否熔断
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
