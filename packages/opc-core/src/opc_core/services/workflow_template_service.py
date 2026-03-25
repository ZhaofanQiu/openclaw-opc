"""
opc-core: 工作流模板服务 (v0.4.2-P2)

工作流模板业务逻辑层

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from opc_database.models import WorkflowTemplate, WorkflowTemplateRating
from opc_database.repositories import (
    WorkflowTemplateRatingRepository,
    WorkflowTemplateRepository,
)

from .workflow_service import WorkflowResult, WorkflowService, WorkflowStepConfig


@dataclass
class TemplateCreateRequest:
    """创建模板请求"""
    name: str
    description: Optional[str]
    steps_config: List[Dict[str, Any]]  # WorkflowStepConfig 字典列表
    category: str
    tags: List[str]
    created_by: str
    is_public: bool = False


@dataclass
class TemplateListResult:
    """模板列表结果"""
    templates: List[Dict[str, Any]]
    total: int
    categories: List[str]


class WorkflowTemplateService:
    """工作流模板服务
    
    提供模板的创建、查询、实例化、Fork、评分等功能
    """
    
    def __init__(
        self,
        template_repo: WorkflowTemplateRepository,
        rating_repo: WorkflowTemplateRatingRepository,
        workflow_service: WorkflowService,
    ):
        self.template_repo = template_repo
        self.rating_repo = rating_repo
        self.workflow_service = workflow_service
    
    # ========================================
    # 模板 CRUD
    # ========================================
    
    async def create_template(
        self,
        request: TemplateCreateRequest,
    ) -> WorkflowTemplate:
        """创建模板"""
        template = WorkflowTemplate(
            id=f"tmpl-{uuid.uuid4().hex[:8]}",
            name=request.name,
            description=request.description,
            steps_config="",  # 通过set_steps_config设置
            category=request.category,
            tags="",  # 通过set_tags设置
            usage_count=0,
            avg_rating=0.0,
            rating_count=0,
            version=1,
            parent_template_id=None,
            created_by=request.created_by,
            is_system=False,
            is_public=request.is_public,
        )
        
        # 设置JSON字段
        template.set_steps_config(request.steps_config)
        template.set_tags(request.tags)
        
        return await self.template_repo.create(template)
    
    async def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """获取模板详情"""
        return await self.template_repo.get_by_id(template_id)
    
    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any],
        user_id: str,
    ) -> Optional[WorkflowTemplate]:
        """更新模板（只有创建者可更新）"""
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return None
        
        # 权限检查
        if template.created_by != user_id and not template.is_system:
            raise PermissionError("Only creator can update template")
        
        # 更新字段
        if "name" in updates:
            template.name = updates["name"]
        if "description" in updates:
            template.description = updates["description"]
        if "category" in updates:
            template.category = updates["category"]
        if "tags" in updates:
            template.set_tags(updates["tags"])
        if "is_public" in updates:
            template.is_public = updates["is_public"]
        if "steps_config" in updates:
            template.set_steps_config(updates["steps_config"])
            template.version += 1  # 更新步骤时增加版本号
        
        template.updated_at = datetime.utcnow()
        return await self.template_repo.update(template)
    
    async def delete_template(self, template_id: str, user_id: str) -> bool:
        """删除模板（只有创建者可删除）"""
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            return False
        
        # 权限检查
        if template.created_by != user_id:
            raise PermissionError("Only creator can delete template")
        
        # 检查是否有Fork的子模板
        forks = await self.template_repo.get_forked_templates(template_id)
        if forks:
            # 可以设置标记删除而不是物理删除，或者级联删除
            pass
        
        await self.template_repo.delete(template)
        return True
    
    # ========================================
    # 模板查询
    # ========================================
    
    async def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        is_public: Optional[bool] = None,
        sort_by: str = "usage_count",
        include_system: bool = True,
    ) -> TemplateListResult:
        """获取模板列表"""
        templates = []
        
        if category:
            templates = await self.template_repo.get_by_category(category)
        elif tags:
            templates = await self.template_repo.get_by_tags(tags)
        elif is_public:
            templates = await self.template_repo.get_public_templates()
        elif user_id:
            templates = await self.template_repo.get_user_templates(user_id)
        else:
            # 获取所有（公开+系统+用户自己的）
            public_templates = await self.template_repo.get_public_templates()
            system_templates = await self.template_repo.get_system_templates() if include_system else []
            
            seen = set()
            templates = []
            for t in system_templates + public_templates:
                if t.id not in seen:
                    seen.add(t.id)
                    templates.append(t)
        
        # 排序
        if sort_by == "usage_count":
            templates.sort(key=lambda x: x.usage_count or 0, reverse=True)
        elif sort_by == "created_at":
            templates.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        elif sort_by == "rating":
            templates.sort(key=lambda x: x.avg_rating or 0, reverse=True)
        
        # 获取分类列表
        categories = await self.template_repo.get_categories()
        
        return TemplateListResult(
            templates=[t.to_dict() for t in templates],
            total=len(templates),
            categories=categories,
        )
    
    async def search_templates(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索模板"""
        templates = await self.template_repo.search(keyword, limit)
        return [t.to_dict() for t in templates]
    
    async def get_popular_templates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门模板"""
        templates = await self.template_repo.get_popular(limit)
        return [t.to_dict() for t in templates]
    
    async def get_top_rated_templates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取高评分模板"""
        templates = await self.template_repo.get_top_rated(limit)
        return [t.to_dict() for t in templates]
    
    async def get_categories_and_tags(self) -> Dict[str, List[str]]:
        """获取所有分类和标签"""
        categories = await self.template_repo.get_categories()
        tags = await self.template_repo.get_all_tags()
        return {
            "categories": categories,
            "tags": tags,
        }
    
    # ========================================
    # 模板实例化
    # ========================================
    
    async def create_workflow_from_template(
        self,
        template_id: str,
        initial_input: Dict[str, Any],
        created_by: str,
        workflow_name: Optional[str] = None,
        custom_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> WorkflowResult:
        """从模板创建工作流"""
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # 获取步骤配置
        steps_config = custom_steps or template.get_steps_config()
        
        # 转换为 WorkflowStepConfig
        steps = []
        for step_data in steps_config:
            steps.append(WorkflowStepConfig(
                employee_id=step_data["employee_id"],
                title=step_data["title"],
                description=step_data.get("description", ""),
                estimated_cost=step_data.get("estimated_cost", 0.0),
            ))
        
        # 创建工作流
        name = workflow_name or template.name
        result = await self.workflow_service.create_workflow(
            name=name,
            description=template.description,
            steps=steps,
            initial_input=initial_input,
            created_by=created_by,
        )
        
        # 更新模板使用统计
        template.increment_usage()
        await self.template_repo.update(template)
        
        return result
    
    # ========================================
    # Fork 功能
    # ========================================
    
    async def fork_template(
        self,
        template_id: str,
        new_name: str,
        created_by: str,
    ) -> WorkflowTemplate:
        """Fork模板"""
        parent = await self.template_repo.get_by_id(template_id)
        if not parent:
            raise ValueError(f"Parent template {template_id} not found")
        
        # 创建新模板，复制父模板内容
        forked = WorkflowTemplate(
            id=f"tmpl-{uuid.uuid4().hex[:8]}",
            name=new_name,
            description=parent.description,
            steps_config=parent.steps_config,  # 直接复制JSON
            category=parent.category,
            tags=parent.tags,
            usage_count=0,
            avg_rating=0.0,
            rating_count=0,
            version=1,
            parent_template_id=parent.id,
            created_by=created_by,
            is_system=False,
            is_public=False,  # Fork的模板默认私有
        )
        
        return await self.template_repo.create(forked)
    
    async def get_template_fork_history(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的Fork历史"""
        forks = await self.template_repo.get_forked_templates(template_id)
        return [f.to_dict() for f in forks]
    
    # ========================================
    # 评分功能
    # ========================================
    
    async def rate_template(
        self,
        template_id: str,
        user_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> None:
        """评分模板"""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        
        template = await self.template_repo.get_by_id(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # 检查用户是否已评分
        existing = await self.rating_repo.get_user_rating(template_id, user_id)
        
        if existing:
            # 更新评分
            existing.rating = rating
            existing.comment = comment
            await self.rating_repo.update(existing)
        else:
            # 创建新评分
            new_rating = WorkflowTemplateRating(
                id=f"rate-{uuid.uuid4().hex[:8]}",
                template_id=template_id,
                user_id=user_id,
                rating=rating,
                comment=comment,
            )
            await self.rating_repo.create(new_rating)
        
        # 重新计算平均评分
        stats = await self.rating_repo.get_rating_stats(template_id)
        template.avg_rating = stats["average"]
        template.rating_count = stats["count"]
        await self.template_repo.update(template)
    
    async def get_template_ratings(
        self,
        template_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """获取模板评分列表"""
        ratings = await self.rating_repo.get_by_template(template_id, limit, offset)
        stats = await self.rating_repo.get_rating_stats(template_id)
        
        return {
            "ratings": [r.to_dict() for r in ratings],
            "stats": stats,
            "limit": limit,
            "offset": offset,
        }
    
    async def get_user_rating(
        self,
        template_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取用户对模板的评分"""
        rating = await self.rating_repo.get_user_rating(template_id, user_id)
        return rating.to_dict() if rating else None
