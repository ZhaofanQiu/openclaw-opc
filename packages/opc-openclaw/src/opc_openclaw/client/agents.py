"""
opc-openclaw: Agent客户端

OpenClaw Agent API 客户端

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#AgentClient
"""

from typing import Any, Dict, List, Optional

from .base import BaseClient


class AgentClient(BaseClient):
    """
    OpenClaw Agent 管理客户端
    
    提供 Agent 生命周期管理的API操作
    """
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有可用 Agent 列表
        
        Returns:
            Agent 列表
        """
        response = await self.get("/api/agents")
        return response.get("agents", [])
    
    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 详情
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent 详情，不存在返回 None
        """
        try:
            return await self.get(f"/api/agents/{agent_id}")
        except Exception:
            return None
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        获取 Agent 状态
        
        Args:
            agent_id: Agent ID
            
        Returns:
            {
                "agent_id": "...",
                "status": "online/offline/busy",
                "active_sessions": 0
            }
        """
        return await self.get(f"/api/agents/{agent_id}/status")
    
    async def check_agent_health(self, agent_id: str) -> bool:
        """
        检查 Agent 是否健康可用
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否可用
        """
        try:
            status = await self.get_agent_status(agent_id)
            return status.get("status") != "offline"
        except Exception:
            return False
