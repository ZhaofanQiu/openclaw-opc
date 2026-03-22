"""Models package - v2.0 Simplified"""

# v2.0 简化模型
from models.agent_v2 import Agent, AgentStatus, PositionLevel
from models.task_v2 import Task, TaskStatus, TaskPriority

__all__ = [
    "Agent",
    "AgentStatus",
    "PositionLevel",
    "Task",
    "TaskStatus",
    "TaskPriority",
]
