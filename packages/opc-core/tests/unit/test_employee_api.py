"""
Employee API 测试

使用 FastAPI TestClient + 依赖覆盖进行测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from opc_core import create_app
from opc_database.models import Employee, AgentStatus, PositionLevel


@pytest.fixture
def mock_employee_repo():
    """创建 Mock Employee Repository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock(return_value=[])
    repo.get_by_status = AsyncMock(return_value=[])
    repo.get_by_openclaw_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.bind_openclaw_agent = AsyncMock()
    return repo


@pytest.fixture
def test_app(mock_employee_repo):
    """创建带依赖覆盖的测试应用"""
    from opc_core.api.dependencies import get_employee_repo
    
    app = create_app()
    app.dependency_overrides[get_employee_repo] = lambda: mock_employee_repo
    return app


@pytest.fixture
def client(test_app):
    """测试客户端"""
    return TestClient(test_app)


class TestEmployeeAPI:
    """Employee API 测试类"""
    
    API_PREFIX = "/api/v1"
    
    def test_list_employees(self, client, mock_employee_repo):
        """测试获取员工列表"""
        # Mock 数据
        mock_employee = MagicMock()
        mock_employee.to_dict.return_value = {
            "id": "emp_1",
            "name": "员工1",
            "status": "idle"
        }
        mock_employee_repo.get_all.return_value = [mock_employee]
        
        response = client.get(f"{self.API_PREFIX}/employees")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["employees"]) == 1
    
    def test_list_employees_by_status(self, client, mock_employee_repo):
        """测试按状态获取员工列表"""
        mock_employee_repo.get_by_status.return_value = []
        
        response = client.get(f"{self.API_PREFIX}/employees?status=idle")
        
        assert response.status_code == 200
        mock_employee_repo.get_by_status.assert_called_once()
    
    def test_create_employee(self, client, mock_employee_repo):
        """测试创建员工"""
        mock_employee_repo.get_by_openclaw_id.return_value = None
        
        response = client.post(f"{self.API_PREFIX}/employees", json={
            "name": "新员工",
            "emoji": "🤖",
            "position_level": 2,
            "monthly_budget": 1000.0
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "新员工"
        assert "id" in data
        mock_employee_repo.create.assert_called_once()
    
    def test_create_employee_duplicate_agent(self, client, mock_employee_repo):
        """测试创建员工时使用已绑定的 Agent"""
        existing = MagicMock()
        existing.name = "老员工"
        mock_employee_repo.get_by_openclaw_id.return_value = existing
        
        response = client.post(f"{self.API_PREFIX}/employees", json={
            "name": "新员工",
            "openclaw_agent_id": "agent_bound"
        })
        
        assert response.status_code == 400
        assert "已被" in response.json()["detail"]
    
    def test_get_employee(self, client, mock_employee_repo):
        """测试获取员工详情"""
        mock_emp = MagicMock()
        mock_emp.to_dict.return_value = {
            "id": "emp_123",
            "name": "测试员工",
            "status": "idle"
        }
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.get(f"{self.API_PREFIX}/employees/emp_123")
        
        assert response.status_code == 200
        assert response.json()["name"] == "测试员工"
    
    def test_get_employee_not_found(self, client, mock_employee_repo):
        """测试获取不存在的员工"""
        mock_employee_repo.get_by_id.return_value = None
        
        response = client.get(f"{self.API_PREFIX}/employees/nonexistent")
        
        assert response.status_code == 404
    
    def test_update_employee(self, client, mock_employee_repo):
        """测试更新员工"""
        mock_emp = MagicMock()
        mock_emp.to_dict.return_value = {"id": "emp_123", "name": "更新后"}
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.put(f"{self.API_PREFIX}/employees/emp_123", json={
            "name": "更新后",
            "monthly_budget": 2000.0
        })
        
        assert response.status_code == 200
        assert "updated" in response.json()["message"].lower()
        mock_employee_repo.update.assert_called_once()
    
    def test_delete_employee(self, client, mock_employee_repo):
        """测试删除员工"""
        mock_emp = MagicMock()
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.delete(f"{self.API_PREFIX}/employees/emp_123")
        
        assert response.status_code == 200
        mock_employee_repo.delete.assert_called_once()
    
    def test_bind_agent(self, client, mock_employee_repo):
        """测试绑定 Agent"""
        mock_emp = MagicMock()
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        # Mock AgentManager 支持异步上下文管理器
        from unittest.mock import AsyncMock
        mock_manager = AsyncMock()
        mock_manager.is_available = AsyncMock(return_value=True)
        mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
        mock_manager.__aexit__ = AsyncMock(return_value=None)
        
        with patch('opc_core.api.employees.AgentManager', return_value=mock_manager):
            response = client.post(f"{self.API_PREFIX}/employees/emp_123/bind", json={
                "openclaw_agent_id": "agent_new"
            })
        
        assert response.status_code == 200
        assert response.json()["message"] == "Agent bound"
    
    def test_unbind_agent(self, client, mock_employee_repo):
        """测试解绑 Agent"""
        mock_emp = MagicMock()
        mock_emp.openclaw_agent_id = "agent_old"
        mock_emp.is_bound = "true"
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.post(f"{self.API_PREFIX}/employees/emp_123/unbind")
        
        assert response.status_code == 200
        assert mock_emp.openclaw_agent_id is None
    
    def test_get_budget(self, client, mock_employee_repo):
        """测试获取预算信息"""
        mock_emp = MagicMock()
        mock_emp.monthly_budget = 1000.0
        mock_emp.used_budget = 300.0
        mock_emp.remaining_budget = 700.0
        mock_emp.budget_percentage = 70.0
        mock_emp.mood_emoji = "😐"
        mock_employee_repo.get_by_id.return_value = mock_emp
        
        response = client.get(f"{self.API_PREFIX}/employees/emp_123/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_budget"] == 1000.0
        assert data["remaining"] == 700.0
