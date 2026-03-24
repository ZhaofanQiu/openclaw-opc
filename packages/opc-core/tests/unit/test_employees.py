"""
opc-core: 员工 API 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
from fastapi.testclient import TestClient


class TestEmployeeEndpoints:
    """员工 API 端点测试"""
    
    def test_list_employees(self, client: TestClient):
        """测试获取员工列表"""
        response = client.get("/api/v1/employees")
        assert response.status_code == 200
        data = response.json()
        assert "employees" in data
        assert "total" in data
    
    def test_create_employee_validation(self, client: TestClient):
        """测试创建员工参数验证"""
        # 缺少必填字段
        response = client.post("/api/v1/employees", json={})
        assert response.status_code == 422
        
        # 名称太短
        response = client.post("/api/v1/employees", json={"name": ""})
        assert response.status_code == 422
    
    def test_get_employee_not_found(self, client: TestClient):
        """测试获取不存在的员工"""
        response = client.get("/api/v1/employees/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_delete_employee_not_found(self, client: TestClient):
        """测试删除不存在的员工"""
        response = client.delete("/api/v1/employees/nonexistent")
        assert response.status_code == 404


class TestEmployeeBinding:
    """员工绑定测试"""
    
    def test_bind_agent_not_found(self, client: TestClient):
        """测试绑定不存在的员工"""
        response = client.post(
            "/api/v1/employees/nonexistent/bind",
            json={"openclaw_agent_id": "agent_1"}
        )
        assert response.status_code == 404
    
    def test_unbind_agent_not_found(self, client: TestClient):
        """测试解绑不存在的员工"""
        response = client.post("/api/v1/employees/nonexistent/unbind")
        assert response.status_code == 404
    
    def test_get_budget_not_found(self, client: TestClient):
        """测试获取不存在员工的预算"""
        response = client.get("/api/v1/employees/nonexistent/budget")
        assert response.status_code == 404
