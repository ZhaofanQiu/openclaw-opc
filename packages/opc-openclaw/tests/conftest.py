"""
opc-openclaw: 测试配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio

from opc_openclaw.client import BaseClient


class MockClient(BaseClient):
    """Mock 客户端，用于测试"""
    
    def __init__(self, responses=None, **kwargs):
        super().__init__(**kwargs)
        self.responses = responses or {}
        self.call_history = []
    
    async def request(self, method: str, path: str, **kwargs):
        """Mock 请求方法"""
        self.call_history.append({
            "method": method,
            "path": path,
            "kwargs": kwargs
        })
        
        # 返回预设响应
        key = f"{method}:{path}"
        if key in self.responses:
            return self.responses[key]
        
        # 默认响应
        return {"status": "ok", "mock": True}
    
    async def close(self):
        """Mock 关闭"""
        pass


@pytest.fixture
def mock_client():
    """提供 Mock 客户端"""
    return MockClient()


@pytest.fixture
def mock_agent_list():
    """Mock Agent 列表响应"""
    return {
        "agents": [
            {"id": "agent_1", "name": "Agent 1", "model": "kimi-coding", "status": "online"},
            {"id": "agent_2", "name": "Agent 2", "model": "kimi-coding", "status": "offline"},
        ]
    }


@pytest.fixture
def mock_session_response():
    """Mock 会话创建响应"""
    return {
        "session_key": "sess_test123",
        "status": "ok",
        "response": {
            "text": "收到任务，开始执行...",
            "payloads": [{"text": "收到任务，开始执行..."}]
        },
        "meta": {
            "agentMeta": {
                "usage": {
                    "input": 100,
                    "output": 50
                }
            }
        }
    }
