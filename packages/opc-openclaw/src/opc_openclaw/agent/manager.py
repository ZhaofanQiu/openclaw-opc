"""
opc-openclaw: Agent管理器

高层Agent管理接口

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#AgentManager
"""

from typing import List, Optional

from ..client import AgentClient
from .lifecycle import AgentInfo, AgentLifecycle


class AgentManager:
    """
    Agent 管理器

    提供高层的 Agent 管理能力
    """

    def __init__(self, client: Optional[AgentClient] = None, **kwargs):
        """
        初始化管理器

        Args:
            client: AgentClient 实例（可选）
            **kwargs: 传递给 AgentClient 的参数
        """
        self.client = client or AgentClient(**kwargs)
        self.lifecycle = AgentLifecycle(self.client)

    async def list_agents(self) -> List[AgentInfo]:
        """
        列出所有 Agent

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

    async def close(self):
        """关闭连接"""
        await self.client.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
