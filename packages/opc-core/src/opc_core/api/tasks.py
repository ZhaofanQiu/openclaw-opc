"""
opc-core: 任务管理 API

Task Router

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#Task
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository, TaskRepository
from opc_database.models import AgentStatus, TaskStatus
from opc_openclaw import Messenger

from ..api.dependencies import get_employee_repo, get_task_repo, verify_api_key

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ============ 数据模型 ============

class TaskCreate(BaseModel):
    """创建任务请求"""
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str = Field(default="", description="任务描述")
    priority: str = Field(default="normal", description="优先级: low/normal/high")
    estimated_cost: float = Field(default=100.0, ge=0, description="预估成本")


class TaskUpdate(BaseModel):
    """更新任务请求"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = None
    estimated_cost: Optional[float] = Field(default=None, ge=0)


class TaskAssignRequest(BaseModel):
    """分配任务请求"""
    employee_id: str = Field(..., description="员工ID")


class TaskCompleteRequest(BaseModel):
    """完成任务请求"""
    result: str = Field(..., description="执行结果")
    actual_cost: float = Field(default=0.0, ge=0, description="实际成本")


class TaskMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., description="消息内容")
    sender_type: str = Field(default="user", description="发送者类型")


# ============ API 路由 ============

@router.get("", response_model=dict)
async def list_tasks(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key)
):
    """获取任务列表"""
    if status:
        tasks = await repo.get_by_status(TaskStatus(status))
    elif employee_id:
        tasks = await repo.get_by_employee(employee_id)
    else:
        tasks = await repo.get_all(limit=1000)
    
    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks)
    }


@router.post("", response_model=dict, status_code=201)
async def create_task(
    data: TaskCreate,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key)
):
    """创建任务"""
    from opc_database.models import Task
    
    task = Task(
        id=f"task_{uuid.uuid4().hex[:8]}",
        title=data.title,
        description=data.description,
        priority=data.priority,
        estimated_cost=data.estimated_cost,
        status=TaskStatus.PENDING.value
    )
    
    await repo.create(task)
    
    return {
        "id": task.id,
        "title": task.title,
        "message": "Task created"
    }


@router.get("/{task_id}", response_model=dict)
async def get_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key)
):
    """获取任务详情"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task.to_dict()


@router.put("/{task_id}", response_model=dict)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key)
):
    """更新任务"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if data.title:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.priority:
        task.priority = data.priority
    if data.estimated_cost is not None:
        task.estimated_cost = data.estimated_cost
    
    await repo.update(task)
    
    return {"message": "Task updated", "task": task.to_dict()}


@router.delete("/{task_id}", response_model=dict)
async def delete_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """删除任务"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 如果任务已分配，释放员工
    if task.assigned_to:
        employee = await emp_repo.get_by_id(task.assigned_to)
        if employee:
            employee.status = AgentStatus.IDLE.value
            employee.current_task_id = None
            await emp_repo.update(employee)
    
    await repo.delete(task)
    
    return {"message": "Task deleted"}


# ============ 任务分配 ============

@router.post("/{task_id}/assign", response_model=dict)
async def assign_task(
    task_id: str,
    data: TaskAssignRequest,
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """分配任务给员工"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    employee = await emp_repo.get_by_id(data.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 检查员工可用性
    if employee.status != AgentStatus.IDLE.value:
        raise HTTPException(status_code=400, detail="Employee is not available")
    
    if not employee.openclaw_agent_id:
        raise HTTPException(status_code=400, detail="Employee not bound to OpenClaw")
    
    # 分配任务
    await repo.assign_task(task_id, data.employee_id)
    
    # 更新员工状态
    await emp_repo.update_status(data.employee_id, AgentStatus.WORKING, task_id)
    
    return {
        "message": "Task assigned",
        "task_id": task_id,
        "employee_id": data.employee_id
    }


@router.post("/{task_id}/start", response_model=dict)
async def start_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """开始执行任务 - 通知 Agent"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.ASSIGNED.value, TaskStatus.PENDING.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Task status is {task.status}, cannot start"
        )
    
    employee = await emp_repo.get_by_id(task.assigned_to)
    if not employee:
        raise HTTPException(status_code=400, detail="Task not assigned")
    
    # 更新任务状态
    await repo.start_task(task_id)
    
    # 发送消息给 Agent
    message = f"""# 任务开始: {task.title}

**任务ID**: {task.id}
**描述**: {task.description}

请开始执行任务，完成后使用 opc-bridge skill 报告结果。
"""
    
    async with Messenger() as messenger:
        response = await messenger.send(
            agent_id=employee.openclaw_agent_id,
            message=message,
            timeout=300
        )
    
    return {
        "message": "Task started",
        "task_id": task_id,
        "agent_response": response.content if response.success else None
    }


@router.post("/{task_id}/complete", response_model=dict)
async def complete_task(
    task_id: str,
    data: TaskCompleteRequest,
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """完成任务"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await repo.complete_task(task_id, data.result, data.actual_cost)
    
    # 更新员工状态
    if task.assigned_to:
        employee = await emp_repo.get_by_id(task.assigned_to)
        if employee:
            await emp_repo.update_status(task.assigned_to, AgentStatus.IDLE)
            await emp_repo.increment_completed_tasks(task.assigned_to)
    
    return {"message": "Task completed"}


@router.post("/{task_id}/fail", response_model=dict)
async def fail_task(
    task_id: str,
    reason: str = "Task failed",
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """标记任务失败"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await repo.fail_task(task_id, reason)
    
    # 更新员工状态
    if task.assigned_to:
        await emp_repo.update_status(task.assigned_to, AgentStatus.IDLE)
    
    return {"message": "Task marked as failed"}


@router.post("/{task_id}/rework", response_model=dict)
async def rework_task(
    task_id: str,
    feedback: str = "",
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key)
):
    """请求返工"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not task.can_rework:
        raise HTTPException(status_code=400, detail="Maximum rework count reached")
    
    await repo.request_rework(task_id, feedback)
    
    return {"message": "Task sent for rework", "rework_count": task.rework_count + 1}


# ============ 任务消息 ============

@router.get("/{task_id}/messages", response_model=dict)
async def get_messages(
    task_id: str,
    limit: int = 100,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key)
):
    """获取任务消息"""
    
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 这里需要获取 session 来创建 message repo
    # 简化处理，返回空列表
    return {"messages": [], "total": 0}


@router.post("/{task_id}/messages", response_model=dict)
async def send_message(
    task_id: str,
    data: TaskMessageRequest,
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """发送消息给任务执行者"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not task.assigned_to:
        raise HTTPException(status_code=400, detail="Task not assigned")
    
    employee = await emp_repo.get_by_id(task.assigned_to)
    if not employee or not employee.openclaw_agent_id:
        raise HTTPException(status_code=400, detail="Employee not bound")
    
    # 发送消息给 Agent
    async with Messenger() as messenger:
        response = await messenger.send(
            agent_id=employee.openclaw_agent_id,
            message=data.content,
            timeout=300
        )
    
    return {
        "message": "Message sent",
        "response": response.content if response.success else None
    }
