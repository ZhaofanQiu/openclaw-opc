"""
简化版 Tasks Router
核心功能: 任务 CRUD + 分配 + 执行
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Tasks"])

# ============ 数据模型 ============

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    priority: str = "medium"  # low, medium, high
    estimated_cost: int = Field(default=100, ge=0)

class TaskAssign(BaseModel):
    agent_id: str

class TaskComplete(BaseModel):
    output: str
    score: int = Field(default=5, ge=1, le=5)

# ============ 任务管理 ============

@router.get("")
def list_tasks(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    # TODO: 从数据库查询
    return {"tasks": [], "total": 0}

@router.post("")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """创建任务"""
    # TODO: 创建任务，自动生成手册
    return {"id": "", "message": "Task created"}

@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取任务详情"""
    return {}

@router.put("/{task_id}")
def update_task(
    task_id: str,
    data: TaskCreate,
    db: Session = Depends(get_db)
):
    """更新任务"""
    return {"message": "Task updated"}

@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    return {"message": "Task deleted"}

# ============ 任务分配与执行 ============

@router.post("/{task_id}/assign")
def assign_task(
    task_id: str,
    data: TaskAssign,
    db: Session = Depends(get_db)
):
    """
    分配任务给员工
    
    这是核心功能：
    1. 检查员工可用性
    2. 生成任务手册
    3. 创建任务步骤
    4. 唤醒 Agent
    """
    # TODO: 实现完整流程
    return {
        "message": "Task assigned",
        "task_id": task_id,
        "agent_id": data.agent_id
    }

@router.post("/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db)):
    """开始执行任务"""
    # TODO: 调用 TaskExecutor
    return {"message": "Task started"}

@router.post("/{task_id}/complete")
def complete_task(
    task_id: str,
    data: TaskComplete,
    db: Session = Depends(get_db)
):
    """完成任务"""
    return {"message": "Task completed"}

@router.post("/{task_id}/rework")
def rework_task(
    task_id: str,
    reason: str,
    db: Session = Depends(get_db)
):
    """返工任务"""
    return {"message": "Task sent for rework", "reason": reason}

# ============ 任务手册 ============

@router.get("/{task_id}/manual")
def get_task_manual(task_id: str, db: Session = Depends(get_db)):
    """获取任务手册"""
    return {"has_manual": False, "content": ""}

@router.post("/{task_id}/manual/regenerate")
def regenerate_manual(task_id: str, db: Session = Depends(get_db)):
    """重新生成手册"""
    return {"message": "Manual regenerated"}

# ============ 任务步骤（聊天） ============

@router.get("/{task_id}/messages")
def get_task_messages(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取任务消息列表"""
    return {"messages": [], "total": 0}

@router.post("/{task_id}/messages")
def send_message(
    task_id: str,
    content: str,
    db: Session = Depends(get_db)
):
    """发送消息"""
    return {"message": "Message sent"}
