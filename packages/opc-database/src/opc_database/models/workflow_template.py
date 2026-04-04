"""
opc-database: 工作流模板模型 (v0.4.2-P2)

工作流模板数据模型，支持保存、复用、Fork、评分

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class WorkflowTemplate(Base):
    """工作流模板
    
    存储可复用的工作流配置，支持版本控制和Fork
    """
    
    __tablename__ = "workflow_templates"
    
    # ========================================
    # 基础字段
    # ========================================
    id: Mapped[str] = mapped_column(
        String(32), 
        primary_key=True,
        comment="模板ID: tmpl-xxx"
    )
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        comment="模板名称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="模板描述"
    )
    
    # ========================================
    # 模板内容 (JSON存储步骤配置)
    # ========================================
    steps_config: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="步骤配置JSON，WorkflowStepConfig数组"
    )
    
    # ========================================
    # 分类和标签
    # ========================================
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        comment="分类: research/writing/review/code/general"
    )
    tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="标签JSON数组，如['AI', '医疗', '报告']"
    )
    
    # ========================================
    # 使用统计
    # ========================================
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="使用次数"
    )
    avg_rating: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="平均评分 0-5"
    )
    rating_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="评分次数"
    )
    
    # ========================================
    # 版本控制
    # ========================================
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="版本号"
    )
    parent_template_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("workflow_templates.id"),
        nullable=True,
        comment="父模板ID（Fork来源）"
    )
    
    # ========================================
    # 权限控制
    # ========================================
    created_by: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="创建者用户ID"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否系统预设模板"
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否公开模板"
    )
    
    # ========================================
    # 时间戳
    # ========================================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="最后使用时间"
    )
    
    # ========================================
    # 关系
    # ========================================
    ratings: Mapped[List["WorkflowTemplateRating"]] = relationship(
        "WorkflowTemplateRating",
        back_populates="template",
        cascade="all, delete-orphan"
    )
    
    # Fork关系
    parent_template: Mapped[Optional["WorkflowTemplate"]] = relationship(
        "WorkflowTemplate",
        remote_side=[id],
        back_populates="forks"
    )
    forks: Mapped[List["WorkflowTemplate"]] = relationship(
        "WorkflowTemplate",
        back_populates="parent_template"
    )
    
    # ========================================
    # 便捷方法
    # ========================================
    def get_steps_config(self) -> List[Dict[str, Any]]:
        """获取步骤配置"""
        return json.loads(self.steps_config) if self.steps_config else []
    
    def set_steps_config(self, steps: List[Dict[str, Any]]) -> None:
        """设置步骤配置"""
        self.steps_config = json.dumps(steps, ensure_ascii=False)
    
    def get_tags(self) -> List[str]:
        """获取标签列表"""
        return json.loads(self.tags) if self.tags else []
    
    def set_tags(self, tags: List[str]) -> None:
        """设置标签"""
        self.tags = json.dumps(tags, ensure_ascii=False)
    
    def increment_usage(self) -> None:
        """增加使用次数"""
        if self.usage_count is None:
            self.usage_count = 0
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
    
    def update_rating(self, new_rating: float) -> None:
        """更新评分（添加新评分后的平均值）"""
        total_score = self.avg_rating * self.rating_count + new_rating
        self.rating_count += 1
        self.avg_rating = total_score / self.rating_count
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps_config": self.get_steps_config(),
            "category": self.category,
            "tags": self.get_tags(),
            "usage_count": self.usage_count,
            "avg_rating": round(self.avg_rating, 1) if self.avg_rating is not None else 0.0,
            "rating_count": self.rating_count,
            "version": self.version,
            "parent_template_id": self.parent_template_id,
            "created_by": self.created_by,
            "is_system": self.is_system,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class WorkflowTemplateRating(Base):
    """模板评分
    
    用户对模板的评分和评论
    """
    
    __tablename__ = "workflow_template_ratings"
    
    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        comment="评分ID: rate-xxx"
    )
    template_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("workflow_templates.id"),
        nullable=False,
        comment="模板ID"
    )
    user_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="评分用户ID"
    )
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="评分 1-5星"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="评论内容"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="评分时间"
    )
    
    # ========================================
    # 关系
    # ========================================
    template: Mapped["WorkflowTemplate"] = relationship(
        "WorkflowTemplate",
        back_populates="ratings"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
