"""
opc-core: 报表 API

Report Router

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#Report
"""

from fastapi import APIRouter, Depends

from opc_database.repositories import EmployeeRepository, TaskRepository

from ..api.dependencies import get_employee_repo, get_task_repo, verify_api_key

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/dashboard", response_model=dict)
async def get_dashboard_report(
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """
    获取 Dashboard 报表数据

    汇总所有关键指标
    """
    # 员工统计
    employees = await emp_repo.get_all(limit=1000)
    budget_stats = await emp_repo.get_budget_stats()

    # 任务统计
    task_stats = await task_repo.get_task_stats()

    # 计算在线员工数
    from opc_database.models import AgentStatus

    online_count = sum(1 for e in employees if e.status == AgentStatus.IDLE.value)
    working_count = sum(1 for e in employees if e.status == AgentStatus.WORKING.value)

    return {
        "employees": {
            "total": len(employees),
            "online": online_count,
            "working": working_count,
            "total_budget": budget_stats["total_budget"],
            "total_used": budget_stats["total_used"],
            "total_remaining": budget_stats["total_remaining"],
        },
        "tasks": task_stats,
        "summary": {
            "status": "normal" if budget_stats["total_remaining"] > 1000 else "warning",
            "health_score": (
                min(
                    100,
                    int(
                        (
                            task_stats["completion_rate"] * 0.5
                            + (1 - budget_stats["usage_rate"]) * 0.5
                        )
                        * 100
                    ),
                )
                if task_stats["total_tasks"] > 0
                else 100
            ),
        },
    }


@router.get("/employees", response_model=dict)
async def get_employee_report(
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取员工绩效报表"""
    employees = await emp_repo.get_all(limit=1000)

    report = []
    for emp in employees:
        report.append(
            {
                "id": emp.id,
                "name": emp.name,
                "emoji": emp.emoji,
                "status": emp.status,
                "monthly_budget": emp.monthly_budget,
                "used_budget": emp.used_budget,
                "remaining_budget": emp.remaining_budget,
                "completed_tasks": emp.completed_tasks,
                "efficiency": round(
                    emp.completed_tasks / max(1, emp.used_budget) * 1000, 2
                ),
            }
        )

    # 按完成任务数排序
    report.sort(key=lambda x: x["completed_tasks"], reverse=True)

    return {"employees": report, "total": len(report)}


@router.get("/tasks", response_model=dict)
async def get_task_report(
    task_repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取任务统计报表"""
    stats = await task_repo.get_task_stats()

    # 获取最近完成的任务
    from opc_database.models import TaskStatus

    completed = await task_repo.get_by_status(TaskStatus.COMPLETED, limit=10)

    return {
        "summary": stats,
        "recent_completed": [
            {
                "id": t.id,
                "title": t.title,
                "assigned_to": t.assigned_to,
                "actual_cost": t.actual_cost,
            }
            for t in completed
        ],
    }
