"""
opc-database: 仓库包

所有数据仓库定义

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.4
"""

from .base import BaseRepository
from .employee_repo import EmployeeRepository
from .partner_message_repo import PartnerMessageRepository
from .task_repo import TaskMessageRepository, TaskRepository
from .workflow_template_repo import (
    WorkflowTemplateRatingRepository,
    WorkflowTemplateRepository,
)

__all__ = [
    "BaseRepository",
    "EmployeeRepository",
    "PartnerMessageRepository",  # v0.4.4
    "TaskRepository",
    "TaskMessageRepository",
    # Workflow Template (v0.4.2-P2)
    "WorkflowTemplateRepository",
    "WorkflowTemplateRatingRepository",
]
