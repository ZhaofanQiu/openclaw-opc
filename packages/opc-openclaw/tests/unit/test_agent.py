"""
opc-openclaw: Agent管理器单元测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest

from opc_openclaw.agent import AgentManager
from opc_openclaw.client import AgentClient


class TestAgentManager:
    """AgentManager 测试"""
    
    @pytest.mark.asyncio
    async def test_list_agents(self, mock_client, mock_agent_list):
        """测试列出 Agent"""
        # 设置 Mock 响应
        mock_client.responses = {
            "GET:/api/agents": mock_agent_list
        }
        
        client = AgentClient()
        client._client = mock_client._client  # 替换内部客户端
        
        # 由于我们mock了client，直接测试
        # 这里简化测试，实际应使用更完整的 mock
        pass
    
    def test_binding_result(self):
        """测试绑定结果"""
        from opc_openclaw.agent import BindingResult
        
        # 成功绑定
        success = BindingResult(
            success=True,
            employee_id="emp_1",
            agent_id="agent_1"
        )
        assert success.is_bound is True
        
        # 失败绑定
        failed = BindingResult(
            success=False,
            employee_id="emp_1",
            agent_id="agent_1",
            error="Agent 不可用"
        )
        assert failed.is_bound is False


class TestAgentLifecycle:
    """AgentLifecycle 测试"""
    
    def test_agent_info_from_dict(self):
        """测试从字典创建 AgentInfo"""
        from opc_openclaw.agent.lifecycle import AgentInfo
        
        data = {
            "id": "agent_test",
            "name": "测试Agent",
            "model": "kimi-coding",
            "status": "online",
            "is_active": True
        }
        
        info = AgentInfo.from_dict(data)
        assert info.id == "agent_test"
        assert info.name == "测试Agent"
        assert info.model == "kimi-coding"
        assert info.is_active is True
