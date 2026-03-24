"""
opc-openclaw: 交互包

Agent 交互层

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from .messenger import MessageResponse, MessageType, Messenger

__all__ = [
    "Messenger",
    "MessageType",
    "MessageResponse",
]
