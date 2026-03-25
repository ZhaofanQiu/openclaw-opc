"""
opc-core: 任务管理 API (v0.4.1)

Task Router - 适配 Phase 2 新架构

核心变更:
- /tasks/{id}/assign 改为同步返回结果
- 使用 TaskService 替代直接 Repository 操作
- 添加 /tasks/{id}/retry 路由

作者: OpenClaw OPC Team
创建日期: 2026-03-24
更新日期: 2026-03-25
版本: 0.4.1

API文档: API.md#Task
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository, TaskRepository
from opc_database.models import TaskStatus

from ..api.dependencies import get_employee_repo, get_task_repo, verify_api_key
from ..services import (
    TaskService,
    TaskNotFoundError,
    EmployeeNotFoundError,
    AgentNotBoundError,
    TaskAssignmentError,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ============ 数据模型 ============


class TaskCreate(BaseModel):
    """创建任务请求"""

    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    description: str = Field(default="", description="任务描述")
    priority: str = Field(default="normal", description="优先级: low/normal/high")
    estimated_cost: float = Field(default=100.0, ge=0, description="预估成本")
    employee_id: Optional[str] = Field(default=None, description="预分配员工ID")


class TaskUpdate(BaseModel):
    """更新任务请求"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[str] = None
    estimated_cost: Optional[float] = Field(default=None, ge=0)


class TaskAssignRequest(BaseModel):
    """分配任务请求"""

    employee_id: str = Field(..., description="员工ID")


class TaskResponse(BaseModel):
    """任务响应 (更新后包含完整结果)"""

    id: str
    title: str
    description: str
    status: str
    priority: str
    assigned_to: Optional[str]
    estimated_cost: float
    actual_cost: float
    tokens_input: int
    tokens_output: int
    session_key: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[str]
    rework_count: int
    max_rework: int


# ============ 依赖注入 ============


def get_task_service(
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
) -> TaskService:
    """获取 TaskService 实例"""
    return TaskService(task_repo=repo, emp_repo=emp_repo)


# ============ API 路由 ============


@router.get("", response_model=dict)
async def list_tasks(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取任务列表"""
    if status:
        tasks = await repo.get_by_status(TaskStatus(status))
    elif employee_id:
        tasks = await repo.get_by_employee(employee_id)
    else:
        tasks = await repo.get_all(limit=1000)

    return {"tasks": [t.to_dict() for t in tasks], "total": len(tasks)}


@router.post("", response_model=dict, status_code=201)
async def create_task(
    data: TaskCreate,
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """创建任务 (如果指定了员工，自动分配并执行)"""
    from opc_database.models import Task

    task = Task(
        id=f"task_{uuid.uuid4().hex[:8]}",
        title=data.title,
        description=data.description,
        priority=data.priority,
        estimated_cost=data.estimated_cost,
        status=TaskStatus.PENDING.value,
        assigned_to=data.employee_id,
    )

    await repo.create(task)

    # 如果指定了员工，自动分配并执行
    if data.employee_id:
        task_service = TaskService(repo, emp_repo)
        try:
            task = await task_service.assign_task(task.id, data.employee_id)
            return {
                "id": task.id,
                "title": task.title,
                "message": "Task created and assigned",
                "status": task.status
            }
        except Exception as e:
            # 分配失败但任务已创建，返回警告
            return {
                "id": task.id,
                "title": task.title,
                "message": f"Task created but assignment failed: {str(e)}",
                "status": task.status
            }

    return {"id": task.id, "title": task.title, "message": "Task created"}


@router.get("/{task_id}", response_model=dict)
async def get_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
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
    api_key: str = Depends(verify_api_key),
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
    api_key: str = Depends(verify_api_key),
):
    """删除任务"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 如果任务已分配，释放员工
    if task.assigned_to:
        employee = await emp_repo.get_by_id(task.assigned_to)
        if employee:
            from opc_database.models import AgentStatus
            employee.status = AgentStatus.IDLE.value
            employee.current_task_id = None
            await emp_repo.update(employee)

    await repo.delete(task)

    return {"message": "Task deleted"}


# ============ 任务分配 (新架构 - 同步返回) ============


@router.post("/{task_id}/assign", response_model=dict)
async def assign_task(
    task_id: str,
    data: TaskAssignRequest,
    task_service: TaskService = Depends(get_task_service),
    api_key: str = Depends(verify_api_key),
):
    """
    分配任务给员工 (新架构: 同步返回结果)

    此端点会:
    1. 验证任务和员工
    2. 调用 OpenClaw Agent 执行任务
    3. 同步等待 Agent 回复
    4. 解析 OPC-REPORT 格式结果
    5. 返回最终任务状态

    响应包含:
    - status: completed/failed/needs_revision/needs_review
    - result: Agent 执行结果摘要
    - tokens_output: 实际消耗的 Token 数
    - actual_cost: 实际成本

    ⚠️ 注意: 此操作是同步的，可能需要等待 15-60 秒
    """
    try:
        task = await task_service.assign_task(task_id, data.employee_id)

        return {
            "message": "Task assigned and completed",
            "task": task.to_dict(),
        }

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except EmployeeNotFoundError:
        raise HTTPException(status_code=404, detail="Employee not found")
    except AgentNotBoundError:
        raise HTTPException(
            status_code=400, detail="Employee has no OpenClaw agent bound"
        )
    except TaskAssignmentError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/retry", response_model=dict)
async def retry_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service),
    api_key: str = Depends(verify_api_key),
):
    """
    重试失败的任务

    可重试的状态: failed, needs_revision, needs_review
    会检查返工次数限制 (max_rework)
    """
    try:
        task = await task_service.retry_task(task_id)

        return {
            "message": "Task retried successfully",
            "task": task.to_dict(),
        }

    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except TaskAssignmentError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 任务状态管理 (简化) ============


@router.post("/{task_id}/cancel", response_model=dict)
async def cancel_task(
    task_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """取消任务 (仅 PENDING 状态可取消)"""
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status {task.status}"
        )

    task.status = TaskStatus.FAILED.value
    task.result = "Task cancelled by user"
    await repo.update(task)

    return {"message": "Task cancelled"}


# ============ 以下路由已废弃 (Phase 2 架构变更) ============

# 原 /tasks/{id}/start - 已合并到 /assign
# 原 /tasks/{id}/complete - 已由 Agent 通过 OPC-REPORT 触发
# 原 /tasks/{id}/fail - 已由 Agent 通过 OPC-REPORT 触发
# 原 /tasks/{id}/rework - 已由 Agent 通过 OPC-REPORT 触发
