"""
简化版 Manuals Router
核心功能: 手册管理
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Manuals"])

# ============ 数据模型 ============

class ManualTemplate(BaseModel):
    id: str
    name: str
    description: str
    applicable_scenarios: List[str]

class ManualGenerate(BaseModel):
    task_id: str
    template_id: Optional[str] = None  # None = 自动选择

class ManualContent(BaseModel):
    content: str
    constraints: List[str]
    references: List[str]

# ============ 预置模板 ============

TEMPLATES = [
    ManualTemplate(
        id="code_review",
        name="代码审查",
        description="审查代码质量、发现潜在问题",
        applicable_scenarios=["代码", "review", "bug", "fix"]
    ),
    ManualTemplate(
        id="research",
        name="研究调研",
        description="研究技术、调研方案",
        applicable_scenarios=["研究", "调研", "分析", "report"]
    ),
    ManualTemplate(
        id="writing",
        name="内容创作",
        description="写作、文档撰写",
        applicable_scenarios=["写作", "文档", "文章", "content"]
    ),
    ManualTemplate(
        id="data_analysis",
        name="数据分析",
        description="数据处理、可视化",
        applicable_scenarios=["数据", "可视化", "图表", "analysis"]
    ),
    ManualTemplate(
        id="generic",
        name="通用任务",
        description="通用任务执行",
        applicable_scenarios=[]
    ),
]

# ============ API ============

@router.get("/templates")
def list_templates() -> List[ManualTemplate]:
    """获取手册模板列表"""
    return TEMPLATES

@router.get("/templates/{template_id}")
def get_template(template_id: str) -> ManualTemplate:
    """获取模板详情"""
    for t in TEMPLATES:
        if t.id == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")

@router.post("/generate")
def generate_manual(data: ManualGenerate, db: Session = Depends(get_db)):
    """
    生成任务手册
    
    根据任务内容自动生成手册
    """
    # TODO: 实现手册生成
    return {
        "message": "Manual generated",
        "task_id": data.task_id,
        "template_id": data.template_id or "generic"
    }

@router.get("/task/{task_id}")
def get_task_manual(task_id: str, db: Session = Depends(get_db)):
    """获取任务的手册"""
    return {
        "has_manual": False,
        "template_id": None,
        "content": ""
    }

@router.post("/task/{task_id}/regenerate")
def regenerate_task_manual(task_id: str, db: Session = Depends(get_db)):
    """重新生成任务手册"""
    return {"message": "Manual regenerated"}

# ============ 岗位手册 ============

@router.get("/position/{position_id}")
def get_position_manual(position_id: str):
    """获取岗位手册"""
    return {"content": ""}

@router.put("/position/{position_id}")
def update_position_manual(position_id: str, content: str):
    """更新岗位手册"""
    return {"message": "Position manual updated"}

# ============ 公司手册 ============

@router.get("/company")
def get_company_manual():
    """获取公司手册"""
    return {"content": ""}

@router.put("/company")
def update_company_manual(content: str):
    """更新公司手册"""
    return {"message": "Company manual updated"}
