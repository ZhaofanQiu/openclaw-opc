"""
Workflow Template Service v0.5.4

模板管理服务
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Agent
from models.workflow_template_v2 import (
    WorkflowTemplateV2, WorkflowTemplateFavorite, WorkflowTemplateUsage,
    TemplateCategory, TemplateVisibility
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowTemplateService:
    """工作流模板服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== CRUD ==========
    
    def create_template(
        self,
        name: str,
        description: str,
        category: str,
        steps_config: List[Dict],
        budget_config: Dict,
        created_by: str,
        tags: List[str] = None,
        visibility: str = "private",
        team_id: str = None,
    ) -> WorkflowTemplateV2:
        """创建模板"""
        template = WorkflowTemplateV2(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            visibility=visibility,
            team_id=team_id,
            steps_config={
                "steps": steps_config,
                "budget_allocation": budget_config.get("allocation", []),
                "rework_budget_ratio": budget_config.get("rework_ratio", 0.2),
            },
            default_budget_ratio=budget_config,
            created_by=created_by,
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        logger.info("template_created", template_id=template.id, name=name)
        return template
    
    def get_template(self, template_id: str, agent_id: str = None) -> Optional[WorkflowTemplateV2]:
        """获取模板（检查权限）"""
        template = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        
        if not template:
            return None
        
        # 检查权限
        if template.visibility == TemplateVisibility.PRIVATE.value:
            if template.created_by != agent_id:
                return None
        
        return template
    
    def update_template(
        self,
        template_id: str,
        agent_id: str,
        updates: Dict,
    ) -> WorkflowTemplateV2:
        """更新模板（创建新版本）"""
        template = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        
        if not template:
            raise ValueError("Template not found")
        
        if template.created_by != agent_id:
            raise ValueError("Only creator can update template")
        
        # 更新字段
        for field in ["name", "description", "category", "tags", "visibility"]:
            if field in updates:
                setattr(template, field, updates[field])
        
        if "steps_config" in updates:
            template.steps_config["steps"] = updates["steps_config"]
        
        if "budget_config" in updates:
            template.steps_config["rework_budget_ratio"] = updates["budget_config"].get("rework_ratio", 0.2)
            template.default_budget_ratio = updates["budget_config"]
        
        template.version += 1
        template.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(template)
        
        logger.info("template_updated", template_id=template_id, version=template.version)
        return template
    
    def delete_template(self, template_id: str, agent_id: str) -> bool:
        """删除模板"""
        template = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        
        if not template:
            return False
        
        if template.created_by != agent_id:
            raise ValueError("Only creator can delete template")
        
        self.db.delete(template)
        self.db.commit()
        
        logger.info("template_deleted", template_id=template_id)
        return True
    
    def fork_template(
        self,
        template_id: str,
        new_name: str,
        agent_id: str,
    ) -> WorkflowTemplateV2:
        """Fork模板"""
        source = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        
        if not source:
            raise ValueError("Source template not found")
        
        # 创建新模板
        new_template = WorkflowTemplateV2(
            id=str(uuid.uuid4())[:8],
            name=new_name,
            description=source.description,
            category=source.category,
            tags=source.tags.copy(),
            visibility=TemplateVisibility.PRIVATE.value,
            steps_config=source.steps_config.copy(),
            default_budget_ratio=source.default_budget_ratio.copy(),
            parent_template_id=template_id,
            created_by=agent_id,
        )
        self.db.add(new_template)
        self.db.commit()
        self.db.refresh(new_template)
        
        logger.info("template_forked", from_id=template_id, to_id=new_template.id)
        return new_template
    
    # ========== 查询 ==========
    
    def list_templates(
        self,
        agent_id: str,
        category: str = None,
        tags: List[str] = None,
        visibility: str = None,
        sort_by: str = "usage",  # usage/rating/created
        limit: int = 20,
        offset: int = 0,
    ) -> Dict:
        """列出模板"""
        query = self.db.query(WorkflowTemplateV2)
        
        # 权限过滤
        query = query.filter(
            (WorkflowTemplateV2.visibility == TemplateVisibility.PUBLIC.value) |
            (WorkflowTemplateV2.created_by == agent_id) |
            (
                (WorkflowTemplateV2.visibility == TemplateVisibility.TEAM.value) &
                (WorkflowTemplateV2.team_id == self._get_agent_team_id(agent_id))
            )
        )
        
        # 分类过滤
        if category:
            query = query.filter(WorkflowTemplateV2.category == category)
        
        # 标签过滤
        if tags:
            for tag in tags:
                query = query.filter(WorkflowTemplateV2.tags.contains([tag]))
        
        # 可见性过滤
        if visibility:
            query = query.filter(WorkflowTemplateV2.visibility == visibility)
        
        # 排序
        if sort_by == "usage":
            query = query.order_by(WorkflowTemplateV2.usage_count.desc())
        elif sort_by == "rating":
            query = query.order_by(WorkflowTemplateV2.rating.desc())
        elif sort_by == "created":
            query = query.order_by(WorkflowTemplateV2.created_at.desc())
        
        total = query.count()
        templates = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "templates": [self._format_template_summary(t) for t in templates],
        }
    
    def get_my_templates(self, agent_id: str) -> List[Dict]:
        """获取我创建的模板"""
        templates = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.created_by == agent_id
        ).order_by(WorkflowTemplateV2.updated_at.desc()).all()
        
        return [self._format_template_detail(t) for t in templates]
    
    def get_favorite_templates(self, agent_id: str) -> List[Dict]:
        """获取收藏的模板"""
        favorites = self.db.query(WorkflowTemplateFavorite).filter(
            WorkflowTemplateFavorite.agent_id == agent_id
        ).all()
        
        template_ids = [f.template_id for f in favorites]
        templates = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id.in_(template_ids)
        ).all()
        
        return [self._format_template_summary(t) for t in templates]
    
    def get_popular_templates(self, category: str = None, limit: int = 10) -> List[Dict]:
        """获取热门模板"""
        query = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.visibility == TemplateVisibility.PUBLIC.value
        )
        
        if category:
            query = query.filter(WorkflowTemplateV2.category == category)
        
        templates = query.order_by(
            WorkflowTemplateV2.usage_count.desc(),
            WorkflowTemplateV2.rating.desc()
        ).limit(limit).all()
        
        return [self._format_template_summary(t) for t in templates]
    
    # ========== 收藏 ==========
    
    def add_favorite(self, template_id: str, agent_id: str) -> bool:
        """收藏模板"""
        # 检查是否已收藏
        existing = self.db.query(WorkflowTemplateFavorite).filter(
            WorkflowTemplateFavorite.template_id == template_id,
            WorkflowTemplateFavorite.agent_id == agent_id
        ).first()
        
        if existing:
            return True
        
        favorite = WorkflowTemplateFavorite(
            template_id=template_id,
            agent_id=agent_id,
        )
        self.db.add(favorite)
        self.db.commit()
        return True
    
    def remove_favorite(self, template_id: str, agent_id: str) -> bool:
        """取消收藏"""
        self.db.query(WorkflowTemplateFavorite).filter(
            WorkflowTemplateFavorite.template_id == template_id,
            WorkflowTemplateFavorite.agent_id == agent_id
        ).delete()
        self.db.commit()
        return True
    
    # ========== 评分 ==========
    
    def rate_template(self, template_id: str, agent_id: str, rating: int) -> float:
        """给模板评分"""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        template = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        
        if not template:
            raise ValueError("Template not found")
        
        # 更新平均评分
        new_count = template.rating_count + 1
        new_rating = (template.rating * template.rating_count + rating) / new_count
        
        template.rating = round(new_rating, 2)
        template.rating_count = new_count
        
        self.db.commit()
        return template.rating
    
    # ========== 使用统计 ==========
    
    def record_usage(
        self,
        template_id: str,
        workflow_id: str,
        agent_id: str,
    ) -> WorkflowTemplateUsage:
        """记录模板使用"""
        usage = WorkflowTemplateUsage(
            template_id=template_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
        )
        self.db.add(usage)
        
        # 增加使用计数
        template = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        if template:
            template.usage_count += 1
        
        self.db.commit()
        return usage
    
    def update_usage_result(
        self,
        template_id: str,
        workflow_id: str,
        status: str,
        completion_time: int = None,
        rework_count: int = 0,
        was_fused: bool = False,
    ):
        """更新使用结果"""
        usage = self.db.query(WorkflowTemplateUsage).filter(
            WorkflowTemplateUsage.template_id == template_id,
            WorkflowTemplateUsage.workflow_id == workflow_id
        ).first()
        
        if not usage:
            return
        
        usage.status = status
        usage.completion_time = completion_time
        usage.rework_count = rework_count
        usage.was_fused = "true" if was_fused else "false"
        usage.completed_at = datetime.utcnow()
        
        # 更新模板统计
        template = self.db.query(WorkflowTemplateV2).filter(
            WorkflowTemplateV2.id == template_id
        ).first()
        
        if template and status == "completed":
            # 更新平均完成时间
            completed_usages = self.db.query(WorkflowTemplateUsage).filter(
                WorkflowTemplateUsage.template_id == template_id,
                WorkflowTemplateUsage.status == "completed",
                WorkflowTemplateUsage.completion_time.isnot(None)
            ).all()
            
            if completed_usages:
                avg_time = sum(u.completion_time for u in completed_usages) / len(completed_usages)
                template.avg_completion_time = int(avg_time)
            
            # 更新平均返工次数
            template.avg_rework_count = (
                template.avg_rework_count * (template.usage_count - 1) + rework_count
            ) / template.usage_count
            
            # 更新成功率
            completed = self.db.query(WorkflowTemplateUsage).filter(
                WorkflowTemplateUsage.template_id == template_id,
                WorkflowTemplateUsage.status == "completed"
            ).count()
            
            not_fused = self.db.query(WorkflowTemplateUsage).filter(
                WorkflowTemplateUsage.template_id == template_id,
                WorkflowTemplateUsage.status == "completed",
                WorkflowTemplateUsage.was_fused == "false"
            ).count()
            
            if completed > 0:
                template.success_rate = round(not_fused / completed * 100, 2)
        
        self.db.commit()
    
    # ========== 辅助方法 ==========
    
    def _get_agent_team_id(self, agent_id: str) -> Optional[str]:
        """获取员工团队ID"""
        # 简化实现，实际应该从Agent模型获取
        return None
    
    def _format_template_summary(self, template: WorkflowTemplateV2) -> Dict:
        """格式化模板摘要"""
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "tags": template.tags,
            "visibility": template.visibility,
            "version": template.version,
            "usage_count": template.usage_count,
            "rating": template.rating,
            "rating_count": template.rating_count,
            "success_rate": template.success_rate,
            "created_by": template.created_by,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }
    
    def _format_template_detail(self, template: WorkflowTemplateV2) -> Dict:
        """格式化模板详情"""
        return {
            **self._format_template_summary(template),
            "steps_config": template.steps_config,
            "default_budget_ratio": template.default_budget_ratio,
            "avg_completion_time": template.avg_completion_time,
            "avg_rework_count": template.avg_rework_count,
            "created_at": template.created_at.isoformat() if template.created_at else None,
        }
