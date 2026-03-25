"""
opc-core: API 路由聚合

所有 API 路由的聚合导出

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.2-P2
"""

from fastapi import APIRouter

from .budget import router as budget_router
from .employees import router as employees_router
from .manuals import router as manuals_router
from .reports import router as reports_router
from .skill_api import router as skill_router
from .tasks import router as tasks_router
from .workflow_analytics import router as workflow_analytics_router  # v0.4.2-P2
from .workflow_templates import router as workflow_templates_router  # v0.4.2-P2
from .workflows import router as workflows_router  # v0.4.2

# 创建主 API Router
api_router = APIRouter(prefix="/api/v1")

# 注册子路由
api_router.include_router(employees_router)
api_router.include_router(tasks_router)
api_router.include_router(budget_router)
api_router.include_router(manuals_router)
api_router.include_router(reports_router)
api_router.include_router(skill_router)
api_router.include_router(workflows_router)  # v0.4.2
api_router.include_router(workflow_templates_router)  # v0.4.2-P2
api_router.include_router(workflow_analytics_router)  # v0.4.2-P2

__all__ = ["api_router"]
