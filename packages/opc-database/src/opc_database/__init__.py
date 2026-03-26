"""
opc-database: 数据库管理模块

OpenClaw OPC v0.4.3 - 数据库管理模块

提供异步数据库连接、ORM模型和Repository数据访问层。

使用示例:
    from opc_database import get_session
    from opc_database.repositories import EmployeeRepository

    async with get_session() as session:
        repo = EmployeeRepository(session)
        employee = await repo.get_by_id("emp_xxx")

作者: OpenClaw OPC Team
版本: 0.4.3
"""

__version__ = "0.4.3"

from .connection import (
    check_connection,
    close_db,
    get_database_url,
    get_session,
    init_db,
)
from .models import (
    AgentStatus,
    Base,
    CompanyBudget,
    CompanyConfig,
    Employee,
    EmployeeSkill,
    PositionLevel,
    Task,
    TaskMessage,
    TaskPriority,
    TaskStatus,
    WorkflowTemplate,
    WorkflowTemplateRating,
)
from .repositories import (
    BaseRepository,
    EmployeeRepository,
    TaskMessageRepository,
    TaskRepository,
    WorkflowTemplateRatingRepository,
    WorkflowTemplateRepository,
)

__all__ = [
    # Version
    "__version__",
    # Connection
    "get_session",
    "init_db",
    "close_db",
    "check_connection",
    "get_database_url",
    # Models
    "Base",
    "Employee",
    "EmployeeSkill",
    "Task",
    "TaskMessage",
    "CompanyBudget",
    "CompanyConfig",
    # Enums
    "AgentStatus",
    "PositionLevel",
    "TaskStatus",
    "TaskPriority",
    # Workflow Template (v0.4.2-P2)
    "WorkflowTemplate",
    "WorkflowTemplateRating",
    # Repositories
    "BaseRepository",
    "EmployeeRepository",
    "TaskRepository",
    "TaskMessageRepository",
    "WorkflowTemplateRepository",
    "WorkflowTemplateRatingRepository",
]
