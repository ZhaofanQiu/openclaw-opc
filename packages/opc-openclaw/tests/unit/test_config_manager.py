"""
opc-openclaw: ConfigManager 单元测试
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from opc_openclaw.config import AgentConfig, ConfigError, ConfigManager


class TestConfigManager:
    """ConfigManager 测试"""

    def test_init_default_path(self):
        """测试默认配置路径"""
        manager = ConfigManager()
        assert manager.config_path == Path.home() / ".openclaw" / "config"

    def test_init_custom_path(self, temp_config_dir):
        """测试自定义配置路径"""
        custom_path = temp_config_dir / "custom_config.yaml"
        manager = ConfigManager(str(custom_path))
        assert manager.config_path == custom_path

    def test_load_config_not_exists(self, temp_config_dir):
        """测试配置文件不存在时返回空字典"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        config = manager._load_config()
        assert config == {}

    def test_load_config_exists(self, temp_config_dir, sample_config):
        """测试加载现有配置"""
        config_path = temp_config_dir / "config"
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_path))
        config = manager._load_config()
        assert config == sample_config

    def test_save_config(self, temp_config_dir):
        """测试保存配置"""
        config_path = temp_config_dir / "config"
        manager = ConfigManager(str(config_path))

        test_config = {"agents": {"opc-test": {"name": "Test"}}}
        manager._save_config(test_config)

        assert config_path.exists()
        with open(config_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded == test_config

    def test_save_config_backup(self, temp_config_dir):
        """测试保存配置时自动备份"""
        config_path = temp_config_dir / "config"

        # 先创建原配置
        with open(config_path, "w") as f:
            yaml.dump({"agents": {"old": {}}}, f)

        manager = ConfigManager(str(config_path))
        manager._save_config({"agents": {"new": {}}})

        # 检查备份存在
        backup_path = config_path.with_suffix(".config.backup")
        assert backup_path.exists()


class TestValidateAgentId:
    """Agent ID 验证测试"""

    @pytest.fixture
    def manager(self, temp_config_dir):
        return ConfigManager(str(temp_config_dir / "config"))

    @pytest.mark.parametrize(
        "agent_id,expected_valid,expected_error",
        [
            ("opc-worker-1", True, ""),
            ("opc-test-agent", True, ""),
            ("opc-dev-001", True, ""),
            ("", False, "cannot be empty"),
            ("main", False, "reserved"),
            ("default", False, "reserved"),
            ("worker_1", False, 'must start with "opc-"'),
            ("opc-", False, 'cannot be just "opc-"'),
            ("opc-worker@1", False, "Invalid characters"),
            ("opc-worker 1", False, "Invalid characters"),
        ],
    )
    def test_validate_agent_id(self, manager, agent_id, expected_valid, expected_error):
        """测试各种 Agent ID 验证情况"""
        is_valid, error_msg = manager.validate_agent_id(agent_id)
        assert is_valid == expected_valid
        if expected_error:
            assert expected_error in error_msg


class TestReadAgents:
    """读取 Agent 测试"""

    def test_read_agents_filters_correctly(self, temp_config_dir, sample_config):
        """测试只返回 opc- 开头的 Agent"""
        config_path = temp_config_dir / "config"
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_path))
        agents = manager.read_agents()

        # 只返回 opc- 开头的
        agent_ids = [a.id for a in agents]
        assert "opc-worker-1" in agent_ids
        assert "opc-worker-2" in agent_ids
        assert "main" not in agent_ids
        assert "default" not in agent_ids
        assert "other_agent" not in agent_ids

    def test_read_agents_empty_config(self, temp_config_dir):
        """测试空配置返回空列表"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        agents = manager.read_agents()
        assert agents == []

    def test_get_agent_valid(self, temp_config_dir, sample_config):
        """测试获取存在的 Agent"""
        config_path = temp_config_dir / "config"
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_path))
        agent = manager.get_agent("opc-worker-1")

        assert agent is not None
        assert agent.id == "opc-worker-1"
        assert agent.name == "Worker One"
        assert agent.model == "kimi-coding/k2p5"

    def test_get_agent_invalid_id(self, temp_config_dir, sample_config):
        """测试获取不符合命名规范的 Agent 返回 None"""
        config_path = temp_config_dir / "config"
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_path))
        assert manager.get_agent("main") is None
        assert manager.get_agent("other_agent") is None


class TestAddAgent:
    """添加 Agent 测试"""

    def test_add_agent_success(self, temp_config_dir):
        """测试成功添加 Agent"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = manager.add_agent(
            agent_id="opc-new-worker",
            model="kimi-coding/k2p5",
            name="New Worker",
            description="A new worker",
        )

        assert success is True
        assert "added successfully" in msg
        assert "restart" in msg.lower()

        # 验证配置已保存
        agent = manager.get_agent("opc-new-worker")
        assert agent is not None
        assert agent.name == "New Worker"

    def test_add_agent_invalid_id(self, temp_config_dir):
        """测试添加无效 ID 的 Agent"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = manager.add_agent(
            agent_id="invalid_worker",  # 不以 opc- 开头
            model="kimi-coding/k2p5",
        )

        assert success is False
        assert "must start with" in msg

    def test_add_agent_already_exists(self, temp_config_dir, sample_config):
        """测试添加已存在的 Agent"""
        config_path = temp_config_dir / "config"
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_path))
        success, msg = manager.add_agent(
            agent_id="opc-worker-1",  # 已存在
            model="kimi-coding/k2p5",
        )

        assert success is False
        assert "already exists" in msg


class TestRemoveAgent:
    """移除 Agent 测试"""

    def test_remove_agent_success(self, temp_config_dir, sample_config):
        """测试成功移除 Agent"""
        config_path = temp_config_dir / "config"
        with open(config_path, "w") as f:
            yaml.dump(sample_config, f)

        manager = ConfigManager(str(config_path))
        success, msg = manager.remove_agent("opc-worker-1")

        assert success is True
        assert "removed successfully" in msg
        assert manager.get_agent("opc-worker-1") is None

    def test_remove_agent_not_exists(self, temp_config_dir):
        """测试移除不存在的 Agent"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = manager.remove_agent("opc-nonexistent")

        assert success is False
        assert "does not exist" in msg

    def test_remove_agent_invalid_id(self, temp_config_dir):
        """测试移除无效 ID 的 Agent"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = manager.remove_agent("main")

        assert success is False
        assert "Invalid Agent ID" in msg


@pytest.mark.asyncio
class TestRestartGateway:
    """重启 Gateway 测试"""

    async def test_restart_gateway_requires_confirmation(self, temp_config_dir):
        """测试重启需要确认"""
        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = await manager.request_restart_gateway(force=False)

        assert success is False
        assert "CONFIRMATION_REQUIRED" in msg

    @patch("asyncio.create_subprocess_exec")
    async def test_restart_gateway_success(self, mock_exec, temp_config_dir):
        """测试成功重启"""
        # Mock 子进程
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"OK", b""))
        mock_exec.return_value = mock_proc

        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = await manager.request_restart_gateway(force=True)

        assert success is True
        assert "restarted successfully" in msg

    @patch("asyncio.create_subprocess_exec")
    async def test_restart_gateway_cli_not_found(self, mock_exec, temp_config_dir):
        """测试 CLI 不存在"""
        mock_exec.side_effect = FileNotFoundError("openclaw not found")

        manager = ConfigManager(str(temp_config_dir / "config"))
        success, msg = await manager.request_restart_gateway(force=True)

        assert success is False
        assert "not found" in msg