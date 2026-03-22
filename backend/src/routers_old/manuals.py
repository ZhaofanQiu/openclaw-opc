"""
任务手册 API 路由

提供手册模板管理和手册内容获取
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.manual_service import ManualService, get_manual_service
from src.services.manual_template_engine import template_engine
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/manuals", tags=["Task Manuals"])


# ============ 请求/响应模型 ============

class TemplateResponse(BaseModel):
    """模板响应"""
    id: str
    name: str
    description: str


class ManualPreviewRequest(BaseModel):
    """手册预览请求"""
    task_title: str = Field(..., description="任务标题")
    task_description: str = Field(default="", description="任务描述")
    template_id: Optional[str] = Field(default=None, description="模板ID，为空则自动选择")


class ManualPreviewResponse(BaseModel):
    """手册预览响应"""
    content: str
    template_id: str
    template_name: str


class TaskManualResponse(BaseModel):
    """任务手册响应"""
    task_id: str
    has_manual: bool
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    content: Optional[str] = None
    constraints: list = []
    expected_output: Optional[str] = None
    generated_at: Optional[str] = None


# ============ API 端点 ============

@router.get("/templates", response_model=list[TemplateResponse])
@limiter.limit(RATE_LIMITS["default"])
async def list_templates(
    request: Request,  # Required by slowapi
    db: Session = Depends(get_db),
):
    """
    列出所有可用手册模板
    """
    service = get_manual_service(db)
    templates = service.list_available_templates()
    return templates


@router.post("/preview", response_model=ManualPreviewResponse)
@limiter.limit(RATE_LIMITS["create"])
async def preview_manual(
    request: Request,  # Required by slowapi
    data: ManualPreviewRequest,
    db: Session = Depends(get_db),
):
    """
    预览任务手册（不保存）
    
    根据任务标题和描述生成手册预览
    """
    service = get_manual_service(db)
    
    content = service.preview_manual(
        task_title=data.task_title,
        task_description=data.task_description,
        template_id=data.template_id,
    )
    
    # 获取模板信息
    template_id = data.template_id or template_engine.select_template_for_task(
        data.task_title, data.task_description
    )
    template = template_engine.get_template(template_id)
    
    return ManualPreviewResponse(
        content=content,
        template_id=template_id,
        template_name=template.name if template else "通用模板",
    )


@router.get("/task/{task_id}", response_model=TaskManualResponse)
@limiter.limit(RATE_LIMITS["default"])
async def get_task_manual(
    request: Request,  # Required by slowapi
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    获取任务的手册内容
    
    如果任务已生成手册，返回手册内容；否则返回 has_manual=false
    """
    from src.models import Task
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    context = task.get_execution_context()
    manual_data = context.get("manual", {})
    
    if not manual_data:
        return TaskManualResponse(
            task_id=task_id,
            has_manual=False,
        )
    
    template_id = manual_data.get("template_id", "unknown")
    template = template_engine.get_template(template_id)
    
    return TaskManualResponse(
        task_id=task_id,
        has_manual=True,
        template_id=template_id,
        template_name=template.name if template else "Unknown",
        content=manual_data.get("content"),
        constraints=manual_data.get("constraints", []),
        expected_output=manual_data.get("expected_output"),
        generated_at=manual_data.get("generated_at"),
    )


@router.post("/task/{task_id}/regenerate")
@limiter.limit(RATE_LIMITS["create"])
async def regenerate_manual(
    request: Request,  # Required by slowapi
    task_id: str,
    template_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    重新生成任务手册
    
    可以指定新的模板ID，否则使用自动选择
    """
    from src.models import Task
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    service = get_manual_service(db)
    
    try:
        manual = service.generate_manual_for_task(
            task_id=task.id,
            task_title=task.title,
            task_description=task.description or "",
            template_id=template_id,
        )
        
        # 更新任务上下文
        context = task.get_execution_context()
        context["manual"] = {
            "template_id": manual.template_id,
            "content": manual.content,
            "constraints": manual.constraints,
            "expected_output": manual.expected_output,
            "generated_at": datetime.utcnow().isoformat(),
        }
        task.set_execution_context(context)
        db.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "template_id": manual.template_id,
            "template_name": template_engine.get_template(manual.template_id).name if template_engine.get_template(manual.template_id) else "Unknown",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate manual: {str(e)}")


# 导入 datetime 用于 regenerate_manual
from datetime import datetime
