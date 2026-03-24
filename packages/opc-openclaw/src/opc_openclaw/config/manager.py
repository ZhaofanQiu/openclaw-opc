"""
opc-openclaw: Config 管理器

管理 OpenClaw 配置文件 (~/.openclaw/config)

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1
"""

import asyncio
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class AgentConfig:
    """Agent 配置"""

    id: str
    name: str
    model: str
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, agent_id: str, data: Dict[str, Any]) -> "AgentConfig":
        """从字典创建"""
        return cls(
            id=agent_id,
            name=data.get("name", agent_id),
            model=data.get("model", ""),
            description=data.get("description", ""),
            config=data.get("config", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "name": self.name,
            "model": self.model,
        }
        if self.description:
            result["description"] = self.description
        if self.config:
            result["config"] = self.config
        return result


class ConfigManager:
    """
    OpenClaw Config 管理器

    管理 ~/.openclaw/config 文件的读取和修改
    """

    CONFIG_PATH = Path.home() / ".openclaw" / "config"
    AGENT_ID_PREFIX = "opc-"  # Agent ID 必须以此前缀开头（连字符）

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化

        Args:
            config_path: 配置文件路径，默认 ~/.openclaw/config
        """
        self.config_path = Path(config_path) if config_path else self.CONFIG_PATH

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            配置字典
        """
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}")

    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        保存配置文件

        Args:
            config: 配置字典
        """
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 备份原配置
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix(".config.backup")
            shutil.copy2(self.config_path, backup_path)

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise ConfigError(f"Failed to save config: {e}")

    def validate_agent_id(self, agent_id: str) -> Tuple[bool, str]:
        """
        验证 Agent ID 是否符合命名规范

        规则：
        1. 必须以 "opc_" 开头
        2. 不能是 "main" 或 "default"
        3. 只能包含字母、数字、下划线、连字符、点

        Args:
            agent_id: Agent ID

        Returns:
            (is_valid, error_message)
        """
        if not agent_id:
            return False, "Agent ID cannot be empty"

        # 排除 main 和 default
        if agent_id in ("main", "default"):
            return False, f'Agent ID "{agent_id}" is reserved'

        # 必须以 opc_ 开头
        if not agent_id.startswith(self.AGENT_ID_PREFIX):
            return (
                False,
                f'Agent ID must start with "{self.AGENT_ID_PREFIX}" (e.g., opc_worker_001)',
            )

        # 检查合法字符
        valid_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        )
        remaining = agent_id[len(self.AGENT_ID_PREFIX) :]
        if not remaining:
            return False, f'Agent ID cannot be just "{self.AGENT_ID_PREFIX}"'

        invalid_chars = [c for c in remaining if c not in valid_chars]
        if invalid_chars:
            return (
                False,
                f'Invalid characters in Agent ID: {invalid_chars}. Only letters, numbers, underscore, and hyphen are allowed',
            )

        return True, ""

    def read_agents(self) -> List[AgentConfig]:
        """
        读取所有 Agent 配置

        只返回符合命名规范的 Agent（opc_ 开头，排除 main/default）

        Returns:
            Agent 配置列表
        """
        config = self._load_config()
        agents_config = config.get("agents", {})

        agents = []
        for agent_id, agent_data in agents_config.items():
            # 只保留符合命名规范的 Agent
            is_valid, _ = self.validate_agent_id(agent_id)
            if is_valid and isinstance(agent_data, dict):
                agents.append(AgentConfig.from_dict(agent_id, agent_data))

        return agents

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """
        获取指定 Agent 配置

        Args:
            agent_id: Agent ID

        Returns:
            Agent 配置，不存在或不符合规范返回 None
        """
        # 验证命名规范
        is_valid, _ = self.validate_agent_id(agent_id)
        if not is_valid:
            return None

        config = self._load_config()
        agents_config = config.get("agents", {})
        agent_data = agents_config.get(agent_id)

        if isinstance(agent_data, dict):
            return AgentConfig.from_dict(agent_id, agent_data)
        return None

    def add_agent(
        self,
        agent_id: str,
        model: str,
        name: Optional[str] = None,
        description: str = "",
        **kwargs,
    ) -> Tuple[bool, str]:
        """
        添加新 Agent 到配置

        Args:
            agent_id: Agent ID（必须以 opc_ 开头）
            model: 模型名称
            name: 显示名称（可选，默认使用 agent_id）
            description: 描述（可选）
            **kwargs: 其他配置

        Returns:
            (success, message)
            message 包含操作结果和重启提示
        """
        # 验证命名规范
        is_valid, error_msg = self.validate_agent_id(agent_id)
        if not is_valid:
            return False, f"Invalid Agent ID: {error_msg}"

        # 检查是否已存在
        if self.get_agent(agent_id):
            return False, f'Agent "{agent_id}" already exists'

        # 加载配置
        config = self._load_config()
        if "agents" not in config:
            config["agents"] = {}

        # 创建 Agent 配置
        agent_config = {
            "name": name or agent_id,
            "model": model,
        }
        if description:
            agent_config["description"] = description
        if kwargs:
            agent_config["config"] = kwargs

        # 添加到配置
        config["agents"][agent_id] = agent_config

        # 保存配置
        try:
            self._save_config(config)
            return (
                True,
                f'Agent "{agent_id}" added successfully. '
                f'⚠️  You need to restart OpenClaw Gateway for changes to take effect. '
                f'Use request_restart_gateway() to restart.',
            )
        except ConfigError as e:
            return False, str(e)

    def remove_agent(self, agent_id: str) -> Tuple[bool, str]:
        """
        从配置中移除 Agent

        Args:
            agent_id: Agent ID

        Returns:
            (success, message)
        """
        # 验证命名规范
        is_valid, error_msg = self.validate_agent_id(agent_id)
        if not is_valid:
            return False, f"Invalid Agent ID: {error_msg}"

        # 检查是否存在
        if not self.get_agent(agent_id):
            return False, f'Agent "{agent_id}" does not exist'

        # 加载配置
        config = self._load_config()
        if "agents" not in config:
            return False, "No agents configured"

        # 移除 Agent
        del config["agents"][agent_id]

        # 保存配置
        try:
            self._save_config(config)
            return (
                True,
                f'Agent "{agent_id}" removed successfully. '
                f'⚠️  You need to restart OpenClaw Gateway for changes to take effect. '
                f'Use request_restart_gateway() to restart.',
            )
        except ConfigError as e:
            return False, str(e)

    async def request_restart_gateway(
        self, force: bool = False
    ) -> Tuple[bool, str]:
        """
        请求重启 OpenClaw Gateway

        ⚠️ 重要：重启会中断所有正在进行的对话！

        流程：
        1. 检查是否有活跃的会话（如果 CLI 支持）
        2. 向用户展示确认提示
        3. 用户确认后才执行重启

        Args:
            force: 是否跳过确认（仅用于自动化脚本）

        Returns:
            (success, message)
        """
        if not force:
            # 这里应该向用户展示确认提示
            # 由于这是程序化接口，返回需要确认的消息
            return (
                False,
                "RESTART_CONFIRMATION_REQUIRED: "
                "Restarting OpenClaw Gateway will interrupt all active conversations. "
                "Call request_restart_gateway(force=True) to confirm and restart.",
            )

        # 执行重启
        openclaw_bin = os.getenv("OPENCLAW_BIN", "openclaw")
        cmd = [openclaw_bin, "gateway", "restart"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                return False, f"Failed to restart gateway: {error_msg}"

            return True, "OpenClaw Gateway restarted successfully"

        except FileNotFoundError:
            return False, f"OpenClaw CLI not found: {openclaw_bin}"
        except Exception as e:
            return False, f"Error restarting gateway: {e}"

    def agent_exists(self, agent_id: str) -> bool:
        """
        检查 Agent 是否存在

        Args:
            agent_id: Agent ID

        Returns:
            是否存在
        """
        return self.get_agent(agent_id) is not None

    def list_agent_ids(self) -> List[str]:
        """
        获取所有 Agent ID 列表

        Returns:
            Agent ID 列表（只包含 opc_ 开头的）
        """
        agents = self.read_agents()
        return [agent.id for agent in agents]


class ConfigError(Exception):
    """配置错误"""
    pass


__all__ = ["ConfigManager", "AgentConfig", "ConfigError"]