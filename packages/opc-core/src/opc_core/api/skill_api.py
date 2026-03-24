"""
opc-core: Skill API

处理 Agent 通过 opc-bridge skill 发起的 API 调用

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#SkillAPI
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository, TaskRepository

from ..api.dependencies import get_employee_repo, get_task_repo

router = APIRouter(prefix="/skill", tags=["SkillAPI"])


# ============ 数据模型 ============

class GetTaskRequest(BaseModel):
    """获取当前任务请求"""
    agent_id: str = Field(..., description="OpenClaw Agent ID")


class ReportResultRequest(BaseModel):
    """报告任务结果请求"""
    agent_id: str = Field(..., description="OpenClaw Agent ID")
    task_id: str = Field(..., description="任务ID")
    result: str = Field(..., description="执行结果")
    tokens_used: int = Field(..., ge=0, description="消耗的Token数")


class GetBudgetRequest(BaseModel):
    """获取预算请求"""
    agent_id: str = Field(..., description="OpenClaw Agent ID")


class ReadManualRequest(BaseModel):
    """读取手册请求"""
    agent_id: str = Field(..., description="OpenClaw Agent ID")
    manual_type: str = Field(..., description="手册类型: task/employee/company")
    manual_id: Optional[str] = Field(default=None, description="手册ID")


# ============ API 路由 ============

@router.post("/get-current-task", response_model=dict)
async def get_current_task(
    data: GetTaskRequest,
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    task_repo: TaskRepository = Depends(get_task_repo)
):
    """
    获取当前分配给 Agent 的任务
    
    Agent 调用: opc_get_current_task()
    """
    # 通过 OpenClaw Agent ID 找到员工
    employee = await emp_repo.get_by_openclaw_id(data.agent_id)
    
    if not employee or not employee.current_task_id:
        return {
            "has_task": False,
            "task": None
        }
    
    # 获取任务详情
    task = await task_repo.get_by_id(employee.current_task_id)
    if not task:
        return {
            "has_task": False,
            "task": None
        }
    
    return {
        "has_task": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "estimated_cost": task.estimated_cost,
            "status": task.status
        }
    }


@router.post("/report-task-result", response_model=dict)
async def report_task_result(
    data: ReportResultRequest,
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    task_repo: TaskRepository = Depends(get_task_repo)
):
    """
    报告任务执行结果
    
    Agent 调用: opc_report_task_result()
    """
    # 找到员工
    employee = await emp_repo.get_by_openclaw_id(data.agent_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 获取任务
    task = await task_repo.get_by_id(data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 验证任务是否分配给该员工
    if task.assigned_to != employee.id:
        raise HTTPException(status_code=403, detail="Task not assigned to this employee")
    
    # 计算成本（假设 1 token = 0.01 OC币）
    cost = data.tokens_used * 0.01
    
    # 完成任务
    from opc_database.models import AgentStatus
    await task_repo.complete_task(
        task_id=data.task_id,
        result=data.result,
        actual_cost=cost
    )
    
    # 更新员工状态
    await emp_repo.update_status(employee.id, AgentStatus.IDLE)
    await emp_repo.increment_completed_tasks(employee.id)
    await emp_repo.update_budget(employee.id, cost, operation="use")
    
    return {
        "success": True,
        "cost": cost,
        "remaining_budget": employee.remaining_budget - cost,
        "message": "Task completed successfully"
    }


@router.post("/get-budget", response_model=dict)
async def get_budget(
    data: GetBudgetRequest,
    emp_repo: EmployeeRepository = Depends(get_employee_repo)
):
    """
    获取预算状态
    
    Agent 调用: opc_get_budget()
    """
    employee = await emp_repo.get_by_openclaw_id(data.agent_id)
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {
        "monthly_budget": employee.monthly_budget,
        "used_budget": employee.used_budget,
        "remaining_budget": employee.remaining_budget,
        "mood": employee.mood_emoji
    }


@router.post("/read-manual", response_model=dict)
async def read_manual(
    data: ReadManualRequest
):
    """
    读取手册内容
    
    Agent 调用: opc_read_manual()
    """
    from pathlib import Path
    
    manuals_dir = Path("data/manuals")
    
    if data.manual_type == "company":
        path = manuals_dir / "company.md"
    elif data.manual_type == "employee":
        path = manuals_dir / "employees" / f"{data.manual_id}.md"
    elif data.manual_type == "task":
        path = manuals_dir / "tasks" / f"{data.manual_id}.md"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown manual type: {data.manual_type}")
    
    if not path.exists():
        return {
            "exists": False,
            "content": "",
            "path": str(path)
        }
    
    content = path.read_text(encoding="utf-8")
    
    return {
        "exists": True,
        "content": content,
        "path": str(path)
    }
