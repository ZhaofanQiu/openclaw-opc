"""
opc-core: 任务 API 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
from fastapi.testclient import TestClient


class TestTaskEndpoints:
    """任务 API 端点测试"""
    
    def test_list_tasks(self, client: TestClient):
        """测试获取任务列表"""
        response = client.get("/api/v1/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
    
    def test_create_task_validation(self, client: TestClient):
        """测试创建任务参数验证"""
        # 缺少必填字段
        response = client.post("/api/v1/tasks", json={})
        assert response.status_code == 422
        
        # 标题太长
        response = client.post("/api/v1/tasks", json={"title": "x" * 201})
        assert response.status_code == 422
    
    def test_get_task_not_found(self, client: TestClient):
        """测试获取不存在的任务"""
        response = client.get("/api/v1/tasks/nonexistent")
        assert response.status_code == 404
    
    def test_delete_task_not_found(self, client: TestClient):
        """测试删除不存在的任务"""
        response = client.delete("/api/v1/tasks/nonexistent")
        assert response.status_code == 404


class TestTaskWorkflow:
    """任务工作流测试"""
    
    def test_assign_task_not_found(self, client: TestClient):
        """测试分配不存在的任务"""
        response = client.post(
            "/api/v1/tasks/nonexistent/assign",
            json={"employee_id": "emp_1"}
        )
        assert response.status_code == 404
    
    def test_start_task_not_found(self, client: TestClient):
        """测试开始不存在的任务"""
        response = client.post("/api/v1/tasks/nonexistent/start")
        assert response.status_code == 404
    
    def test_complete_task_not_found(self, client: TestClient):
        """测试完成不存在的任务"""
        response = client.post(
            "/api/v1/tasks/nonexistent/complete",
            json={"result": "完成"}
        )
        assert response.status_code == 404
    
    def test_rework_task_not_found(self, client: TestClient):
        """测试返工不存在的任务"""
        response = client.post("/api/v1/tasks/nonexistent/rework")
        assert response.status_code == 404
