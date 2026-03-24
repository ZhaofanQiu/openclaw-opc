"""
opc-core: OpenClaw OPC 核心业务模块

FastAPI + Repository 模式实现的 OPC 业务逻辑

使用示例:
    from opc_core import create_app

    app = create_app()
    # uvicorn.run(app, host="0.0.0.0", port=8000)

作者: OpenClaw OPC Team
版本: 0.4.0
"""

__version__ = "0.4.0"

from .app import create_app
from .api.dependencies import (
    get_db_session,
    get_employee_repo,
    get_task_repo,
    verify_api_key,
)
from .services import EmployeeService, TaskService

__all__ = [
    # Version
    "__version__",
    # App
    "create_app",
    # Dependencies
    "get_db_session",
    "get_employee_repo",
    "get_task_repo",
    "verify_api_key",
    # Services
    "EmployeeService",
    "TaskService",
]
