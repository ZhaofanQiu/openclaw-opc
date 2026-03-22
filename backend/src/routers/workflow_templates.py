"""
Workflow Template Router v0.5.4

模板管理API
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.workflow_template_service import WorkflowTemplateService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflow-templates", tags=["workflow-templates"])


# ============== Request Models ==============

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    category: str = Field(default="custom")
    steps_config: List[dict] = Field(..., description="步骤配置")
    budget_config: dict = Field(default={
        "rework_ratio": 0.2,
        "default_rework_limit": 3,
    })
    tags: List[str] = Field(default=[])
    visibility: str = Field(default="private")
    team_id: Optional[str] = Field(default=None)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    visibility: Optional[str] = Field(default=None)
    steps_config: Optional[List[dict]] = Field(default=None)
    budget_config: Optional[dict] = Field(default=None)


class TemplateFork(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=100)


class TemplateRate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="1-5星评分")


# ============== CRUD Endpoints ==============

@router.post("")
async def create_template(
    data: TemplateCreate,
    created_by: str,
    db: Session = Depends(get_db),
):
    """创建模板"""
    service = WorkflowTemplateService(db)
    try:
        template = service.create_template(
            name=data.name,
            description=data.description,
            category=data.category,
            steps_config=data.steps_config,
            budget_config=data.budget_config,
            created_by=created_by,
            tags=data.tags,
            visibility=data.visibility,
            team_id=data.team_id,
        )
        return {
            "success": True,
            "template": service._format_template_detail(template),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_templates(
    agent_id: str,
    category: str = None,
    tags: str = None,  # 逗号分隔
    visibility: str = None,
    sort_by: str = "usage",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """列出模板"""
    service = WorkflowTemplateService(db)
    tag_list = tags.split(",") if tags else None
    
    result = service.list_templates(
        agent_id=agent_id,
        category=category,
        tags=tag_list,
        visibility=visibility,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/my")
async def get_my_templates(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取我创建的模板"""
    service = WorkflowTemplateService(db)
    return {
        "templates": service.get_my_templates(agent_id),
    }


@router.get("/favorites")
async def get_favorite_templates(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取收藏的模板"""
    service = WorkflowTemplateService(db)
    return {
        "templates": service.get_favorite_templates(agent_id),
    }


@router.get("/popular")
async def get_popular_templates(
    category: str = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取热门模板"""
    service = WorkflowTemplateService(db)
    return {
        "templates": service.get_popular_templates(category=category, limit=limit),
    }


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取模板详情"""
    service = WorkflowTemplateService(db)
    template = service.get_template(template_id, agent_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or no permission")
    
    return service._format_template_detail(template)


@router.put("/{template_id}")
async def update_template(
    template_id: str,
    data: TemplateUpdate,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """更新模板"""
    service = WorkflowTemplateService(db)
    
    updates = {k: v for k, v in data.dict().items() if v is not None}
    
    try:
        template = service.update_template(template_id, agent_id, updates)
        return {
            "success": True,
            "template": service._format_template_detail(template),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """删除模板"""
    service = WorkflowTemplateService(db)
    try:
        success = service.delete_template(template_id, agent_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/fork")
async def fork_template(
    template_id: str,
    data: TemplateFork,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Fork模板"""
    service = WorkflowTemplateService(db)
    try:
        new_template = service.fork_template(template_id, data.new_name, agent_id)
        return {
            "success": True,
            "template": service._format_template_detail(new_template),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== 收藏和评分 ==============

@router.post("/{template_id}/favorite")
async def add_favorite(
    template_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """收藏模板"""
    service = WorkflowTemplateService(db)
    service.add_favorite(template_id, agent_id)
    return {"success": True}


@router.delete("/{template_id}/favorite")
async def remove_favorite(
    template_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """取消收藏"""
    service = WorkflowTemplateService(db)
    service.remove_favorite(template_id, agent_id)
    return {"success": True}


@router.post("/{template_id}/rate")
async def rate_template(
    template_id: str,
    data: TemplateRate,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """评分模板"""
    service = WorkflowTemplateService(db)
    try:
        new_rating = service.rate_template(template_id, agent_id, data.rating)
        return {
            "success": True,
            "new_rating": new_rating,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== 统计 ==============

@router.get("/{template_id}/stats")
async def get_template_stats(
    template_id: str,
    db: Session = Depends(get_db),
):
    """获取模板统计"""
    from src.models.workflow_template_v2 import WorkflowTemplateV2
    
    template = db.query(WorkflowTemplateV2).filter(
        WorkflowTemplateV2.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 计算趋势（最近30天vs前30天）
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    recent_30 = now - timedelta(days=30)
    prev_30 = recent_30 - timedelta(days=30)
    
    from src.models.workflow_template_v2 import WorkflowTemplateUsage
    
    recent_usage = db.query(WorkflowTemplateUsage).filter(
        WorkflowTemplateUsage.template_id == template_id,
        WorkflowTemplateUsage.created_at >= recent_30
    ).count()
    
    prev_usage = db.query(WorkflowTemplateUsage).filter(
        WorkflowTemplateUsage.template_id == template_id,
        WorkflowTemplateUsage.created_at >= prev_30,
        WorkflowTemplateUsage.created_at < recent_30
    ).count()
    
    trend = "up" if recent_usage > prev_usage else "down" if recent_usage < prev_usage else "stable"
    
    return {
        "template_id": template_id,
        "usage": {
            "total": template.usage_count,
            "recent_30_days": recent_usage,
            "trend": trend,
        },
        "performance": {
            "avg_completion_time": template.avg_completion_time,
            "avg_rework_count": template.avg_rework_count,
            "success_rate": template.success_rate,
        },
        "rating": {
            "average": template.rating,
            "count": template.rating_count,
        },
    }


# ============== 预置模板 ==============

@router.get("/presets/list")
async def get_preset_templates():
    """获取预置模板列表"""
    presets = [
        {
            "id": "preset_web_dev",
            "name": "Web开发流程",
            "category": "development",
            "description": "标准Web应用开发流程",
            "steps": ["规划", "后端开发", "前端开发", "联调", "评审", "测试", "交付"],
        },
        {
            "id": "preset_api_dev",
            "name": "API开发流程",
            "category": "development",
            "description": "后端API开发流程",
            "steps": ["规划", "开发", "评审", "测试", "交付"],
        },
        {
            "id": "preset_research",
            "name": "研究调研流程",
            "category": "research",
            "description": "技术调研和研究流程",
            "steps": ["规划", "研究", "评审", "报告"],
        },
        {
            "id": "preset_doc",
            "name": "文档写作流程",
            "category": "documentation",
            "description": "技术文档写作流程",
            "steps": ["规划", "写作", "审核", "发布"],
        },
    ]
    return {"presets": presets}
