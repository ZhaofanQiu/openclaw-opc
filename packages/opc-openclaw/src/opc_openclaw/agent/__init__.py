"""
opc-openclaw: Agent 管理包

Agent 生命周期和状态管理
"""

from .binding import AgentBinding, BindingResult
from .lifecycle import AgentInfo, AgentLifecycle, AgentState
from .manager import AgentManager

__all__ = [
    "AgentManager",
    "AgentLifecycle",
    "AgentBinding",
    "AgentState",
    "AgentInfo",
    "BindingResult",
]