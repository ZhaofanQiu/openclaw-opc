"""
opc-core: 测试配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
