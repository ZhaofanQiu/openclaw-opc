"""
Task API 测试

使用 FastAPI TestClient + 依赖覆盖进行测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

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
def test_app(mock_task_repo, mock_employee_repo):
    """创建带依赖覆盖的测试应用"""
    from opc_core.api.dependencies import get_task_repo, get_employee_repo
    
    app = create_app()
    app.dependency_overrides[get_task_repo] = lambda: mock_task_repo
    app.dependency_overrides[get_employee_repo] = lambda: mock_employee_repo
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
    
    def test_assign_task(self, client, mock_task_repo, mock_employee_repo):
        """测试分配任务"""
        mock_task = MagicMock()
        mock_task.status = "pending"
        mock_task_repo.get_by_id.return_value = mock_task
        
        mock_emp = MagicMock()
        mock_emp.status = "idle"
        mock_emp.openclaw_agent_id = "agent_1"
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/assign", json={
            "employee_id": "emp_123"
        })
        
        assert response.status_code == 200
        assert response.json()["message"] == "Task assigned"
        mock_task_repo.assign_task.assert_called_once()
    
    def test_assign_task_employee_not_available(self, client, mock_task_repo, mock_employee_repo):
        """测试分配任务给不可用的员工"""
        mock_task = MagicMock()
        mock_task_repo.get_by_id.return_value = mock_task
        
        mock_emp = MagicMock()
        mock_emp.status = "working"  # 不空闲
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/assign", json={
            "employee_id": "emp_123"
        })
        
        assert response.status_code == 400
        assert "not available" in response.json()["detail"].lower()
    
    def test_complete_task(self, client, mock_task_repo, mock_employee_repo):
        """测试完成任务"""
        mock_task = MagicMock()
        mock_task.assigned_to = "emp_123"
        mock_task_repo.get_by_id.return_value = mock_task
        
        mock_emp = MagicMock()
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/complete", json={
            "result": "任务完成",
            "actual_cost": 300.0
        })
        
        assert response.status_code == 200
        mock_task_repo.complete_task.assert_called_once()
        mock_employee_repo.increment_completed_tasks.assert_called_once()
    
    def test_fail_task(self, client, mock_task_repo, mock_employee_repo):
        """测试标记任务失败"""
        mock_task = MagicMock()
        mock_task.assigned_to = "emp_123"
        mock_task_repo.get_by_id.return_value = mock_task
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/fail?reason=执行超时")
        
        assert response.status_code == 200
        mock_task_repo.fail_task.assert_called_once()
    
    def test_rework_task(self, client, mock_task_repo):
        """测试请求返工"""
        mock_task = MagicMock()
        mock_task.can_rework = True
        mock_task.rework_count = 0
        mock_task_repo.get_by_id.return_value = mock_task
        
        response = client.post(f"{self.API_PREFIX}/tasks/task_123/rework?feedback=需要修改")
        
        assert response.status_code == 200
        mock_task_repo.request_rework.assert_called_once()
