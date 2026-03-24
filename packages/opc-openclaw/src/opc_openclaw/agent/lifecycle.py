"""
opc-openclaw: Agent生命周期管理

管理 OpenClaw Agent 的创建、删除、暂停等生命周期操作

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#AgentLifecycle
"""

from dataclasses import dataclass
from enum import Enum as PyEnum
from typing import Any, Dict, Optional


class AgentState(PyEnum):
    """Agent状态"""

    ACTIVE = "active"  # 活跃可用
    PAUSED = "paused"  # 暂停
    OFFLINE = "offline"  # 离线


@dataclass
class AgentInfo:
    """Agent信息"""

    id: str
    name: str
    model: str
    status: str
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
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

    def __init__(self, agent_client):
        """
        初始化

        Args:
            agent_client: AgentClient 实例
        """
        self.client = agent_client

    async def discover_agents(self) -> list[AgentInfo]:
        """
        发现所有可用 Agent

        Returns:
            Agent 信息列表
        """
        agents = await self.client.list_agents()
        return [AgentInfo.from_dict(a) for a in agents]

    async def get_agent_info(self, agent_id: str) -> Optional[AgentInfo]:
        """
        获取 Agent 信息

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息，不存在返回 None
        """
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
