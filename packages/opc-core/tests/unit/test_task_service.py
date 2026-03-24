"""
opc-core: TaskService 单元测试 (v0.4.1)

测试 Phase 2 新架构下的同步任务分配

作者: OpenClaw OPC Team
版本: 0.4.1
"""

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
    """测试 assign_task 方法 (新架构)"""

    async def test_assign_task_success(self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee):
        """测试成功分配任务"""
        # Mock
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="---OPC-REPORT---\ntask_id: task-001\nstatus: completed\ntokens_used: 500\nsummary: Task completed\n---END-REPORT---",
            session_key="sess-abc123",
            tokens_input=100,
            tokens_output=500,
        )

        with patch.object(task_service.task_caller, 'assign_task', new_callable=AsyncMock) as mock_assign:
            mock_assign.return_value = mock_response

            # 执行
            result = await task_service.assign_task("task-001", "emp-001")

        # 验证
        assert result.status == TaskStatus.COMPLETED.value
        assert result.session_key == "sess-abc123"
        assert result.tokens_output == 500
        assert "Task completed" in result.result
        assert result.completed_at is not None

        # 验证员工更新
        assert sample_employee.completed_tasks == 1
        assert sample_employee.status == "idle"
        mock_emp_repo.update.assert_called()

    async def test_assign_task_parse_failure(self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee):
        """测试解析失败 (Agent 未返回 OPC-REPORT)"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="I have completed the task but forgot the report format",
            session_key="sess-xyz789",
        )

        with patch.object(task_service.task_caller, 'assign_task', new_callable=AsyncMock) as mock_assign:
            mock_assign.return_value = mock_response

            result = await task_service.assign_task("task-001", "emp-001")

        # 验证状态为 NEEDS_REVIEW
        assert result.status == TaskStatus.NEEDS_REVIEW.value
        assert "Failed to parse" in result.result
        assert result.session_key == "sess-xyz789"

    async def test_assign_task_send_failure(self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee):
        """测试发送失败 (Agent 不可用)"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=False,
            error="Agent not found",
        )

        with patch.object(task_service.task_caller, 'assign_task', new_callable=AsyncMock) as mock_assign:
            mock_assign.return_value = mock_response

            with pytest.raises(TaskAssignmentError) as exc_info:
                await task_service.assign_task("task-001", "emp-001")

            assert "Agent not found" in str(exc_info.value)

        # 验证任务标记为失败
        assert sample_task.status == TaskStatus.FAILED.value
        mock_task_repo.update.assert_called()

    async def test_assign_task_task_not_found(self, task_service, mock_task_repo):
        """测试任务不存在"""
        mock_task_repo.get_by_id.return_value = None

        with pytest.raises(TaskNotFoundError):
            await task_service.assign_task("task-999", "emp-001")

    async def test_assign_task_employee_not_found(self, task_service, mock_task_repo, mock_emp_repo, sample_task):
        """测试员工不存在"""
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = None

        with pytest.raises(EmployeeNotFoundError):
            await task_service.assign_task("task-001", "emp-999")

    async def test_assign_task_agent_not_bound(self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee):
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

    async def test_assign_task_needs_revision(self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee):
        """测试返工任务可以重新分配"""
        sample_task.status = TaskStatus.NEEDS_REVISION.value
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="---OPC-REPORT---\ntask_id: task-001\nstatus: completed\ntokens_used: 300\n---END-REPORT---",
        )

        with patch.object(task_service.task_caller, 'assign_task', new_callable=AsyncMock) as mock_assign:
            mock_assign.return_value = mock_response

            result = await task_service.assign_task("task-001", "emp-001")

        assert result.status == TaskStatus.COMPLETED.value


class TestRetryTask:
    """测试 retry_task 方法"""

    async def test_retry_failed_task(self, task_service, mock_task_repo, mock_emp_repo, sample_task, sample_employee):
        """测试重试失败任务"""
        sample_task.status = TaskStatus.FAILED.value
        sample_task.rework_count = 0
        mock_task_repo.get_by_id.return_value = sample_task
        mock_emp_repo.get_by_id.return_value = sample_employee

        mock_response = TaskResponse(
            success=True,
            content="---OPC-REPORT---\ntask_id: task-001\nstatus: completed\n---END-REPORT---",
        )

        with patch.object(task_service.task_caller, 'assign_task', new_callable=AsyncMock) as mock_assign:
            mock_assign.return_value = mock_response

            result = await task_service.retry_task("task-001")

        assert result.status == TaskStatus.COMPLETED.value
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
