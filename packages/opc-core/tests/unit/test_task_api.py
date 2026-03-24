"""
Task API 测试 (v0.4.1)

使用 FastAPI TestClient + 依赖覆盖进行测试
适配新架构: 同步任务分配

作者: OpenClaw OPC Team
创建日期: 2026-03-24
更新日期: 2026-03-25
版本: 0.4.1
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from opc_core import create_app
from opc_database.models import Task, TaskStatus


@pytest.fixture
def mock_task_repo():
    """创建 Mock Task Repository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_status = AsyncMock(return_value=[])
    repo.get_by_employee = AsyncMock(return_value=[])
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.assign_task = AsyncMock()
    repo.start_task = AsyncMock()
    repo.complete_task = AsyncMock()
    repo.fail_task = AsyncMock()
    repo.request_rework = AsyncMock()
    return repo


@pytest.fixture
def mock_employee_repo():
    """创建 Mock Employee Repository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.update_status = AsyncMock()
    repo.update = AsyncMock()
    repo.increment_completed_tasks = AsyncMock()
    return repo


@pytest.fixture
def mock_task_service():
    """创建 Mock TaskService"""
    service = MagicMock()
    service.assign_task = AsyncMock()
    service.retry_task = AsyncMock()
    return service


@pytest.fixture
def test_app(mock_task_repo, mock_employee_repo, mock_task_service):
    """创建带依赖覆盖的测试应用"""
    from opc_core.api.dependencies import get_task_repo, get_employee_repo
    from opc_core.api.tasks import get_task_service
    
    app = create_app()
    app.dependency_overrides[get_task_repo] = lambda: mock_task_repo
    app.dependency_overrides[get_employee_repo] = lambda: mock_employee_repo
    app.dependency_overrides[get_task_service] = lambda: mock_task_service
    return app


@pytest.fixture
def client(test_app):
    """测试客户端"""
    return TestClient(test_app)


class TestTaskAPI:
    """Task API 测试类"""
    
    API_PREFIX = "/api/v1"
    
    def test_list_tasks(self, client, mock_task_repo):
        """测试获取任务列表"""
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "task_1",
            "title": "任务1",
            "status": "pending"
        }
        mock_task_repo.get_all.return_value = [mock_task]
        
        response = client.get(f"{self.API_PREFIX}/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    
    def test_list_tasks_by_status(self, client, mock_task_repo):
        """测试按状态获取任务列表"""
        mock_task_repo.get_by_status.return_value = []
        
        response = client.get(f"{self.API_PREFIX}/tasks?status=pending")
        
        assert response.status_code == 200
        mock_task_repo.get_by_status.assert_called_once()
    
    def test_list_tasks_by_employee(self, client, mock_task_repo):
        """测试按员工获取任务列表"""
        mock_task_repo.get_by_employee.return_value = []
        
        response = client.get(f"{self.API_PREFIX}/tasks?employee_id=emp_123")
        
        assert response.status_code == 200
    
    def test_create_task(self, client, mock_task_repo):
        """测试创建任务"""
        response = client.post(f"{self.API_PREFIX}/tasks", json={
            "title": "新任务",
            "description": "描述",
            "priority": "high",
            "estimated_cost": 500.0
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "新任务"
        assert "id" in data
        mock_task_repo.create.assert_called_once()
    
    def test_get_task(self, client, mock_task_repo):
        """测试获取任务详情"""
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "task_123",
            "title": "测试任务",
            "status": "pending"
        }
        mock_task_repo.get_by_id.return_value = mock_task
        
        response = client.get(f"{self.API_PREFIX}/tasks/task_123")
        
        assert response.status_code == 200
        assert response.json()["title"] == "测试任务"
    
    def test_get_task_not_found(self, client, mock_task_repo):
        """测试获取不存在的任务"""
        mock_task_repo.get_by_id.return_value = None
        
        response = client.get(f"{self.API_PREFIX}/tasks/nonexistent")
        
        assert response.status_code == 404
    
    def test_update_task(self, client, mock_task_repo):
        """测试更新任务"""
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {"id": "task_123", "title": "更新后"}
        mock_task_repo.get_by_id.return_value = mock_task
        
        response = client.put(f"{self.API_PREFIX}/tasks/task_123", json={
            "title": "更新后",
            "estimated_cost": 600.0
        })
        
        assert response.status_code == 200
        mock_task_repo.update.assert_called_once()
    
    def test_delete_task(self, client, mock_task_repo, mock_employee_repo):
        """测试删除任务"""
        mock_task = MagicMock()
        mock_task.assigned_to = None
        mock_task_repo.get_by_id.return_value = mock_task
        
        response = client.delete(f"{self.API_PREFIX}/tasks/task_123")
        
        assert response.status_code == 200
        mock_task_repo.delete.assert_called_once()


class TestTaskAssignNewArchitecture:
    """新架构任务分配测试"""
    
    API_PREFIX = "/api/v1"
    
    def test_assign_task_success(self, client, mock_task_service):
        """测试成功分配任务 (新架构 - 同步返回)"""
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "task_123",
            "title": "测试任务",
            "status": "completed",
            "actual_cost": 0.5
        }
        mock_task_service.assign_task.return_value = mock_task
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/assign", json={
            "employee_id": "emp_123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Task assigned and completed"
        assert "task" in data
        mock_task_service.assign_task.assert_called_once_with("task_123", "emp_123")
    
    def test_assign_task_not_found(self, client, mock_task_service):
        """测试任务不存在"""
        from opc_core.services import TaskNotFoundError
        mock_task_service.assign_task.side_effect = TaskNotFoundError("Task not found")
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_999/assign", json={
            "employee_id": "emp_123"
        })
        
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]
    
    def test_assign_agent_not_bound(self, client, mock_task_service):
        """测试员工未绑定 Agent"""
        from opc_core.services import AgentNotBoundError
        mock_task_service.assign_task.side_effect = AgentNotBoundError("No agent bound")
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/assign", json={
            "employee_id": "emp_123"
        })
        
        assert response.status_code == 400
        assert "no OpenClaw agent bound" in response.json()["detail"]
    
    def test_retry_task_success(self, client, mock_task_service):
        """测试重试任务"""
        mock_task = MagicMock()
        mock_task.to_dict.return_value = {
            "id": "task_123",
            "status": "completed",
            "rework_count": 1
        }
        mock_task_service.retry_task.return_value = mock_task
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Task retried successfully"
        mock_task_service.retry_task.assert_called_once_with("task_123")
    
    def test_retry_task_not_found(self, client, mock_task_service):
        """测试重试不存在的任务"""
        from opc_core.services import TaskNotFoundError
        mock_task_service.retry_task.side_effect = TaskNotFoundError("Task not found")
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_999/retry")
        
        assert response.status_code == 404


class TestDeprecatedRoutes:
    """已废弃路由测试"""
    
    API_PREFIX = "/api/v1"
    
    def test_complete_task_route_removed(self, client):
        """测试 complete 路由已移除"""
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/complete", json={
            "result": "任务完成"
        })
        
        assert response.status_code == 404
    
    def test_fail_task_route_removed(self, client):
        """测试 fail 路由已移除"""
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/fail?reason=超时")
        
        assert response.status_code == 404
    
    def test_rework_task_route_removed(self, client):
        """测试 rework 路由已移除"""
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/rework?feedback=修改")
        
        assert response.status_code == 404
