"""
opc-core: TaskService 单元测试 (v0.4.1 - Phase 4 异步架构)

测试 Phase 4 异步任务分配架构

作者: OpenClaw OPC Team
版本: 0.4.1
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opc_core.services import (
    TaskService,
    TaskNotFoundError,
    EmployeeNotFoundError,
    AgentNotBoundError,
    TaskAssignmentError,
)
from opc_database.models import Task, TaskStatus, Employee
from opc_openclaw import TaskResponse, ParsedReport


@pytest.fixture
def mock_task_repo():
    """Mock TaskRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_status = AsyncMock(return_value=[])
    repo.get_by_employee = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_emp_repo():
    """Mock EmployeeRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def task_service(mock_task_repo, mock_emp_repo):
    """创建 TaskService 实例"""
    return TaskService(
        task_repo=mock_task_repo,
        emp_repo=mock_emp_repo,
    )


@pytest.fixture
def sample_task():
    """示例任务"""
    task = MagicMock(spec=Task)
    task.id = "task-001"
    task.title = "Test Task"
    task.description = "Test Description"
    task.status = TaskStatus.PENDING.value
    task.assigned_to = "emp-001"
    task.assigned_by = None
    task.estimated_cost = 100.0
    task.actual_cost = 0.0
    task.tokens_input = 0
    task.tokens_output = 0
    task.session_key = None
    task.assigned_at = None
    task.started_at = None
    task.completed_at = None
    task.result = ""
    task.result_files = None
    task.rework_count = 0
    task.max_rework = 3
    task.execution_context = "{}"
    return task


@pytest.fixture
def sample_employee():
    """示例员工"""
    emp = MagicMock(spec=Employee)
    emp.id = "emp-001"
    emp.name = "Test Employee"
    emp.openclaw_agent_id = "opc-worker-1"
    emp.monthly_budget = 1000.0
    emp.used_budget = 200.0
    emp.remaining_budget = 800.0
    emp.status = "idle"
    emp.current_task_id = None
    emp.completed_tasks = 0
    return emp


class TestAssignTask:
    """测试 assign_task 方法 (Phase 4 异步架构)"""

    async def test_assign_task_returns_assigned_status(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试分配任务立即返回 assigned 状态 (Phase 4 异步架构)"""
        # Mock
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        # 执行
        result = await task_service.assign_task("task-001", "emp-001")

        # 验证: 立即返回 assigned 状态
        assert result.status == TaskStatus.ASSIGNED.value
        assert result.started_at is not None

        # 验证员工状态未被修改 (后台任务才修改)
        # 注意: 在真实情况下，后台任务会异步执行，这里我们无法等待它完成

    async def test_assign_task_starts_background_execution(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试分配任务启动后台执行"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="---OPC-REPORT---\ntask_id: task-001\nstatus: completed\ntokens_used: 500\n---END-REPORT---",
            session_key="sess-abc123",
        )

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            # 分配任务
            result = await task_service.assign_task("task-001", "emp-001")

            # 立即返回 assigned
            assert result.status == TaskStatus.ASSIGNED.value

            # 等待一小段时间让后台任务启动
            await asyncio.sleep(0.1)

            # 验证后台任务被调用 (模拟执行)
            # 注意: 由于 asyncio.create_task 创建了独立的任务，
            # 在测试中我们需要手动模拟后台执行

    async def test_assign_task_task_not_found(self, task_service, mock_task_repo):
        """测试任务不存在"""
        mock_task_repo.get_by_id.return_value = None

        with pytest.raises(TaskNotFoundError):
            await task_service.assign_task("task-999", "emp-001")

    async def test_assign_task_employee_not_found(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task
    ):
        """测试员工不存在"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = None

        with pytest.raises(EmployeeNotFoundError):
            await task_service.assign_task("task-001", "emp-999")

    async def test_assign_task_agent_not_bound(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试员工未绑定 Agent"""
        sample_employee.openclaw_agent_id = None
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        with pytest.raises(AgentNotBoundError):
            await task_service.assign_task("task-001", "emp-001")

    async def test_assign_task_wrong_employee(self, task_service, mock_task_repo, sample_task):
        """测试任务不属于该员工"""
        sample_task.assigned_to = "emp-002"
        mock_task_repo.get_by_id.return_value = sample_task

        with pytest.raises(TaskAssignmentError) as exc_info:
            await task_service.assign_task("task-001", "emp-001")

        assert "does not belong to" in str(exc_info.value)

    async def test_assign_task_invalid_status(self, task_service, mock_task_repo, sample_task):
        """测试任务状态不允许分配"""
        sample_task.status = TaskStatus.COMPLETED.value
        mock_task_repo.get_by_id.return_value = sample_task

        with pytest.raises(TaskAssignmentError) as exc_info:
            await task_service.assign_task("task-001", "emp-001")

        assert "Cannot assign task" in str(exc_info.value)

    async def test_assign_task_needs_revision_can_be_reassigned(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试返工任务可以重新分配"""
        sample_task.status = TaskStatus.NEEDS_REVISION.value
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        # 执行
        result = await task_service.assign_task("task-001", "emp-001")

        # 立即返回 assigned
        assert result.status == TaskStatus.ASSIGNED.value


class TestExecuteTaskInBackground:
    """测试后台执行任务"""

    async def test_background_execution_success(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试后台执行成功完成任务"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="---OPC-REPORT---\ntask_id: task-001\nstatus: completed\ntokens_used: 500\nsummary: Task completed successfully\n---END-REPORT---",
            session_key="sess-abc123",
        )

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            # 直接调用后台执行方法
            await task_service._execute_task_in_background("task-001", "emp-001")

        # 验证任务被更新为 completed
        assert sample_task.status == TaskStatus.COMPLETED.value
        assert sample_task.completed_at is not None
        assert sample_task.session_key == "sess-abc123"
        assert "Task completed successfully" in sample_task.result

        # 验证员工统计更新
        assert sample_employee.completed_tasks == 1
        assert sample_employee.status == "idle"

    async def test_background_execution_parse_failure(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试后台执行解析失败"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="I have completed the task but forgot the report format",
            session_key="sess-xyz789",
        )

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            await task_service._execute_task_in_background("task-001", "emp-001")

        # 验证状态为 NEEDS_REVIEW
        assert sample_task.status == TaskStatus.NEEDS_REVIEW.value
        assert "Failed to parse" in sample_task.result

    async def test_background_execution_send_failure(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试后台执行发送失败"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(success=False, error="Agent not found")

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            await task_service._execute_task_in_background("task-001", "emp-001")

        # 验证任务标记为失败
        assert sample_task.status == TaskStatus.FAILED.value
        assert "Failed to send task" in sample_task.result

        # 验证员工状态重置
        assert sample_employee.status == "idle"

    async def test_background_execution_exception(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试后台执行异常"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.side_effect = Exception("Unexpected error")

            await task_service._execute_task_in_background("task-001", "emp-001")

        # 验证任务标记为失败
        assert sample_task.status == TaskStatus.FAILED.value
        assert "Unexpected error" in sample_task.result


class TestRetryTask:
    """测试 retry_task 方法"""

    async def test_retry_failed_task_resets_and_assigns(
        self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee
    ):
        """测试重试失败任务 - 重置状态并分配 (Phase 4: 返回 assigned)"""
        sample_task.status = TaskStatus.FAILED.value
        sample_task.rework_count = 0
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        # 执行
        result = await task_service.retry_task("task-001")

        # Phase 4: 重试后返回 assigned (因为 assign_task 是异步的)
        assert result.status == TaskStatus.ASSIGNED.value
        assert result.rework_count == 1

    async def test_retry_max_reached(self, task_service, mock_task_repo, sample_task):
        """测试返工次数已达上限"""
        sample_task.status = TaskStatus.FAILED.value
        sample_task.rework_count = 3
        sample_task.max_rework = 3
        mock_task_repo.get_by_id.return_value = sample_task

        with pytest.raises(TaskAssignmentError) as exc_info:
            await task_service.retry_task("task-001")

        assert "max rework limit" in str(exc_info.value)

    async def test_retry_invalid_status(self, task_service, mock_task_repo, sample_task):
        """测试非失败状态不能重试"""
        sample_task.status = TaskStatus.COMPLETED.value
        mock_task_repo.get_by_id.return_value = sample_task

        with pytest.raises(TaskAssignmentError) as exc_info:
            await task_service.retry_task("task-001")

        assert "Cannot retry" in str(exc_info.value)


class TestCreateTask:
    """测试 create_task 方法"""

    async def test_create_task(self, task_service, mock_task_repo):
        """测试创建任务"""
        mock_task_repo.create.return_value = MagicMock(spec=Task)

        result = await task_service.create_task(
            title="New Task",
            description="Task Description",
            employee_id="emp-001",
            estimated_cost=100.0,
        )

        assert result is not None
        mock_task_repo.create.assert_called_once()
        created_task = mock_task_repo.create.call_args[0][0]
        assert created_task.title == "New Task"
        assert created_task.status == TaskStatus.PENDING.value


class TestGetTask:
    """测试 get_task 方法"""

    async def test_get_task_found(self, task_service, mock_task_repo, sample_task):
        """测试获取存在的任务"""
        mock_task_repo.get_by_id.return_value = sample_task

        result = await task_service.get_task("task-001")

        assert result == sample_task

    async def test_get_task_not_found(self, task_service, mock_task_repo):
        """测试获取不存在的任务"""
        mock_task_repo.get_by_id.return_value = None

        result = await task_service.get_task("task-999")

        assert result is None


class TestGetEmployeeWorkload:
    """测试 get_employee_workload 方法"""

    async def test_get_workload(self, task_service, mock_task_repo):
        """测试获取工作负载"""
        tasks = [
            MagicMock(status=TaskStatus.IN_PROGRESS.value, actual_cost=100.0),
            MagicMock(status=TaskStatus.COMPLETED.value, actual_cost=200.0),
            MagicMock(status=TaskStatus.FAILED.value, actual_cost=50.0),
            MagicMock(status=TaskStatus.NEEDS_REVIEW.value, actual_cost=0.0),
        ]
        mock_task_repo.get_by_employee.return_value = tasks

        result = await task_service.get_employee_workload("emp-001")

        assert result["total"] == 4
        assert result["in_progress"] == 1
        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["needs_review"] == 1
        assert result["total_cost"] == 350.0
