"""
opc-openclaw: Agent绑定

管理 OPC 员工与 OpenClaw Agent 的绑定关系

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#AgentBinding
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BindingResult:
    """绑定结果"""

    success: bool
    employee_id: str
    agent_id: str
    error: Optional[str] = None

    @property
    def is_bound(self) -> bool:
        """是否成功绑定"""
        return self.success and self.error is None


class AgentBinding:
    """
    Agent 绑定管理

    管理 OPC 员工与 OpenClaw Agent 的一对一绑定关系
    """

    def __init__(self, agent_client):
        """
        初始化

        Args:
            agent_client: AgentClient 实例
        """
        self.client = agent_client

    async def validate_binding(self, agent_id: str, employee_id: str) -> BindingResult:
        """
        验证绑定是否可行

        Args:
            agent_id: OpenClaw Agent ID
            employee_id: OPC 员工ID

        Returns:
            绑定验证结果
        """
        # 检查 Agent 是否存在且可用
        is_available = await self.client.check_agent_health(agent_id)

        if not is_available:
            return BindingResult(
                success=False,
                employee_id=employee_id,
                agent_id=agent_id,
                error="Agent 不可用或不存在",
            )

        return BindingResult(success=True, employee_id=employee_id, agent_id=agent_id)

    async def verify_binding(self, agent_id: str, employee_id: str) -> bool:
        """
        验证现有绑定是否有效

        Args:
            agent_id: Agent ID
            employee_id: 员工ID

        Returns:
            绑定是否有效
        """
        # 检查 Agent 是否健康
        return await self.client.check_agent_health(agent_id)
