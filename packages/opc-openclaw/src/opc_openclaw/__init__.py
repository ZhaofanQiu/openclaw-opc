"""
opc-openclaw: OpenClaw 功能封装模块

OpenClaw OPC v0.4.6 - OpenClaw 集成模块（CLI 版本）

提供 OpenClaw CLI 封装、Agent 生命周期管理和消息交互能力。

使用示例:
    from opc_openclaw import AgentManager, CLIMessenger, TaskCaller

    # Agent 管理
    manager = AgentManager()
    agents = await manager.list_agents()

    # 消息交互（使用 CLI）
    messenger = CLIMessenger()
    response = await messenger.send("opc_agent_1", "任务内容")

    # 任务分配
    task_caller = TaskCaller()
    result = await task_caller.assign_task(task_assignment)

作者: OpenClaw OPC Team
版本: 0.4.6
"""

__version__ = "0.4.6"

from .agent import (
    AgentBinding,
    AgentLifecycle,
    AgentManager,
    AgentState,
    BindingResult,
)
from .client import AgentClient, CLIAgentClient
from .config import AgentConfig, ConfigError, ConfigManager
from .interaction import (
    CLIMessenger,
    MessageResponse,
    MessageType,
    Messenger,  # 向后兼容
    ParsedReport,
    ResponseParser,
    TaskAssignment,
    TaskCaller,
    TaskResponse,
)
from .skill import (
    SKILL_DEFINITION,
    SKILL_METADATA,
    REPORT_START_MARKER,
    REPORT_END_MARKER,
    VALID_STATUSES,
    SkillInstaller,
    get_skill_definition,
    get_skill_yaml,
)

__all__ = [
    # Version
    "__version__",
    # Client
    "AgentClient",
    "CLIAgentClient",
    # Agent
    "AgentManager",
    "AgentLifecycle",
    "AgentBinding",
    "AgentState",
    "BindingResult",
    # Config
    "ConfigManager",
    "AgentConfig",
    "ConfigError",
    # Interaction
    "CLIMessenger",
    "Messenger",  # 向后兼容
    "MessageType",
    "MessageResponse",
    "TaskCaller",
    "TaskAssignment",
    "TaskResponse",
    # Skill
    "SkillInstaller",
    "SKILL_DEFINITION",
    "SKILL_METADATA",
    "ResponseParser",
    "ParsedReport",
    "REPORT_START_MARKER",
    "REPORT_END_MARKER",
    "VALID_STATUSES",
    "get_skill_definition",
    "get_skill_yaml",
]