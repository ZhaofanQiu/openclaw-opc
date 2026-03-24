"""
opc-openclaw: Agent管理器

高层Agent管理接口

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1

API文档: API.md#AgentManager
"""

from typing import List, Optional

from .lifecycle import AgentInfo, AgentLifecycle


class AgentManager:
    """
    Agent 管理器

    提供高层的 Agent 管理能力
    """

    def __init__(self, agent_client=None, openclaw_bin: Optional[str] = None):
        """
        初始化管理器

        Args:
            agent_client: AgentClient 实例（可选）
            openclaw_bin: OpenClaw CLI 路径（可选）
        """
        self.lifecycle = AgentLifecycle(
            agent_client=agent_client,
            openclaw_bin=openclaw_bin,
        )

    async def list_agents(self) -> List[AgentInfo]:
        """
        列出所有 Agent

        只返回符合命名规范的 Agent（opc_ 开头，排除 main/default）

        Returns:
            Agent 列表
        """
        return await self.lifecycle.discover_agents()

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """
        获取 Agent 详情

        Args:
            agent_id: Agent ID

        Returns:
            Agent 信息
        """
        return await self.lifecycle.get_agent_info(agent_id)

    async def is_available(self, agent_id: str) -> bool:
        """
        检查 Agent 是否可用

        Args:
            agent_id: Agent ID

        Returns:
            是否可用
        """
        return await self.lifecycle.is_agent_available(agent_id)

__all__ = ["AgentManager"]
