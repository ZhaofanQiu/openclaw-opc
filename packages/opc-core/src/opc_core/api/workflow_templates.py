"""
opc-core: 工作流模板 API (v0.4.2-P2)

工作流模板 REST API 路由

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from opc_database import get_session
from opc_database.repositories import (
    EmployeeRepository,
    TaskRepository,
    WorkflowTemplateRatingRepository,
    WorkflowTemplateRepository,
)

from ..services import (
    TemplateCreateRequest,
    WorkflowService,
    WorkflowTemplateService,
)

router = APIRouter(prefix="/workflow-templates", tags=["workflow-templates"])


# ========================================
# Pydantic 模型
# ========================================

class TemplateCreateSchema(BaseModel):
    """创建模板请求"""
    name: str
    description: Optional[str] = None
    steps_config: List[dict]
    category: str = "general"
    tags: List[str] = []
    is_public: bool = False


class TemplateUpdateSchema(BaseModel):
    """更新模板请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    steps_config: Optional[List[dict]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class TemplateRateSchema(BaseModel):
    """评分请求"""
    rating: int  # 1-5
    comment: Optional[str] = None


class CreateWorkflowFromTemplateSchema(BaseModel):
    """从模板创建工作流请求"""
    initial_input: dict
    workflow_name: Optional[str] = None


class ForkTemplateSchema(BaseModel):
    """Fork模板请求"""
    new_name: str


# ========================================
# 依赖注入
# ========================================

async def get_template_service():
    """获取模板服务"""
    async with get_session() as session:
        template_repo = WorkflowTemplateRepository(session)
        rating_repo = WorkflowTemplateRatingRepository(session)
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        workflow_service = WorkflowService(task_repo, emp_repo, None)  # task_service 需要单独处理
        yield WorkflowTemplateService(template_repo, rating_repo, workflow_service)


# ========================================
# 模板 CRUD
# ========================================

@router.post("", response_model=dict)
async def create_template(
    data: TemplateCreateSchema,
    user_id: str = "current_user",  # TODO: 从认证获取
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """创建模板"""
    try:
        request = TemplateCreateRequest(
            name=data.name,
            description=data.description,
            steps_config=data.steps_config,
            category=data.category,
            tags=data.tags,
            created_by=user_id,
            is_public=data.is_public,
        )
        template = await service.create_template(request)
        return {"success": True, "data": template.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=dict)
async def list_templates(
    category: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    is_public: Optional[bool] = None,
    sort_by: str = "usage_count",  # usage_count, created_at, rating
    include_system: bool = True,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取模板列表"""
    result = await service.list_templates(
        category=category,
        tags=tags,
        user_id=user_id if not is_public else None,
        is_public=is_public,
        sort_by=sort_by,
        include_system=include_system,
    )
    return {"success": True, "data": result}


@router.get("/search", response_model=dict)
async def search_templates(
    q: str,
    limit: int = 50,
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """搜索模板"""
    templates = await service.search_templates(q, limit)
    return {"success": True, "data": templates}


@router.get("/popular", response_model=dict)
async def get_popular_templates(
    limit: int = 10,
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取热门模板"""
    templates = await service.get_popular_templates(limit)
    return {"success": True, "data": templates}


@router.get("/top-rated", response_model=dict)
async def get_top_rated_templates(
    limit: int = 10,
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取高评分模板"""
    templates = await service.get_top_rated_templates(limit)
    return {"success": True, "data": templates}


@router.get("/categories", response_model=dict)
async def get_categories_and_tags(
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取所有分类和标签"""
    data = await service.get_categories_and_tags()
    return {"success": True, "data": data}


@router.get("/{template_id}", response_model=dict)
async def get_template(
    template_id: str,
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取模板详情"""
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"success": True, "data": template.to_dict()}


@router.put("/{template_id}", response_model=dict)
async def update_template(
    template_id: str,
    data: TemplateUpdateSchema,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """更新模板"""
    try:
        updates = data.dict(exclude_unset=True)
        template = await service.update_template(template_id, updates, user_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"success": True, "data": template.to_dict()}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}", response_model=dict)
async def delete_template(
    template_id: str,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """删除模板"""
    try:
        success = await service.delete_template(template_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"success": True}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ========================================
# 模板实例化
# ========================================

@router.post("/{template_id}/create-workflow", response_model=dict)
async def create_workflow_from_template(
    template_id: str,
    data: CreateWorkflowFromTemplateSchema,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """从模板创建工作流"""
    try:
        result = await service.create_workflow_from_template(
            template_id=template_id,
            initial_input=data.initial_input,
            created_by=user_id,
            workflow_name=data.workflow_name,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Fork 功能
# ========================================

@router.post("/{template_id}/fork", response_model=dict)
async def fork_template(
    template_id: str,
    data: ForkTemplateSchema,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """Fork模板"""
    try:
        template = await service.fork_template(template_id, data.new_name, user_id)
        return {"success": True, "data": template.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{template_id}/forks", response_model=dict)
async def get_template_fork_history(
    template_id: str,
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取模板的Fork历史"""
    forks = await service.get_template_fork_history(template_id)
    return {"success": True, "data": forks}


# ========================================
# 评分功能
# ========================================

@router.post("/{template_id}/rate", response_model=dict)
async def rate_template(
    template_id: str,
    data: TemplateRateSchema,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """评分模板"""
    try:
        await service.rate_template(
            template_id=template_id,
            user_id=user_id,
            rating=data.rating,
            comment=data.comment,
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}/ratings", response_model=dict)
async def get_template_ratings(
    template_id: str,
    limit: int = 20,
    offset: int = 0,
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取模板评分列表"""
    result = await service.get_template_ratings(template_id, limit, offset)
    return {"success": True, "data": result}


@router.get("/{template_id}/my-rating", response_model=dict)
async def get_user_rating(
    template_id: str,
    user_id: str = "current_user",
    service: WorkflowTemplateService = Depends(get_template_service),
):
    """获取当前用户对模板的评分"""
    rating = await service.get_user_rating(template_id, user_id)
    return {"success": True, "data": rating}
