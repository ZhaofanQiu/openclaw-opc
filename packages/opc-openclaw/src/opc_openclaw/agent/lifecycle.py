"""
opc-openclaw: Agent生命周期管理

管理 OpenClaw Agent 的发现和状态管理

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1

API文档: API.md#AgentLifecycle
"""

import os
from dataclasses import dataclass
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional


class AgentState(PyEnum):
    """Agent状态"""

    ACTIVE = "active"  # 活跃可用
    PAUSED = "paused"  # 暂停
    OFFLINE = "offline"  # 离线


@dataclass
class AgentInfo:
    """Agent信息"""

    id: str
    name: str = ""
    model: str = ""
    status: str = ""
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        """从字典创建"""
        agent_id = data.get("id", "")
        return cls(
            id=agent_id,
            name=data.get("name") or agent_id,  # 默认使用 id
            model=data.get("model", ""),
            status=data.get("status", ""),
            is_active=data.get("is_active", True),
        )


class AgentLifecycle:
    """
    Agent 生命周期管理器

    注意: OpenClaw 的 Agent 由 OpenClaw 管理，
    这里提供的是发现和状态管理能力
    """

    # Agent ID 命名规范：必须以 opc_ 或 opc- 开头
    AGENT_ID_PREFIXES = ("opc_", "opc-")

    def __init__(self, agent_client=None, openclaw_bin: Optional[str] = None):
        """
        初始化

        Args:
            agent_client: AgentClient 实例（可选）
            openclaw_bin: OpenClaw CLI 路径（可选）
        """
        if agent_client is None:
            from ..client import CLIAgentClient

            self.client = CLIAgentClient(openclaw_bin=openclaw_bin)
        else:
            self.client = agent_client

    def _is_valid_agent_id(self, agent_id: str) -> bool:
        """
        检查 Agent ID 是否符合命名规范

        规则：
        1. 必须以 "opc_" 或 "opc-" 开头
        2. 不能是 "main" 或 "default"
        3. 只能包含字母、数字、下划线、连字符
        """
        if not agent_id:
            return False

        # 排除 main 和 default
        if agent_id in ("main", "default"):
            return False

        # 必须以 opc_ 或 opc- 开头
        if not any(agent_id.startswith(prefix) for prefix in self.AGENT_ID_PREFIXES):
            return False

        # 检查合法字符
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
        # 获取前缀之后的内容
        remaining = agent_id
        for prefix in self.AGENT_ID_PREFIXES:
            if agent_id.startswith(prefix):
                remaining = agent_id[len(prefix):]
                break
        
        if not remaining:
            return False

        return all(c in valid_chars for c in remaining)

    async def discover_agents(self) -> List[AgentInfo]:
        """
        发现所有可用 Agent

        只返回符合命名规范的 Agent（opc_ 开头，排除 main/default）

        Returns:
            Agent 信息列表
        """
        agents = await self.client.list_agents()

        # 过滤：只保留 opc_ 开头且排除 main/default
        filtered = []
        for agent_data in agents:
            agent_id = agent_data.get("id", "")
            if self._is_valid_agent_id(agent_id):
                filtered.append(AgentInfo.from_dict(agent_data))

        return filtered

    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """
        获取 Agent 信息

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息，不存在或不符合规范返回 None
        """
        if not self._is_valid_agent_id(agent_id):
            return None

        data = await self.client.get_agent(agent_id)
        if data:
            return AgentInfo.from_dict(data)
        return None

    async def is_agent_available(self, agent_id: str) -> bool:
        """
        检查 Agent 是否可用

        Args:
            agent_id: Agent ID

        Returns:
            是否可用
        """
        if not self._is_valid_agent_id(agent_id):
            return False

        return await self.client.check_agent_health(agent_id)

    async def get_agent_model(self, agent_id: str) -> str:
        """
        获取 Agent 使用的模型

        Args:
            agent_id: Agent ID

        Returns:
            模型名称，未知返回空字符串
        """
        info = await self.get_agent_info(agent_id)
        return info.model if info else ""

    async def close(self):
        """关闭连接（CLI 模式无连接需要关闭）"""
        pass
