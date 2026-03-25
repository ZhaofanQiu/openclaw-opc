"""
opc-openclaw: 交互包

Agent 交互层（CLI 版本）

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.2
"""

from .messenger import CLIMessenger, MessageResponse, MessageType, Messenger
from .task_caller import TaskAssignment, TaskCaller, TaskResponse
from .response_parser import ResponseParser, ParsedReport, parse_response

__all__ = [
    "CLIMessenger",
    "Messenger",  # 向后兼容
    "MessageType",
    "MessageResponse",
    "TaskCaller",
    "TaskAssignment",
    "TaskResponse",
    # v0.4.2 新增
    "ResponseParser",
    "ParsedReport",
    "parse_response",
]