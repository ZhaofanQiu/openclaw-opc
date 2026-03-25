"""
opc-database: 工作流模板仓库 (v0.4.2-P2)

WorkflowTemplate 数据访问层

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

from typing import List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from ..models.workflow_template import WorkflowTemplate, WorkflowTemplateRating
from .base import BaseRepository


class WorkflowTemplateRepository(BaseRepository[WorkflowTemplate]):
    """工作流模板仓库"""
    
    model = WorkflowTemplate
    
    def __init__(self, session):
        super().__init__(session, WorkflowTemplate)
    
    async def get_by_category(self, category: str) -> List[WorkflowTemplate]:
        """按分类获取模板"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.category == category)
            .order_by(desc(self.model.usage_count))
        )
        return result.scalars().all()
    
    async def get_by_tags(self, tags: List[str]) -> List[WorkflowTemplate]:
        """按标签获取模板（包含任一标签）"""
        # 由于 tags 是 JSON 字符串，需要在应用层过滤
        result = await self.session.execute(select(self.model))
        templates = result.scalars().all()
        
        matching = []
        for template in templates:
            template_tags = template.get_tags()
            if any(tag in template_tags for tag in tags):
                matching.append(template)
        return matching
    
    async def get_public_templates(self, limit: int = 100) -> List[WorkflowTemplate]:
        """获取公开模板"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.is_public == True)
            .order_by(desc(self.model.usage_count))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_user_templates(self, user_id: str) -> List[WorkflowTemplate]:
        """获取用户创建的模板"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.created_by == user_id)
            .order_by(desc(self.model.created_at))
        )
        return result.scalars().all()
    
    async def get_system_templates(self) -> List[WorkflowTemplate]:
        """获取系统预设模板"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.is_system == True)
            .order_by(self.model.category, desc(self.model.usage_count))
        )
        return result.scalars().all()
    
    async def search(self, keyword: str, limit: int = 50) -> List[WorkflowTemplate]:
        """搜索模板（名称、描述、标签）"""
        # 名称和描述搜索
        result = await self.session.execute(
            select(self.model)
            .where(
                (self.model.name.ilike(f"%{keyword}%")) |
                (self.model.description.ilike(f"%{keyword}%"))
            )
            .limit(limit)
        )
        name_matches = result.scalars().all()
        
        # 标签搜索（在应用层过滤）
        result = await self.session.execute(select(self.model))
        all_templates = result.scalars().all()
        
        tag_matches = [
            t for t in all_templates
            if keyword.lower() in [tag.lower() for tag in t.get_tags()]
        ]
        
        # 合并去重
        seen = set()
        combined = []
        for t in name_matches + tag_matches:
            if t.id not in seen:
                seen.add(t.id)
                combined.append(t)
        
        return combined[:limit]
    
    async def get_popular(self, limit: int = 10) -> List[WorkflowTemplate]:
        """获取热门模板（按使用次数）"""
        result = await self.session.execute(
            select(self.model)
            .order_by(desc(self.model.usage_count))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_top_rated(self, limit: int = 10) -> List[WorkflowTemplate]:
        """获取高评分模板"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.rating_count >= 3)  # 至少3个评分
            .order_by(desc(self.model.avg_rating))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_categories(self) -> List[str]:
        """获取所有分类"""
        result = await self.session.execute(
            select(self.model.category).distinct()
        )
        return [r[0] for r in result.all()]
    
    async def get_all_tags(self) -> List[str]:
        """获取所有标签（去重）"""
        result = await self.session.execute(select(self.model.tags))
        all_tags = set()
        for row in result.all():
            if row[0]:
                tags = WorkflowTemplate(tags=row[0]).get_tags()
                all_tags.update(tags)
        return sorted(list(all_tags))
    
    async def get_forked_templates(self, parent_id: str) -> List[WorkflowTemplate]:
        """获取从指定模板Fork的所有模板"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.parent_template_id == parent_id)
        )
        return result.scalars().all()


class WorkflowTemplateRatingRepository(BaseRepository[WorkflowTemplateRating]):
    """模板评分仓库"""
    
    model = WorkflowTemplateRating
    
    def __init__(self, session):
        super().__init__(session, WorkflowTemplateRating)
    
    async def get_by_template(
        self, 
        template_id: str, 
        limit: int = 50,
        offset: int = 0
    ) -> List[WorkflowTemplateRating]:
        """获取模板的评分列表"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.template_id == template_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def get_by_user(self, user_id: str) -> List[WorkflowTemplateRating]:
        """获取用户的所有评分"""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(desc(self.model.created_at))
        )
        return result.scalars().all()
    
    async def get_user_rating(
        self, 
        template_id: str, 
        user_id: str
    ) -> Optional[WorkflowTemplateRating]:
        """获取用户对特定模板的评分"""
        result = await self.session.execute(
            select(self.model)
            .where(
                (self.model.template_id == template_id) &
                (self.model.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_rating_stats(self, template_id: str) -> dict:
        """获取评分统计"""
        result = await self.session.execute(
            select(
                func.count(self.model.id).label("count"),
                func.avg(self.model.rating).label("average")
            )
            .where(self.model.template_id == template_id)
        )
        row = result.one()
        return {
            "count": row.count or 0,
            "average": round(row.average, 1) if row.average else 0.0,
        }
