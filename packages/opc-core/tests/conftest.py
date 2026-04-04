"""
opc-core: 测试配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.6
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from opc_core import create_app


@pytest.fixture
def app():
    """提供 FastAPI 应用实例"""
    return create_app()


@pytest.fixture
def client(app):
    """提供测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_employee_data():
    """Mock 员工数据"""
    return {
        "id": "emp_test123",
        "name": "测试员工",
        "emoji": "🤖",
        "position_level": 2,
        "monthly_budget": 1000.0,
        "openclaw_agent_id": "agent_test"
    }


@pytest.fixture
def mock_task_data():
    """Mock 任务数据"""
    return {
        "id": "task_test456",
        "title": "测试任务",
        "description": "这是一个测试任务",
        "priority": "normal",
        "estimated_cost": 500.0,
        "status": "pending"
    }


# ============================================
# Integration Test Fixtures
# ============================================

@pytest.fixture
def mock_employee_repo():
    """Mock Employee Repository"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    repo.get_by_id = MagicMock(return_value=None)
    repo.create = MagicMock()
    repo.update = MagicMock()
    repo.delete = MagicMock()
    repo.update_status = MagicMock()
    repo.get_by_status = MagicMock(return_value=[])
    repo.get_available_employees = MagicMock(return_value=[])
    repo.update_budget = MagicMock()
    repo.get_budget_stats = MagicMock(return_value={"total": 0, "used": 0})
    repo.bind_agent = MagicMock()
    repo.unbind_agent = MagicMock()
    repo.set_current_task = MagicMock()
    repo.clear_current_task = MagicMock()
    repo.increment_completed_tasks = MagicMock()
    return repo


@pytest.fixture
def mock_task_repo():
    """Mock Task Repository"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    repo.get_by_id = MagicMock(return_value=None)
    repo.create = MagicMock()
    repo.update = MagicMock()
    repo.delete = MagicMock()
    repo.get_by_status = MagicMock(return_value=[])
    repo.get_by_employee = MagicMock(return_value=[])
    repo.assign_task = MagicMock()
    repo.start_task = MagicMock()
    repo.complete_task = MagicMock()
    repo.fail_task = MagicMock()
    repo.request_rework = MagicMock()
    repo.get_stats = MagicMock(return_value={"total": 0, "completed": 0})
    return repo


@pytest.fixture
def mock_openclaw_client():
    """Mock OpenClaw Client"""
    client = MagicMock()
    client.agents = MagicMock()
    client.sessions = MagicMock()
    return client
