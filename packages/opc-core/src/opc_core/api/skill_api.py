"""
opc-core: Skill API (⚠️ 已废弃)

Phase 2 架构变更后，此模块不再使用。

原功能:
- Agent 通过 HTTP POST 回调报告任务结果
- Agent 查询当前任务和预算

新架构:
- Agent 在消息回复中嵌入 OPC-REPORT 格式
- Core 通过 ResponseParser 同步解析结果
- 不再需要 HTTP 回调端点

保留原因:
- 向后兼容 (如有旧版 Agent)
- 提供手动测试接口
- 读取手册功能仍可独立使用

作者: OpenClaw OPC Team
创建日期: 2026-03-24
废弃日期: 2026-03-25
版本: 0.4.1

API文档: API.md#SkillAPI (Deprecated)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository, TaskRepository

from ..api.dependencies import get_employee_repo, get_task_repo

router = APIRouter(
    prefix="/skill",
    tags=["SkillAPI (Deprecated)"],
    deprecated=True,  # FastAPI 标记为废弃
)


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


# ============ 废弃提示 ============

DEPRECATION_NOTICE = {
    "warning": "This API is deprecated",
    "reason": "Phase 2 architecture change: Agent now reports results via OPC-REPORT format in message replies",
    "alternative": "Use /api/tasks/{id}/assign for synchronous task assignment and result retrieval",
    "docs": "See PLAN_v0.4.1.md for migration guide",
}


# ============ API 路由 (已废弃) ============


@router.post(
    "/get-current-task",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="⚠️ 已废弃: 获取当前任务",
    description="Agent 不再通过此端点获取任务。任务通过 /tasks/{id}/assign 同步分配。",
)
async def get_current_task(
    data: GetTaskRequest,
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
):
    """
    ⚠️ 已废弃

    原功能: Agent 调用 opc_get_current_task() 获取当前任务
    新方式: 任务通过 /tasks/{id}/assign 同步分配，Agent 直接收到任务消息
    """
    # 保留原功能以兼容旧版
    employee = await emp_repo.get_by_openclaw_id(data.agent_id)

    if not employee or not employee.current_task_id:
        return {"deprecated": True, **DEPRECATION_NOTICE, "has_task": False}

    task = await task_repo.get_by_id(employee.current_task_id)
    if not task:
        return {"deprecated": True, **DEPRECATION_NOTICE, "has_task": False}

    return {
        "deprecated": True,
        **DEPRECATION_NOTICE,
        "has_task": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
        },
    }


@router.post(
    "/report-task-result",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="⚠️ 已废弃: 报告任务结果",
    description="Agent 不再通过此端点报告结果。结果通过 OPC-REPORT 格式在消息回复中嵌入。",
)
async def report_task_result(
    data: ReportResultRequest,
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
):
    """
    ⚠️ 已废弃

    原功能: Agent 调用 opc_report_task_result() 报告任务完成
    新方式: Agent 在回复中嵌入 OPC-REPORT 格式，Core 通过 ResponseParser 解析

    示例 OPC-REPORT 格式:
    ```
    ---OPC-REPORT---
    task_id: task-001
    status: completed
    tokens_used: 500
    summary: Task completed successfully
    ---END-REPORT---
    ```
    """
    # 保留原功能以兼容旧版
    employee = await emp_repo.get_by_openclaw_id(data.agent_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    task = await task_repo.get_by_id(data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 验证任务是否分配给该员工
    if task.assigned_to != employee.id:
        raise HTTPException(
            status_code=403, detail="Task not assigned to this employee"
        )

    # 计算成本
    cost = data.tokens_used * 0.01

    # 完成任务
    from opc_database.models import AgentStatus

    await task_repo.complete_task(
        task_id=data.task_id, result=data.result, actual_cost=cost
    )

    # 更新员工状态
    await emp_repo.update_status(employee.id, AgentStatus.IDLE)
    await emp_repo.increment_completed_tasks(employee.id)
    await emp_repo.update_budget(employee.id, cost, operation="use")

    return {
        "deprecated": True,
        **DEPRECATION_NOTICE,
        "success": True,
        "cost": cost,
        "remaining_budget": employee.remaining_budget - cost,
        "message": "Task completed (via deprecated API)",
    }


@router.post(
    "/get-budget",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="⚠️ 已废弃: 获取预算",
    description="预算信息现在通过任务消息传递给 Agent。",
)
async def get_budget(
    data: GetBudgetRequest, emp_repo: EmployeeRepository = Depends(get_employee_repo)
):
    """
    ⚠️ 已废弃

    原功能: Agent 调用 opc_get_budget() 获取预算
    新方式: 预算信息包含在任务分配消息中
    """
    employee = await emp_repo.get_by_openclaw_id(data.agent_id)

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "deprecated": True,
        **DEPRECATION_NOTICE,
        "monthly_budget": employee.monthly_budget,
        "used_budget": employee.used_budget,
        "remaining_budget": employee.remaining_budget,
        "mood": employee.mood_emoji,
    }


@router.post(
    "/read-manual",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="读取手册内容 (仍可用)",
    description="此端点仍可用，Agent 可通过它读取手册内容。",
)
async def read_manual(data: ReadManualRequest):
    """
    读取手册内容

    Agent 可通过此端点读取手册。
    注意: Agent 应优先使用任务消息中提供的绝对路径读取手册。
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
        raise HTTPException(
            status_code=400, detail=f"Unknown manual type: {data.manual_type}"
        )

    if not path.exists():
        return {"exists": False, "content": "", "path": str(path)}

    content = path.read_text(encoding="utf-8")

    return {"exists": True, "content": content, "path": str(path)}
