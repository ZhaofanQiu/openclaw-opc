"""
opc-openclaw: AgentLifecycle 单元测试
"""

from unittest.mock import AsyncMock

import pytest

from opc_openclaw.agent import AgentInfo, AgentLifecycle


class TestAgentLifecycle:
    """AgentLifecycle 测试"""

    @pytest.fixture
    def mock_client(self):
        """创建 mock client"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def lifecycle(self, mock_client):
        """创建 lifecycle"""
        return AgentLifecycle(agent_client=mock_client)

    @pytest.mark.asyncio
    async def test_discover_agents_filters_valid(self, lifecycle, mock_client):
        """测试只返回有效的 Agent"""
        mock_client.list_agents.return_value = [
            {"id": "opc-worker-1", "name": "Worker 1", "model": "kimi-coding/k2p5"},
            {"id": "opc-worker-2", "name": "Worker 2", "model": "kimi-coding/k2p5"},
            {"id": "main", "name": "Main", "model": "kimi-coding/k2p5"},  # 应该过滤
            {"id": "default", "name": "Default", "model": "kimi-coding/k2p5"},  # 应该过滤
            {"id": "other", "name": "Other", "model": "kimi-coding/k2p5"},  # 应该过滤
        ]

        agents = await lifecycle.discover_agents()

        assert len(agents) == 2
        agent_ids = [a.id for a in agents]
        assert "opc-worker-1" in agent_ids
        assert "opc-worker-2" in agent_ids
        assert "main" not in agent_ids
        assert "default" not in agent_ids
        assert "other" not in agent_ids

    @pytest.mark.asyncio
    async def test_discover_agents_empty(self, lifecycle, mock_client):
        """测试空列表"""
        mock_client.list_agents.return_value = []

        agents = await lifecycle.discover_agents()

        assert agents == []

    @pytest.mark.asyncio
    async def test_get_agent_info_valid(self, lifecycle, mock_client):
        """测试获取有效的 Agent"""
        mock_client.get_agent.return_value = {
            "id": "opc-worker-1",
            "name": "Worker 1",
            "model": "kimi-coding/k2p5",
            "status": "online",
        }

        agent = await lifecycle.get_agent_info("opc-worker-1")

        assert agent is not None
        assert agent.id == "opc-worker-1"
        assert agent.name == "Worker 1"

    @pytest.mark.asyncio
    async def test_get_agent_info_invalid_id(self, lifecycle):
        """测试获取无效的 Agent ID"""
        agent = await lifecycle.get_agent_info("main")
        assert agent is None

        agent = await lifecycle.get_agent_info("invalid_worker")
        assert agent is None

    @pytest.mark.asyncio
    async def test_is_agent_available_valid(self, lifecycle, mock_client):
        """测试检查有效的 Agent"""
        mock_client.check_agent_health.return_value = True

        is_available = await lifecycle.is_agent_available("opc-worker-1")

        assert is_available is True

    @pytest.mark.asyncio
    async def test_is_agent_available_invalid_id(self, lifecycle):
        """测试检查无效的 Agent ID"""
        is_available = await lifecycle.is_agent_available("main")
        assert is_available is False

    @pytest.mark.asyncio
    async def test_get_agent_model(self, lifecycle, mock_client):
        """测试获取 Agent 模型"""
        mock_client.get_agent.return_value = {
            "id": "opc-worker-1",
            "model": "kimi-coding/k2p5",
        }

        model = await lifecycle.get_agent_model("opc-worker-1")

        assert model == "kimi-coding/k2p5"

    @pytest.mark.asyncio
    async def test_get_agent_model_not_found(self, lifecycle, mock_client):
        """测试获取不存在的 Agent 模型"""
        mock_client.get_agent.return_value = None

        model = await lifecycle.get_agent_model("opc-worker-1")

        assert model == ""


class TestAgentInfo:
    """AgentInfo 测试"""

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": "opc-worker-1",
            "name": "Worker 1",
            "model": "kimi-coding/k2p5",
            "status": "online",
            "is_active": True,
        }
        agent = AgentInfo.from_dict(data)

        assert agent.id == "opc-worker-1"
        assert agent.name == "Worker 1"
        assert agent.model == "kimi-coding/k2p5"
        assert agent.status == "online"
        assert agent.is_active is True

    def test_from_dict_defaults(self):
        """测试默认值"""
        data = {"id": "opc-worker-1"}
        agent = AgentInfo.from_dict(data)

        assert agent.name == "opc-worker-1"  # 默认使用 id
        assert agent.model == ""
        assert agent.status == ""
        assert agent.is_active is True  # 默认活跃


class TestValidateAgentId:
    """Agent ID 验证测试"""

    @pytest.fixture
    def lifecycle(self):
        return AgentLifecycle()

    @pytest.mark.parametrize(
        "agent_id,expected",
        [
            ("opc-worker-1", True),
            ("opc-test", True),
            ("opc-dev-001", True),  # hyphen should be accepted
            ("", False),
            ("main", False),
            ("default", False),
            ("worker_1", False),
            ("opc-", False),
            ("opc-worker@1", False),
            ("opc-worker space", False),
        ],
    )
    def test_validate_agent_id(self, lifecycle, agent_id, expected):
        """测试各种 Agent ID 验证情况"""
        result = lifecycle._is_valid_agent_id(agent_id)
        assert result == expected