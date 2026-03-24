"""
opc-openclaw: 会话客户端

OpenClaw Session API 客户端

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#SessionClient
"""

from typing import Any, Dict, List, Optional

from .base import BaseClient


class SessionClient(BaseClient):
    """
    OpenClaw 会话管理客户端

    提供会话(spawn)相关的API操作
    """

    async def spawn_session(
        self,
        agent_id: str,
        message: str,
        timeout: int = 300,
        label: Optional[str] = None,
        cleanup: str = "keep",
    ) -> Dict[str, Any]:
        """
        创建新的 Agent 会话并发送消息

        Args:
            agent_id: Agent ID
            message: 初始消息
            timeout: 超时时间（秒）
            label: 会话标签
            cleanup: 清理策略 ("keep" | "delete")

        Returns:
            {
                "session_key": "会话标识",
                "status": "状态",
                "response": "Agent响应"
            }
        """
        payload = {
            "agent_id": agent_id,
            "task": message,
            "timeout": timeout,
            "cleanup": cleanup,
        }
        if label:
            payload["label"] = label

        return await self.post("/api/sessions/spawn", json=payload)

    async def send_message(
        self, session_key: str, message: str, timeout: int = 300
    ) -> Dict[str, Any]:
        """
        向现有会话发送消息

        Args:
            session_key: 会话标识
            message: 消息内容
            timeout: 超时时间（秒）

        Returns:
            Agent 响应
        """
        payload = {
            "message": message,
            "timeout": timeout,
        }
        return await self.post(f"/api/sessions/{session_key}/send", json=payload)

    async def get_session_status(self, session_key: str) -> Dict[str, Any]:
        """
        获取会话状态

        Args:
            session_key: 会话标识

        Returns:
            会话状态信息
        """
        return await self.get(f"/api/sessions/{session_key}/status")

    async def get_session_messages(
        self, session_key: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取会话消息历史

        Args:
            session_key: 会话标识
            limit: 消息数量限制

        Returns:
            消息列表
        """
        response = await self.get(
            f"/api/sessions/{session_key}/messages", params={"limit": limit}
        )
        return response.get("messages", [])

    async def close_session(self, session_key: str) -> bool:
        """
        关闭会话

        Args:
            session_key: 会话标识

        Returns:
            是否成功关闭
        """
        try:
            await self.post(f"/api/sessions/{session_key}/close")
            return True
        except Exception:
            return False
