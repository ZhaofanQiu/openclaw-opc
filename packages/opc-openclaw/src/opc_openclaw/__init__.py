"""
opc-openclaw: OpenClaw 功能封装模块

OpenClaw OPC v0.4.0 - OpenClaw 集成模块

提供 OpenClaw API 客户端、Agent 生命周期管理和消息交互能力。

使用示例:
    from opc_openclaw import AgentManager, Messenger

    # Agent 管理
    async with AgentManager() as manager:
        agents = await manager.list_agents()

    # 消息交互
    async with Messenger() as messenger:
        response = await messenger.send("agent_1", "任务内容")

作者: OpenClaw OPC Team
版本: 0.4.0
"""

__version__ = "0.4.0"

from .agent import (
    AgentBinding,
    AgentLifecycle,
    AgentManager,
    BindingResult,
)
from .client import (
    AgentClient,
    BaseClient,
    OpenClawAPIError,
    SessionClient,
)
from .interaction import (
    MessageResponse,
    MessageType,
    Messenger,
)
from .skill import (
    SKILL_DEFINITION,
    SKILL_METADATA,
    get_skill_definition,
    get_skill_yaml,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "BaseClient",
    "AgentClient",
    "SessionClient",
    "OpenClawAPIError",
    # Agent
    "AgentManager",
    "AgentLifecycle",
    "AgentBinding",
    "BindingResult",
    # Interaction
    "Messenger",
    "MessageType",
    "MessageResponse",
    # Skill
    "SKILL_DEFINITION",
    "SKILL_METADATA",
    "get_skill_definition",
    "get_skill_yaml",
]
