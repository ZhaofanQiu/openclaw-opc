"""
简化版 Tasks Router
核心功能: 任务 CRUD + 分配 + 执行
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.task_v2 import Task, TaskStatus, TaskPriority
from models.agent_v2 import Agent, AgentStatus
from utils.logging_config import get_logger
from core.openclaw_client import assign_task

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
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    
    tasks = query.all()
    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks)
    }

@router.post("")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """创建任务"""
    task = Task(
        id=f"task_{uuid.uuid4().hex[:8]}",
        title=data.title,
        description=data.description,
        priority=data.priority,
        estimated_cost=float(data.estimated_cost),
        status=TaskStatus.PENDING.value
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    logger.info(f"Created task: {task.title} ({task.id})")
    
    return {
        "id": task.id,
        "title": task.title,
        "message": "Task created"
    }

@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

@router.put("/{task_id}")
def update_task(
    task_id: str,
    data: TaskCreate,
    db: Session = Depends(get_db)
):
    """更新任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.title = data.title
    task.description = data.description
    task.priority = data.priority
    task.estimated_cost = float(data.estimated_cost)
    
    db.commit()
    db.refresh(task)
    
    return {"message": "Task updated", "task": task.to_dict()}

@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted"}


@router.get("/{task_id}/manual")
def get_task_manual(task_id: str, db: Session = Depends(get_db)):
    """获取任务手册"""
    from services.manual_service import get_task_manual
    
    manual = get_task_manual(task_id)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual not found")
    
    return manual

# ============ 任务分配与执行 ============

@router.post("/{task_id}/assign")
async def assign_task_endpoint(
    task_id: str,
    data: TaskAssign,
    db: Session = Depends(get_db)
):
    """
    分配任务给员工
    
    核心功能：
    1. 检查员工可用性
    2. 更新任务状态
    3. 发送消息到 Agent（同步或异步）
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    agent = db.query(Agent).filter(Agent.id == data.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.status != AgentStatus.IDLE.value:
        raise HTTPException(status_code=400, detail="Agent is not available")
    
    # 检查是否绑定了 OpenClaw agent
    if not agent.openclaw_agent_id:
        raise HTTPException(status_code=400, detail="Agent not bound to OpenClaw")
    
    # 更新任务状态
    task.assigned_to = data.agent_id
    task.status = TaskStatus.ASSIGNED.value
    db.commit()
    
    # 更新员工状态
    agent.status = AgentStatus.WORKING.value
    agent.current_task_id = task_id
    db.commit()
    
    logger.info(f"Task {task_id} assigned to agent {data.agent_id}")
    
    # 生成任务手册
    from services.manual_service import generate_task_manual
    manual_result = generate_task_manual(
        task_id=task_id,
        title=task.title,
        description=task.description,
        estimated_cost=task.estimated_cost
    )
    
    logger.info(f"Manual generated: {manual_result['relative_path']} (template: {manual_result['template']})")
    
    # 获取所有手册路径
    manual_paths = {
        "task": manual_result['relative_path'],
        "company": "data/manuals/company.md",
        "employee": f"data/manuals/employees/{data.agent_id}.md"
    }
    
    # 如果任务有指定职责，添加职责手册
    # TODO: 任务模型需要添加 role 字段
    # 暂时默认使用 executor 职责
    manual_paths["role"] = "data/manuals/roles/executor.md"
    
    # 发送消息到 Agent（异步）
    try:
        import asyncio
        response = await assign_task(
            agent_id=agent.openclaw_agent_id,
            agent_name=agent.name,
            task_id=task_id,
            task_title=task.title,
            task_description=task.description,
            manual_paths=manual_paths,
            async_mode=True
        )
        
        return {
            "message": "Task assigned and agent notified",
            "task_id": task_id,
            "agent_id": data.agent_id,
            "execution_id": response.execution_id,
            "status": response.status,
            "manuals": manual_paths
        }
    except Exception as e:
        logger.error(f"Failed to notify agent: {e}")
        return {
            "message": "Task assigned but failed to notify agent",
            "task_id": task_id,
            "agent_id": data.agent_id,
            "error": str(e),
            "manuals": manual_paths
        }

@router.post("/{task_id}/start")
def start_task(task_id: str, db: Session = Depends(get_db)):
    """开始执行任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = TaskStatus.IN_PROGRESS.value
    db.commit()
    
    return {"message": "Task started"}

@router.post("/{task_id}/complete")
def complete_task(
    task_id: str,
    data: TaskComplete,
    db: Session = Depends(get_db)
):
    """完成任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = TaskStatus.COMPLETED.value
    task.result = data.output
    task.score = data.score
    db.commit()
    
    # 更新员工状态
    if task.assigned_to:
        agent = db.query(Agent).filter(Agent.id == task.assigned_to).first()
        if agent:
            agent.status = AgentStatus.IDLE.value
            agent.current_task_id = None
            agent.completed_tasks += 1
            db.commit()
    
    return {"message": "Task completed"}

@router.post("/{task_id}/rework")
def rework_task(
    task_id: str,
    reason: str,
    db: Session = Depends(get_db)
):
    """返工任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.rework_count += 1
    task.status = TaskStatus.ASSIGNED.value
    db.commit()
    
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
