"""
opc-openclaw: 交互包

Agent 交互层（CLI 版本）

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1
"""

from .messenger import CLIMessenger, MessageResponse, MessageType, Messenger
from .task_caller import TaskAssignment, TaskCaller, TaskResponse

__all__ = [
    "CLIMessenger",
    "Messenger",  # 向后兼容
    "MessageType",
    "MessageResponse",
    "TaskCaller",
    "TaskAssignment",
    "TaskResponse",
]