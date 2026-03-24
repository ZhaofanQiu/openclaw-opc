"""
opc-openclaw: Agent包

Agent 生命周期管理

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from .binding import AgentBinding, BindingResult
from .lifecycle import AgentInfo, AgentLifecycle, AgentState
from .manager import AgentManager

__all__ = [
    "AgentManager",
    "AgentLifecycle",
    "AgentBinding",
    "BindingResult",
    "AgentInfo",
    "AgentState",
]
