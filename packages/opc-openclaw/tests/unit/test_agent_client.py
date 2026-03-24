"""
AgentClient 测试

使用 respx 进行 HTTP Mock 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
import respx
from httpx import Response

from opc_openclaw.client.agents import AgentClient


class TestAgentClient:
    """AgentClient 测试类"""
    
    @respx.mock
    async def test_list_agents(self):
        """测试获取 Agent 列表"""
        respx.get("http://localhost:8080/api/agents").mock(
            return_value=Response(200, json={
                "agents": [
                    {"id": "agent_1", "name": "Agent 1"},
                    {"id": "agent_2", "name": "Agent 2"},
                ]
            })
        )
        
        client = AgentClient()
        agents = await client.list_agents()
        
        assert len(agents) == 2
        assert agents[0]["id"] == "agent_1"
    
    @respx.mock
    async def test_list_agents_empty(self):
        """测试获取空 Agent 列表"""
        respx.get("http://localhost:8080/api/agents").mock(
            return_value=Response(200, json={"agents": []})
        )
        
        client = AgentClient()
        agents = await client.list_agents()
        
        assert agents == []
    
    @respx.mock
    async def test_get_agent(self):
        """测试获取 Agent 详情"""
        respx.get("http://localhost:8080/api/agents/agent_123").mock(
            return_value=Response(200, json={
                "id": "agent_123",
                "name": "Test Agent",
                "status": "online"
            })
        )
        
        client = AgentClient()
        agent = await client.get_agent("agent_123")
        
        assert agent is not None
        assert agent["id"] == "agent_123"
        assert agent["name"] == "Test Agent"
    
    @respx.mock
    async def test_get_agent_not_found(self):
        """测试获取不存在的 Agent"""
        respx.get("http://localhost:8080/api/agents/nonexistent").mock(
            return_value=Response(404)
        )
        
        client = AgentClient()
        agent = await client.get_agent("nonexistent")
        
        assert agent is None
    
    @respx.mock
    async def test_get_agent_status(self):
        """测试获取 Agent 状态"""
        respx.get("http://localhost:8080/api/agents/agent_123/status").mock(
            return_value=Response(200, json={
                "agent_id": "agent_123",
                "status": "online",
                "active_sessions": 2
            })
        )
        
        client = AgentClient()
        status = await client.get_agent_status("agent_123")
        
        assert status["status"] == "online"
        assert status["active_sessions"] == 2
    
    @respx.mock
    async def test_check_agent_health_online(self):
        """测试检查在线 Agent 健康状态"""
        respx.get("http://localhost:8080/api/agents/agent_123/status").mock(
            return_value=Response(200, json={
                "agent_id": "agent_123",
                "status": "online"
            })
        )
        
        client = AgentClient()
        is_healthy = await client.check_agent_health("agent_123")
        
        assert is_healthy is True
    
    @respx.mock
    async def test_check_agent_health_offline(self):
        """测试检查离线 Agent 健康状态"""
        respx.get("http://localhost:8080/api/agents/agent_123/status").mock(
            return_value=Response(200, json={
                "agent_id": "agent_123",
                "status": "offline"
            })
        )
        
        client = AgentClient()
        is_healthy = await client.check_agent_health("agent_123")
        
        assert is_healthy is False
    
    @respx.mock
    async def test_check_agent_health_error(self):
        """测试检查 Agent 健康状态（API 错误）"""
        respx.get("http://localhost:8080/api/agents/agent_123/status").mock(
            return_value=Response(500)
        )
        
        client = AgentClient()
        is_healthy = await client.check_agent_health("agent_123")
        
        assert is_healthy is False
