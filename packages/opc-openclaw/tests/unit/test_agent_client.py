"""
opc-openclaw: CLIAgentClient 单元测试 (v0.4.1)
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from opc_openclaw.client import CLIAgentClient


class TestCLIAgentClient:
    """CLIAgentClient 测试"""

    @pytest.fixture
    def client(self):
        """创建 client"""
        return CLIAgentClient(openclaw_bin="/usr/bin/openclaw")

    @pytest.fixture
    def mock_agents_list(self):
        """Mock agents list JSON 响应"""
        return [
            {"id": "main", "name": "Main Agent", "model": "kimi-coding/k2p5"},
            {"id": "opc-worker-1", "name": "Worker 1", "model": "kimi-coding/k2p5"},
            {"id": "opc-worker-2", "name": "Worker 2", "model": "kimi-coding/k2p5"},
        ]

    @pytest.mark.asyncio
    async def test_list_agents_success(self, client, mock_agents_list):
        """测试成功获取 Agent 列表"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(json.dumps(mock_agents_list).encode(), b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            agents = await client.list_agents()

        assert len(agents) == 3
        assert agents[0]["id"] == "main"
        assert agents[1]["id"] == "opc-worker-1"
        assert agents[2]["id"] == "opc-worker-2"

    @pytest.mark.asyncio
    async def test_list_agents_with_warnings(self, client, mock_agents_list):
        """测试解析包含 Config warnings 的输出"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(
                b"Config warnings:\n- some warning\n" + json.dumps(mock_agents_list).encode(),
                b""
            )
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            agents = await client.list_agents()

        assert len(agents) == 3
        assert agents[1]["id"] == "opc-worker-1"

    @pytest.mark.asyncio
    async def test_list_agents_error(self, client):
        """测试获取列表失败"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Error"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            agents = await client.list_agents()

        assert agents == []

    @pytest.mark.asyncio
    async def test_list_agents_invalid_json(self, client):
        """测试无效的 JSON 响应"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b"not valid json", b"")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            agents = await client.list_agents()

        assert agents == []

    @pytest.mark.asyncio
    async def test_get_agent_success(self, client):
        """测试成功获取 Agent"""
        with patch.object(
            client,
            "list_agents",
            new=AsyncMock(
                return_value=[
                    {"id": "opc-worker-1", "name": "Worker 1", "status": "online"}
                ]
            ),
        ):
            agent = await client.get_agent("opc-worker-1")

        assert agent is not None
        assert agent["id"] == "opc-worker-1"
        assert agent["status"] == "online"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client):
        """测试 Agent 不存在"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Agent not found"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            agent = await client.get_agent("opc-nonexistent")

        assert agent is None

    @pytest.mark.asyncio
    async def test_check_agent_health_online(self, client):
        """测试 Agent 在线"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(
                json.dumps({"id": "opc-worker-1", "status": "online"}).encode(),
                b"",
            )
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            is_healthy = await client.check_agent_health("opc-worker-1")

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_check_agent_health_offline(self, client):
        """测试 Agent 离线"""
        with patch.object(
            client,
            "list_agents",
            new=AsyncMock(
                return_value=[
                    {"id": "opc-worker-1", "status": "offline"}
                ]
            ),
        ):
            is_healthy = await client.check_agent_health("opc-worker-1")

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_check_agent_health_ping_fallback(self, client):
        """测试通过 ping 检查健康"""
        # 第一次调用 get_agent 失败
        mock_proc_get = AsyncMock()
        mock_proc_get.returncode = 1
        mock_proc_get.communicate = AsyncMock(return_value=(b"", b"Not found"))

        # 第二次调用 ping 成功
        mock_proc_ping = AsyncMock()
        mock_proc_ping.returncode = 0
        mock_proc_ping.communicate = AsyncMock(return_value=(b"pong", b""))

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=[mock_proc_get, mock_proc_ping],
        ):
            is_healthy = await client.check_agent_health("opc-worker-1")

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_get_agent_status(self, client):
        """测试获取 Agent 状态"""
        with patch.object(
            client,
            "list_agents",
            new=AsyncMock(
                return_value=[
                    {"id": "opc-worker-1", "status": "busy", "active_sessions": 2}
                ]
            ),
        ):
            status = await client.get_agent_status("opc-worker-1")

        assert status["agent_id"] == "opc-worker-1"
        assert status["status"] == "busy"
        assert status["active_sessions"] == 2

    @pytest.mark.asyncio
    async def test_get_agent_status_unknown(self, client):
        """测试获取未知 Agent 状态"""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"Not found"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            status = await client.get_agent_status("opc-unknown")

        assert status["agent_id"] == "opc-unknown"
        assert status["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_cli_not_found(self, client):
        """测试 CLI 不存在"""
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("openclaw not found"),
        ):
            agents = await client.list_agents()
            assert agents == []
