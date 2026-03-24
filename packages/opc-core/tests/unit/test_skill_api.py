"""
opc-core: Skill API 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
from fastapi.testclient import TestClient


class TestSkillAPI:
    """Skill API 测试"""
    
    def test_get_current_task_not_found(self, client: TestClient):
        """测试获取不存在的 Agent 的任务"""
        response = client.post(
            "/api/v1/skill/get-current-task",
            json={"agent_id": "nonexistent_agent"}
        )
        # 即使 Agent 不存在，也返回 has_task: false
        assert response.status_code == 200
        data = response.json()
        assert data["has_task"] is False
    
    def test_report_task_result_not_found(self, client: TestClient):
        """测试报告不存在的任务"""
        response = client.post(
            "/api/v1/skill/report-task-result",
            json={
                "agent_id": "agent_1",
                "task_id": "nonexistent_task",
                "result": "完成",
                "tokens_used": 100
            }
        )
        assert response.status_code == 404
    
    def test_get_budget_not_found(self, client: TestClient):
        """测试获取不存在 Agent 的预算"""
        response = client.post(
            "/api/v1/skill/get-budget",
            json={"agent_id": "nonexistent_agent"}
        )
        assert response.status_code == 404
    
    def test_read_manual_invalid_type(self, client: TestClient):
        """测试读取无效类型的手册"""
        response = client.post(
            "/api/v1/skill/read-manual",
            json={
                "agent_id": "agent_1",
                "manual_type": "invalid_type"
            }
        )
        assert response.status_code == 400
