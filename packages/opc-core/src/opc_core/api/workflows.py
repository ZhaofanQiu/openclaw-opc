"""
opc-core: 工作流 API (v0.4.2)

Workflow Router - 多 Agent 串行协作

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository, TaskRepository

from ..api.dependencies import get_employee_repo, get_task_repo, verify_api_key
from ..services import (
    TaskService,
    WorkflowService,
    WorkflowStepConfig,
    WorkflowError,
    InvalidStepConfigError,
    WorkflowNotFoundError,
    ReworkLimitExceeded,
    InvalidReworkTarget,
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# ============ 数据模型 ============


class WorkflowStep(BaseModel):
    """工作流步骤配置 (v0.4.6 - 支持步骤手册)"""
    employee_id: str = Field(..., description="执行员工ID")
    title: str = Field(..., min_length=1, max_length=200, description="步骤标题")
    description: str = Field(default="", description="步骤描述")
    estimated_cost: float = Field(default=100.0, ge=0, description="预估成本")
    # v0.4.6 新增：步骤手册字段
    manual_content: Optional[str] = Field(default=None, description="步骤执行手册（Markdown格式）")
    input_requirements: Optional[str] = Field(default=None, description="输入要求说明")
    output_deliverables: Optional[str] = Field(default=None, description="输出交付物说明")


class WorkflowCreate(BaseModel):
    """创建工作流请求"""
    name: str = Field(..., min_length=1, max_length=200, description="工作流名称")
    description: Optional[str] = Field(default=None, description="工作流描述")
    steps: list[WorkflowStep] = Field(..., min_items=2, description="步骤配置列表（至少2步）")
    initial_input: dict = Field(default_factory=dict, description="初始输入数据")
    max_rework_per_step: int = Field(default=2, ge=0, le=5, description="每步最大返工次数")


class WorkflowReworkRequest(BaseModel):
    """请求返工"""
    from_task_id: str = Field(..., description="当前任务ID（发现需要返工的节点）")
    to_task_id: str = Field(..., description="目标任务ID（需要返工的节点）")
    reason: str = Field(..., min_length=1, description="返工原因")
    instructions: str = Field(..., min_length=1, description="返工指令")


# ============ 依赖注入 ============


def get_task_service(
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
) -> TaskService:
    """获取 TaskService 实例"""
    return TaskService(task_repo=repo, emp_repo=emp_repo)


def get_workflow_service(
    repo: TaskRepository = Depends(get_task_repo),
    emp_repo: EmployeeRepository = Depends(get_employee_repo),
    task_service: TaskService = Depends(get_task_service),
) -> WorkflowService:
    """获取 WorkflowService 实例"""
    return WorkflowService(
        task_repo=repo,
        emp_repo=emp_repo,
        task_service=task_service,
    )


# ============ API 路由 ============


@router.post("", response_model=dict, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    api_key: str = Depends(verify_api_key),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """
    创建工作流

    创建多步骤工作流，自动：
    1. 验证所有步骤的员工存在且绑定了 Agent
    2. 为每个步骤创建任务
    3. 建立步骤间的链表关系
    4. 触发第一个任务执行

    请求示例:
    ```json
    {
        "name": "研究报告生成",
        "description": "自动生成研究报告",
        "steps": [
            {
                "employee_id": "emp_researcher",
                "title": "研究主题",
                "description": "研究AI在医疗领域的应用",
                "estimated_cost": 200
            },
            {
                "employee_id": "emp_reviewer",
                "title": "审查结果",
                "description": "验证研究结果的准确性",
                "estimated_cost": 150
            }
        ],
        "initial_input": {"topic": "AI医疗"},
        "max_rework_per_step": 2
    }
    ```
    """
    try:
        # 转换步骤配置 (v0.4.6: 包含步骤手册字段)
        steps = [
            WorkflowStepConfig(
                employee_id=s.employee_id,
                title=s.title,
                description=s.description,
                estimated_cost=s.estimated_cost,
                # v0.4.6 新增字段
                manual_content=s.manual_content,
                input_requirements=s.input_requirements,
                output_deliverables=s.output_deliverables,
            )
            for s in data.steps
        ]

        result = await workflow_service.create_workflow(
            name=data.name,
            description=data.description,
            steps=steps,
            initial_input=data.initial_input,
            created_by="api",  # 可从 api_key 解析
            max_rework_per_step=data.max_rework_per_step,
        )

        return {
            "workflow_id": result.workflow_id,
            "first_task_id": result.first_task_id,
            "task_ids": result.task_ids,
            "status": result.status,
            "message": f"Workflow created with {len(result.task_ids)} steps",
        }

    except InvalidStepConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except WorkflowError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=dict)
async def list_workflows(
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """
    获取工作流列表

    返回所有具有 workflow_id 的任务，按 workflow_id 分组
    """
    from sqlalchemy import select, func
    from opc_database.models import Task

    # 获取所有唯一的 workflow_id
    result = await repo.session.execute(
        select(Task.workflow_id, func.count().label("task_count"))
        .where(Task.workflow_id.isnot(None))
        .group_by(Task.workflow_id)
    )

    workflows = []
    for row in result.all():
        wf_id = row.workflow_id
        task_count = row.task_count

        # 获取工作流的第一步任务信息
        head_task = await repo.get_workflow_head(wf_id)
        if head_task:
            workflows.append({
                "workflow_id": wf_id,
                "name": head_task.title.split(" - Step 1:")[0] if " - Step 1:" in head_task.title else head_task.title,
                "total_steps": head_task.total_steps,
                "task_count": task_count,
                "status": "running",  # 简化状态
                "created_at": head_task.created_at.isoformat() if head_task.created_at else None,
            })

    return {"workflows": workflows, "total": len(workflows)}


@router.get("/{workflow_id}", response_model=dict)
async def get_workflow(
    workflow_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """
    获取工作流详情

    返回工作流的所有步骤及其状态
    """
    tasks = await repo.get_by_workflow(workflow_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # 获取进度信息
    completed = sum(1 for t in tasks if t.status == "completed")
    total = tasks[0].total_steps if tasks else 0

    return {
        "workflow_id": workflow_id,
        "name": tasks[0].title.split(" - Step 1:")[0] if " - Step 1:" in tasks[0].title else tasks[0].title,
        "total_steps": total,
        "completed_steps": completed,
        "progress_percent": round(completed / total * 100, 1) if total > 0 else 0,
        "status": "completed" if completed == total else "running",
        "tasks": [t.to_dict() for t in tasks],
    }


@router.get("/{workflow_id}/progress", response_model=dict)
async def get_workflow_progress(
    workflow_id: str,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    api_key: str = Depends(verify_api_key),
):
    """获取工作流进度"""
    progress = await workflow_service.get_workflow_progress(workflow_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "workflow_id": progress.workflow_id,
        "total_steps": progress.total_steps,
        "completed_steps": progress.completed_steps,
        "current_step": progress.current_step,
        "status": progress.status,
        "progress_percent": progress.progress_percent,
    }


@router.post("/{workflow_id}/rework", response_model=dict)
async def request_rework(
    workflow_id: str,
    data: WorkflowReworkRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    api_key: str = Depends(verify_api_key),
):
    """
    请求返工

    从当前步骤返工到上游步骤
    """
    try:
        rework_task = await workflow_service.request_rework(
            from_task_id=data.from_task_id,
            to_task_id=data.to_task_id,
            reason=data.reason,
            instructions=data.instructions,
        )

        return {
            "message": "Rework requested successfully",
            "rework_task_id": rework_task.id,
            "original_task_id": rework_task.rework_target,
            "rework_count": rework_task.rework_count,
        }

    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except InvalidReworkTarget as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReworkLimitExceeded as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{workflow_id}", response_model=dict)
async def delete_workflow(
    workflow_id: str,
    repo: TaskRepository = Depends(get_task_repo),
    api_key: str = Depends(verify_api_key),
):
    """
    删除工作流

    删除工作流及其所有关联任务
    """
    tasks = await repo.get_by_workflow(workflow_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # 删除所有任务
    for task in tasks:
        await repo.delete(task)

    return {
        "message": f"Workflow {workflow_id} deleted",
        "deleted_tasks": len(tasks),
    }
