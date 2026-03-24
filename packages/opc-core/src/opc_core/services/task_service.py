"""
opc-core: 任务服务 (v0.4.1)

任务业务逻辑服务 - 适配 Phase 2 新架构

核心变更:
- assign_task() 改为同步流程
- 使用 ResponseParser 解析 Agent 回复
- 移除对 HTTP 回调的依赖

作者: OpenClaw OPC Team
创建日期: 2026-03-24
更新日期: 2026-03-25
版本: 0.4.1
"""

from datetime import datetime, timezone
from typing import Optional

from opc_database.repositories import EmployeeRepository, TaskRepository
from opc_database.models import Task, TaskStatus, Employee
from opc_openclaw import (
    TaskCaller,
    TaskAssignment,
    ResponseParser,
    ParsedReport,
    TaskResponse,
)


class TaskNotFoundError(Exception):
    """任务不存在"""
    pass


class EmployeeNotFoundError(Exception):
    """员工不存在"""
    pass


class AgentNotBoundError(Exception):
    """员工未绑定 Agent"""
    pass


class TaskAssignmentError(Exception):
    """任务分配失败"""
    pass


class TaskService:
    """
    任务业务服务 (v0.4.1)

    封装任务相关的业务逻辑，适配 Phase 2 新架构：
    - 同步分配任务
    - 使用 ResponseParser 解析 Agent 回复
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        emp_repo: EmployeeRepository,
    ):
        self.task_repo = task_repo
        self.emp_repo = emp_repo
        self.task_caller = TaskCaller()
        self.response_parser = ResponseParser()

    # ============================================================
    # 核心方法: 任务分配 (新架构 - 同步解析)
    # ============================================================

    async def assign_task(
        self,
        task_id: str,
        employee_id: str,
    ) -> Task:
        """
        分配任务给员工 (新架构: 同步解析)

        流程:
        1. 验证员工存在并绑定 Agent
        2. 验证任务存在且属于该员工
        3. 更新任务状态为 IN_PROGRESS
        4. 构建任务分配消息 (含预算)
        5. 调用 TaskCaller 发送任务 (同步等待 Agent 回复)
        6. 使用 ResponseParser 解析回复
        7. 根据解析结果更新任务
        8. 结算预算

        Args:
            task_id: 任务ID
            employee_id: 员工ID

        Returns:
            Task: 更新后的任务对象

        Raises:
            TaskNotFoundError: 任务不存在
            EmployeeNotFoundError: 员工不存在
            AgentNotBoundError: 员工未绑定 Agent
            TaskAssignmentError: 分配失败
        """
        # Step 1: 验证员工存在
        employee = await self._get_employee(employee_id)

        # Step 2: 验证员工绑定了 Agent
        if not employee.openclaw_agent_id:
            raise AgentNotBoundError(
                f"Employee {employee_id} has no OpenClaw agent bound"
            )

        # Step 3: 验证任务存在且属于该员工
        task = await self._validate_and_get_task(task_id, employee_id)

        # Step 4: 更新状态为 IN_PROGRESS
        task.status = TaskStatus.IN_PROGRESS.value
        task.started_at = datetime.now(timezone.utc)
        await self.task_repo.update(task)

        # 更新员工状态
        employee.status = "working"
        employee.current_task_id = task.id
        await self.emp_repo.update(employee)

        try:
            # Step 5: 构建任务分配
            assignment = self._build_task_assignment(task, employee)

            # Step 6: 发送任务 (同步等待 Agent 回复)
            response = await self.task_caller.assign_task(assignment)

            if not response.success:
                # 发送失败 (Agent 不可用等)
                task.status = TaskStatus.FAILED.value
                task.completed_at = datetime.now(timezone.utc)
                task.result = f"Failed to send task to agent: {response.error}"
                await self.task_repo.update(task)
                raise TaskAssignmentError(
                    f"Failed to assign task: {response.error}"
                )

            # Step 7: 解析 Agent 回复
            report = self.response_parser.parse(response.content)

            # Step 8: 根据解析结果更新任务
            self._update_task_from_report(task, report, response)

            # Step 9: 结算预算
            self._settle_budget(task, employee, report)

            # 更新员工统计
            employee.status = "idle"
            employee.current_task_id = None
            if report.is_valid and report.status == "completed":
                employee.completed_tasks += 1
            await self.emp_repo.update(employee)

            return task

        except Exception as e:
            # 意外错误，标记为失败
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.now(timezone.utc)
            task.result = f"Unexpected error during task assignment: {str(e)}"
            await self.task_repo.update(task)

            # 重置员工状态
            employee.status = "idle"
            employee.current_task_id = None
            await self.emp_repo.update(employee)

            raise TaskAssignmentError(f"Task assignment failed: {e}") from e

    # ============================================================
    # 辅助方法
    # ============================================================

    async def _validate_and_get_task(
        self,
        task_id: str,
        employee_id: str,
    ) -> Task:
        """验证任务存在且属于该员工"""
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        if task.assigned_to != employee_id:
            raise TaskAssignmentError(
                f"Task {task_id} does not belong to employee {employee_id}"
            )

        # 允许的状态: PENDING, ASSIGNED, NEEDS_REVISION, NEEDS_REVIEW
        allowed_statuses = [
            TaskStatus.PENDING.value,
            TaskStatus.ASSIGNED.value,
            TaskStatus.NEEDS_REVISION.value,
            TaskStatus.NEEDS_REVIEW.value,
        ]
        if task.status not in allowed_statuses:
            raise TaskAssignmentError(
                f"Cannot assign task with status {task.status}"
            )

        return task

    async def _get_employee(self, employee_id: str) -> Employee:
        """获取员工"""
        employee = await self.emp_repo.get_by_id(employee_id)
        if not employee:
            raise EmployeeNotFoundError(f"Employee {employee_id} not found")
        return employee

    def _build_task_assignment(
        self,
        task: Task,
        employee: Employee,
    ) -> TaskAssignment:
        """构建任务分配对象"""
        # 获取手册路径 (绝对路径)
        # 注意: 这里使用占位路径，实际应从 manual_service 获取
        company_manual = f"/home/user/opc/manuals/company.md"
        employee_manual = f"/home/user/opc/manuals/employees/{employee.id}.md"
        task_manual = f"/home/user/opc/manuals/tasks/{task.id}.md"

        return TaskAssignment(
            task_id=task.id,
            title=task.title,
            description=task.description,
            agent_id=employee.openclaw_agent_id,
            agent_name=employee.name,
            employee_id=employee.id,
            company_manual_path=company_manual,
            employee_manual_path=employee_manual,
            task_manual_path=task_manual,
            timeout=900,  # 15 分钟
            monthly_budget=employee.monthly_budget,
            used_budget=employee.used_budget,
            remaining_budget=employee.remaining_budget,
        )

    def _update_task_from_report(
        self,
        task: Task,
        report: ParsedReport,
        response: TaskResponse,
    ) -> None:
        """根据解析结果更新任务"""
        task.completed_at = datetime.now(timezone.utc)
        task.session_key = response.session_key

        if report.is_valid:
            # 解析成功
            status_map = {
                "completed": TaskStatus.COMPLETED.value,
                "failed": TaskStatus.FAILED.value,
                "needs_revision": TaskStatus.NEEDS_REVISION.value,
            }
            task.status = status_map.get(
                report.status,
                TaskStatus.COMPLETED.value,
            )

            # 更新 Token 消耗
            if report.tokens_used:
                task.tokens_output = report.tokens_used

            # 构建结果
            result_parts = []
            if report.summary:
                result_parts.append(report.summary)
            if report.result_files:
                result_parts.append(f"\n结果文件: {', '.join(report.result_files)}")
            task.result = "\n".join(result_parts)

            # 存储结果文件路径
            if report.result_files:
                import json
                task.result_files = json.dumps(report.result_files)

        else:
            # 解析失败 (Agent 未返回 OPC-REPORT 格式)
            task.status = TaskStatus.NEEDS_REVIEW.value
            task.result = (
                f"Failed to parse agent response.\n"
                f"Parse errors: {', '.join(report.errors)}\n\n"
                f"Raw response:\n{response.content[:500]}..."
            )

    def _settle_budget(
        self,
        task: Task,
        employee: Employee,
        report: ParsedReport,
    ) -> None:
        """结算预算"""
        tokens_used = report.tokens_used if report.is_valid else 0

        if tokens_used > 0:
            # 假设 1000 tokens = 1 OC币 (可配置)
            cost = tokens_used / 1000.0
            employee.used_budget += cost
            task.actual_cost = cost
            task.tokens_output = tokens_used

    # ============================================================
    # 其他任务方法
    # ============================================================

    async def create_task(
        self,
        title: str,
        description: str,
        employee_id: str,
        estimated_cost: float = 0.0,
    ) -> Task:
        """
        创建任务

        Args:
            title: 任务标题
            description: 任务描述
            employee_id: 员工ID
            estimated_cost: 预估成本

        Returns:
            Task: 创建的任务
        """
        import uuid

        task = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            title=title,
            description=description,
            status=TaskStatus.PENDING.value,
            assigned_to=employee_id,
            estimated_cost=estimated_cost,
            created_at=datetime.now(timezone.utc),
        )
        return await self.task_repo.create(task)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return await self.task_repo.get_by_id(task_id)

    async def get_task_with_employee(
        self, task_id: str
    ) -> tuple[Optional[Task], Optional[Employee]]:
        """
        获取任务及分配的员工信息

        Args:
            task_id: 任务ID

        Returns:
            (Task, Employee) 或 (None, None)
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None, None

        employee = None
        if task.assigned_to:
            employee = await self.emp_repo.get_by_id(task.assigned_to)

        return task, employee

    async def get_pending_tasks(self, limit: int = 100) -> list[Task]:
        """
        获取待处理任务

        Args:
            limit: 数量限制

        Returns:
            任务列表
        """
        return await self.task_repo.get_by_status(TaskStatus.PENDING.value, limit)

    async def retry_task(self, task_id: str) -> Task:
        """
        重试失败的任务

        Args:
            task_id: 任务ID

        Returns:
            Task: 重试后的任务
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")

        retryable_statuses = [
            TaskStatus.FAILED.value,
            TaskStatus.NEEDS_REVISION.value,
            TaskStatus.NEEDS_REVIEW.value,
        ]
        if task.status not in retryable_statuses:
            raise TaskAssignmentError(
                f"Cannot retry task with status {task.status}"
            )

        # 检查返工次数
        if task.rework_count >= task.max_rework:
            raise TaskAssignmentError(
                f"Task {task_id} has reached max rework limit ({task.max_rework})"
            )

        # 重置状态并重新分配
        task.status = TaskStatus.PENDING.value
        task.rework_count += 1
        task.result = ""
        task.completed_at = None
        await self.task_repo.update(task)

        # 重新分配
        return await self.assign_task(task_id, task.assigned_to)

    async def get_employee_workload(self, employee_id: str) -> dict:
        """
        获取员工工作负载

        Args:
            employee_id: 员工ID

        Returns:
            负载统计
        """
        tasks = await self.task_repo.get_by_employee(employee_id)

        in_progress = [
            t for t in tasks if t.status == TaskStatus.IN_PROGRESS.value
        ]
        completed = [
            t for t in tasks if t.status == TaskStatus.COMPLETED.value
        ]
        failed = [t for t in tasks if t.status == TaskStatus.FAILED.value]
        needs_review = [
            t for t in tasks if t.status == TaskStatus.NEEDS_REVIEW.value
        ]

        return {
            "total": len(tasks),
            "in_progress": len(in_progress),
            "completed": len(completed),
            "failed": len(failed),
            "needs_review": len(needs_review),
            "total_cost": sum(t.actual_cost for t in tasks),
        }
