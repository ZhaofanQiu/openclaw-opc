"""
opc-core: 任务服务 (v0.4.1)

任务业务逻辑服务 - 适配 Phase 4 异步架构

核心变更:
- assign_task() 改为异步流程，立即返回
- 后台执行 Agent 任务
- 前端轮询获取状态

作者: OpenClaw OPC Team
创建日期: 2026-03-24
更新日期: 2026-03-25
版本: 0.4.1
"""

import asyncio
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
    # 核心方法: 任务分配 (Phase 4 - 异步架构)
    # ============================================================

    async def assign_task(
        self,
        task_id: str,
        employee_id: str,
    ) -> Task:
        """
        分配任务给员工 (Phase 4: 异步架构)

        流程:
        1. 验证员工存在并绑定 Agent
        2. 验证任务存在且属于该员工
        3. 更新任务状态为 ASSIGNED
        4. 启动后台任务执行
        5. 立即返回任务 (前端轮询跟踪状态)

        Args:
            task_id: 任务ID
            employee_id: 员工ID

        Returns:
            Task: 更新后的任务对象 (status=assigned)

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

        # Step 4: 更新状态为 ASSIGNED (已分配，等待执行)
        task.status = TaskStatus.ASSIGNED.value
        task.started_at = datetime.now(timezone.utc)
        await self.task_repo.update(task)

        # Step 5: 立即更新员工状态为 working（前端可立即看到）
        employee.status = "working"
        employee.current_task_id = task.id
        await self.emp_repo.update(employee)
        print(f"[DEBUG] Employee status updated to WORKING (sync)", flush=True)

        # Step 5.5: 立即提交事务，确保数据持久化（WAL模式下必须）
        await self.task_repo.session.commit()
        print(f"[DEBUG] Transaction committed before starting background task", flush=True)

        # Step 6: 启动后台异步执行任务
        print(f"[DEBUG] Creating background task for task_id={task_id}, employee_id={employee_id}", flush=True)
        
        try:
            asyncio.create_task(
                self._execute_task_in_background(task_id, employee_id)
            )
            print(f"[DEBUG] Background task created successfully", flush=True)
        except Exception as e:
            print(f"[DEBUG] Failed to create background task: {e}", flush=True)

        return task

    async def _execute_task_in_background(
        self,
        task_id: str,
        employee_id: str,
    ) -> None:
        """
        后台执行任务 (异步)

        此方法在后台运行，不影响 assign_task 的立即返回
        """
        print(f"[DEBUG] Background task STARTED: task_id={task_id}, employee_id={employee_id}", flush=True)
        
        # 使用新的数据库 session 执行后台任务
        from opc_database import get_session
        from opc_database.repositories import TaskRepository, EmployeeRepository

        workflow_id = None
        task_id_for_callback = None

        async with get_session() as session:
            task_repo = TaskRepository(session)
            emp_repo = EmployeeRepository(session)

            try:
                # 重新获取任务和员工 (新的 session)
                task = await task_repo.get_by_id(task_id)
                employee = await emp_repo.get_by_id(employee_id)

                if not task or not employee:
                    print(f"[DEBUG] Task or employee not found", flush=True)
                    return

                print(f"[DEBUG] Found task={task.id}, employee={employee.name}", flush=True)

                # 更新为 IN_PROGRESS (执行中)
                task.status = TaskStatus.IN_PROGRESS.value
                await task_repo.update(task)
                print(f"[DEBUG] Task status updated to IN_PROGRESS", flush=True)

                # 更新员工状态
                employee.status = "working"
                employee.current_task_id = task.id
                await emp_repo.update(employee)
                print(f"[DEBUG] Employee status updated to WORKING", flush=True)

                # 构建任务分配
                assignment = self._build_task_assignment(task, employee)

                # 发送任务 (等待 Agent 回复)
                response = await self.task_caller.assign_task(assignment)

                if not response.success:
                    # 发送失败
                    task.status = TaskStatus.FAILED.value
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = f"Failed to send task to agent: {response.error}"
                    await task_repo.update(task)

                    # 重置员工状态
                    employee.status = "idle"
                    employee.current_task_id = None
                    await emp_repo.update(employee)
                    return

                # 解析 Agent 回复
                report = self.response_parser.parse(response.content)

                # 根据解析结果更新任务
                self._update_task_from_report(task, report, response)

                # 结算预算
                self._settle_budget(task, employee, report)

                # 更新员工统计
                employee.status = "idle"
                employee.current_task_id = None
                if report.is_valid and report.status == "completed":
                    employee.completed_tasks += 1
                await emp_repo.update(employee)

                # 保存工作流信息，session 关闭后触发回调
                workflow_id = task.workflow_id
                task_id_for_callback = task.id

            except Exception as e:
                # 意外错误，标记为失败
                task = await task_repo.get_by_id(task_id)
                employee = await emp_repo.get_by_id(employee_id)

                if task:
                    task.status = TaskStatus.FAILED.value
                    task.completed_at = datetime.now(timezone.utc)
                    task.result = f"Unexpected error: {str(e)}"
                    await task_repo.update(task)

                if employee:
                    employee.status = "idle"
                    employee.current_task_id = None
                    await emp_repo.update(employee)

        # session 已关闭，现在安全地触发工作流回调
        if workflow_id and task_id_for_callback:
            print(f"[DEBUG] Task {task_id_for_callback} is part of workflow {workflow_id}, triggering workflow callback", flush=True)
            await self._trigger_workflow_callback(task_id_for_callback)

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
            
            # 存储人类可读反馈（非结构化内容）
            task.feedback = report.human_readable

        else:
            # 解析失败 (Agent 未返回 OPC-REPORT 格式)
            task.status = TaskStatus.NEEDS_REVIEW.value
            task.result = (
                f"Failed to parse agent response.\n"
                f"Parse errors: {', '.join(report.errors)}\n\n"
                f"Raw response:\n{response.content[:500]}..."
            )
            # 解析失败时，将所有内容作为 feedback
            task.feedback = response.content

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

    async def _trigger_workflow_callback(self, task_id: str) -> None:
        """
        触发工作流回调

        当任务完成时，通知 WorkflowService 触发下一步
        """
        # 避免循环导入，延迟导入
        from .workflow_service import WorkflowService

        # 创建新的 session 来执行回调
        from opc_database import get_session

        async with get_session() as session:
            task_repo = TaskRepository(session)
            emp_repo = EmployeeRepository(session)

            # 创建临时的 task_service（不需要 workflow 回调）
            temp_task_service = TaskService(task_repo, emp_repo)

            workflow_service = WorkflowService(
                task_repo=task_repo,
                emp_repo=emp_repo,
                task_service=temp_task_service,
            )

            await workflow_service.on_task_completed(task_id)

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
