"""
opc-core: Tasks API 测试 (v0.4.1)

测试任务管理 API 路由

作者: OpenClaw OPC Team
版本: 0.4.1
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from opc_core import create_app
from opc_database.models import Task, TaskStatus


@pytest.fixture
def mock_task_service():
    """Mock TaskService"""
    service = MagicMock()
    service.assign_task = AsyncMock()
    service.retry_task = AsyncMock()
    service.create_task = AsyncMock()
    service.get_task = AsyncMock()
    return service


@pytest.fixture
def mock_task_repo():
    """Mock TaskRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_status = AsyncMock(return_value=[])
    repo.get_by_employee = AsyncMock(return_value=[])
    repo.get_all = AsyncMock(return_value=[])
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_emp_repo():
    """Mock EmployeeRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def client(mock_task_repo, mock_emp_repo, mock_task_service):
    """创建测试客户端"""
    app = create_app()

    # Mock 依赖
    from opc_core.api.dependencies import get_task_repo, get_employee_repo, verify_api_key
    from opc_core.api.tasks import get_task_service

    def override_task_repo():
        return mock_task_repo

    def override_emp_repo():
        return mock_emp_repo

    def override_api_key():
        return "test-api-key"

    def override_task_service():
        return mock_task_service

    app.dependency_overrides[get_task_repo] = override_task_repo
    app.dependency_overrides[get_employee_repo] = override_emp_repo
    app.dependency_overrides[verify_api_key] = override_api_key
    app.dependency_overrides[get_task_service] = override_task_service

    # 创建客户端并设置默认 headers (Bearer token)
    test_client = TestClient(app)
    test_client.headers = {"Authorization": "Bearer test-api-key"}
    return test_client


@pytest.fixture
def sample_task():
    """示例任务数据"""
    task = MagicMock(spec=Task)
    task.id = "task-001"
    task.title = "Test Task"
    task.description = "Test Description"
    task.status = TaskStatus.COMPLETED.value
    task.priority = "normal"
    task.assigned_to = "emp-001"
    task.estimated_cost = 100.0
    task.actual_cost = 50.0
    task.tokens_input = 100
    task.tokens_output = 500
    task.session_key = "sess-abc123"
    task.created_at = None
    task.started_at = None
    task.completed_at = None
    task.result = "Task completed successfully"
    task.rework_count = 0
    task.max_rework = 3
    task.to_dict.return_value = {
        "id": "task-001",
        "title": "Test Task",
        "status": "completed",
    }
    return task


class TestAssignTask:
    """测试任务分配端点 (新架构 - 同步返回)"""

    def test_assign_task_success(self, client, mock_task_service, sample_task):
        """测试成功分配任务 (同步返回)"""
        mock_task_service.assign_task.return_value = sample_task

        response = client.post(
            "/api/v1/tasks/task-001/assign",
            json={"employee_id": "emp-001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Task assigned and completed"
        assert "task" in data
        assert data["task"]["status"] == "completed"

    def test_assign_task_not_found(self, client, mock_task_service):
        """测试任务不存在"""
        from opc_core.services import TaskNotFoundError
        mock_task_service.assign_task.side_effect = TaskNotFoundError("Task not found")

        response = client.post(
            "/api/v1/tasks/task-999/assign",
            json={"employee_id": "emp-001"},
        )

        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_assign_employee_not_found(self, client, mock_task_service):
        """测试员工不存在"""
        from opc_core.services import EmployeeNotFoundError
        mock_task_service.assign_task.side_effect = EmployeeNotFoundError("Employee not found")

        response = client.post(
            "/api/v1/tasks/task-001/assign",
            json={"employee_id": "emp-999"},
        )

        assert response.status_code == 404
        assert "Employee not found" in response.json()["detail"]

    def test_assign_agent_not_bound(self, client, mock_task_service):
        """测试员工未绑定 Agent"""
        from opc_core.services import AgentNotBoundError
        mock_task_service.assign_task.side_effect = AgentNotBoundError("No agent bound")

        response = client.post(
            "/api/v1/tasks/task-001/assign",
            json={"employee_id": "emp-001"},
        )

        assert response.status_code == 400
        assert "no OpenClaw agent bound" in response.json()["detail"]

    def test_assign_task_error(self, client, mock_task_service):
        """测试分配失败"""
        from opc_core.services import TaskAssignmentError
        mock_task_service.assign_task.side_effect = TaskAssignmentError("Assignment failed")

        response = client.post(
            "/api/v1/tasks/task-001/assign",
            json={"employee_id": "emp-001"},
        )

        assert response.status_code == 500
        assert "Assignment failed" in response.json()["detail"]


class TestRetryTask:
    """测试任务重试端点"""

    def test_retry_task_success(self, client, mock_task_service, sample_task):
        """测试成功重试任务"""
        mock_task_service.retry_task.return_value = sample_task

        response = client.post("/api/v1/tasks/task-001/retry")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Task retried successfully"
        assert "task" in data

    def test_retry_task_not_found(self, client, mock_task_service):
        """测试任务不存在"""
        from opc_core.services import TaskNotFoundError
        mock_task_service.retry_task.side_effect = TaskNotFoundError("Task not found")

        response = client.post("/api/v1/tasks/task-999/retry")

        assert response.status_code == 404

    def test_retry_max_reached(self, client, mock_task_service):
        """测试返工次数已达上限"""
        from opc_core.services import TaskAssignmentError
        mock_task_service.retry_task.side_effect = TaskAssignmentError("Max rework reached")

        response = client.post("/api/v1/tasks/task-001/retry")

        assert response.status_code == 400
        assert "Max rework reached" in response.json()["detail"]


class TestListTasks:
    """测试任务列表端点"""

    def test_list_tasks(self, client, mock_task_repo):
        """测试获取任务列表"""
        response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data

    def test_list_tasks_by_status(self, client, mock_task_repo):
        """测试按状态筛选"""
        response = client.get("/api/v1/tasks?status=pending")

        assert response.status_code == 200
        mock_task_repo.get_by_status.assert_called_once()

    def test_list_tasks_by_employee(self, client, mock_task_repo):
        """测试按员工筛选"""
        response = client.get("/api/v1/tasks?employee_id=emp-001")

        assert response.status_code == 200
        mock_task_repo.get_by_employee.assert_called_once()


class TestCreateTask:
    """测试创建任务端点"""

    def test_create_task(self, client, mock_task_repo):
        """测试创建任务"""
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task_abc123"  # 匹配实际生成的格式
        mock_task.title = "New Task"
        mock_task_repo.create.return_value = mock_task

        response = client.post(
            "/api/v1/tasks",
            json={
                "title": "New Task",
                "description": "Task description",
                "priority": "high",
                "estimated_cost": 200.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data  # 只检查 id 存在，不检查具体值
        assert data["title"] == "New Task"
        assert data["message"] == "Task created"


class TestGetTask:
    """测试获取任务详情端点"""

    def test_get_task_found(self, client, mock_task_repo, sample_task):
        """测试获取存在的任务"""
        mock_task_repo.get_by_id.return_value = sample_task

        response = client.get("/api/v1/tasks/task-001")

        assert response.status_code == 200
        assert response.json()["id"] == "task-001"

    def test_get_task_not_found(self, client, mock_task_repo):
        """测试获取不存在的任务"""
        mock_task_repo.get_by_id.return_value = None

        response = client.get("/api/v1/tasks/task-999")

        assert response.status_code == 404


class TestUpdateTask:
    """测试更新任务端点"""

    def test_update_task(self, client, mock_task_repo, sample_task):
        """测试更新任务"""
        mock_task_repo.get_by_id.return_value = sample_task

        response = client.put(
            "/api/v1/tasks/task-001",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        assert "Task updated" in response.json()["message"]


class TestDeleteTask:
    """测试删除任务端点"""

    def test_delete_task(self, client, mock_task_repo, sample_task):
        """测试删除任务"""
        mock_task_repo.get_by_id.return_value = sample_task

        response = client.delete("/api/v1/tasks/task-001")

        assert response.status_code == 200
        assert "Task deleted" in response.json()["message"]


class TestCancelTask:
    """测试取消任务端点"""

    def test_cancel_task(self, client, mock_task_repo, sample_task):
        """测试取消待处理任务"""
        sample_task.status = TaskStatus.PENDING.value
        mock_task_repo.get_by_id.return_value = sample_task

        response = client.post("/api/v1/tasks/task-001/cancel")

        assert response.status_code == 200
        assert "Task cancelled" in response.json()["message"]

    def test_cancel_task_invalid_status(self, client, mock_task_repo, sample_task):
        """测试取消非待处理任务失败"""
        sample_task.status = TaskStatus.COMPLETED.value
        mock_task_repo.get_by_id.return_value = sample_task

        response = client.post("/api/v1/tasks/task-001/cancel")

        assert response.status_code == 400
