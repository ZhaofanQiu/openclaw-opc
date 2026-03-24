"""
opc-openclaw: 消息发送器

向 Agent 发送消息

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#Messenger
"""

import uuid
from dataclasses import dataclass
from enum import Enum as PyEnum
from typing import Any, Dict, Optional

from ..client import SessionClient


class MessageType(PyEnum):
    """消息类型"""
    TASK = "task"           # 任务分配
    WAKEUP = "wakeup"       # 唤醒
    NOTIFICATION = "notification"  # 通知


@dataclass
class MessageResponse:
    """消息响应"""
    success: bool
    content: str = ""
    session_key: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None
    
    @property
    def total_tokens(self) -> int:
        """总Token消耗"""
        return self.tokens_input + self.tokens_output


class Messenger:
    """
    消息发送器
    
    向 OpenClaw Agent 发送消息
    """
    
    def __init__(self, client: Optional[SessionClient] = None, **kwargs):
        """
        初始化
        
        Args:
            client: SessionClient 实例（可选）
            **kwargs: 传递给 SessionClient 的参数
        """
        self.client = client or SessionClient(**kwargs)
    
    async def send(
        self,
        agent_id: str,
        message: str,
        message_type: MessageType = MessageType.TASK,
        timeout: int = 300,
        label: Optional[str] = None
    ) -> MessageResponse:
        """
        发送消息给 Agent
        
        Args:
            agent_id: Agent ID
            message: 消息内容
            message_type: 消息类型
            timeout: 超时时间（秒）
            label: 会话标签
            
        Returns:
            消息响应
        """
        try:
            # 创建会话并发送消息
            result = await self.client.spawn_session(
                agent_id=agent_id,
                message=message,
                timeout=timeout,
                label=label or f"opc_{message_type.value}_{uuid.uuid4().hex[:8]}",
                cleanup="keep"
            )
            
            # 解析响应
            return self._parse_response(result)
            
        except Exception as e:
            return MessageResponse(
                success=False,
                error=str(e)
            )
    
    def _parse_response(self, data: Dict[str, Any]) -> MessageResponse:
        """解析 API 响应"""
        # 提取文本内容
        content = ""
        if "response" in data:
            if isinstance(data["response"], str):
                content = data["response"]
            elif isinstance(data["response"], dict):
                content = data["response"].get("text", "")
        
        # 提取 token 信息
        tokens_input = 0
        tokens_output = 0
        
        # 从嵌套结构解析
        if "meta" in data and isinstance(data["meta"], dict):
            agent_meta = data["meta"].get("agentMeta", {})
            usage = agent_meta.get("usage", {})
            tokens_input = usage.get("input", 0)
            tokens_output = usage.get("output", 0)
        
        return MessageResponse(
            success=data.get("status") != "error",
            content=content,
            session_key=data.get("session_key"),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            error=data.get("error")
        )
    
    async def close(self):
        """关闭连接"""
        await self.client.close()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
