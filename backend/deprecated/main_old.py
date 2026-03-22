"""
OpenClaw OPC Core Service
FastAPI application for managing AI employees and tasks.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from pydantic import ValidationError

from src.database import init_db, check_database_connection, get_database_info
from src.routers import agents, agent_interaction_logs, approvals, avatars, budget, communication, config, monitor, notifications, reports, shared_memory, skills, skill_growth, tasks, workflows, workflow_extensions, workflow_templates, agent_skill_paths, workflow_details, websocket, api_keys, share, fuse, async_messages, sub_tasks, task_dependencies, workflows_optimized, task_assignment, task_steps, manuals
from src.utils.logging_config import configure_logging, get_logger
from src.utils.rate_limit import limiter, RATE_LIMITS
from src.utils.api_auth import require_read_permission

# Get project root (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if API key auth is enabled
API_KEY_AUTH_ENABLED = os.getenv("API_KEY_AUTH_ENABLED", "true").lower() == "true"

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
json_format = os.getenv("LOG_FORMAT", "text").lower() == "json"
configure_logging(log_level, json_format)
logger = get_logger(__name__)


# OpenAPI documentation metadata
OPENAPI_TAGS = [
    {
        "name": "agents",
        "description": "员工(Agent)管理 - 创建、查询、绑定OpenClaw Agent",
    },
    {
        "name": "agent-logs",
        "description": "Agent交互日志 - 调试和监控所有OpenClaw交互",
    },
    {
        "name": "tasks",
        "description": "任务管理 - 分配、执行、报告",
    },
    {
        "name": "workflows",
        "description": "工作流引擎 - 多步骤协作流程管理",
    },
    {
        "name": "workflows-optimized",
        "description": "工作流查询优化版 - 支持分页和性能优化",
    },
    {
        "name": "budget",
        "description": "预算管理 - OC币分配和统计",
    },
    {
        "name": "skills",
        "description": "技能管理 - 员工技能库",
    },
    {
        "name": "communication",
        "description": "员工间通信 - 消息传递",
    },
    {
        "name": "async-messages",
        "description": "异步消息系统 - 非阻塞通信",
    },
    {
        "name": "notifications",
        "description": "通知系统 - WebSocket实时推送",
    },
    {
        "name": "reports",
        "description": "报告和分析 - 数据统计",
    },
    {
        "name": "avatars",
        "description": "头像管理 - 像素头像上传和生成",
    },
    {
        "name": "config",
        "description": "系统配置 - OpenClaw集成配置",
    },
    {
        "name": "monitor",
        "description": "系统监控 - 健康检查和状态",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Application starting", api_key_auth=API_KEY_AUTH_ENABLED)
    
    # Check database connection
    db_info = get_database_info()
    logger.info("Database configuration", **db_info)
    
    if not db_info["connected"]:
        logger.error("Failed to connect to database", url=db_info["url"])
        raise RuntimeError(f"Database connection failed: {db_info['url']}")
    
    init_db()
    logger.info("Application ready", database_type=db_info["type"])
    yield
    # Shutdown
    logger.info("Application stopping")


# Create FastAPI application with enhanced documentation
app = FastAPI(
    title="OpenClaw OPC API",
    description="""
    # OpenClaw OPC - One-Person Company
    
    将 OpenClaw Agent 作为员工管理的虚拟一人公司系统。
    
    ## 核心功能
    
    - **员工管理**: 雇佣、绑定、管理 AI Agent 员工
    - **任务系统**: 分配任务、追踪进度、自动结算预算
    - **工作流引擎**: 多步骤协作流程，支持返工和熔断机制
    - **预算控制**: OC币预算管理，防止超支
    - **技能成长**: 员工技能路径和成长追踪
    - **实时通知**: WebSocket 推送关键事件
    
    ## 认证
    
    默认启用 API Key 认证。在请求头中添加:
    ```
    X-API-Key: your-api-key
    ```
    
    ## 快速开始
    
    1. 创建 Partner: `POST /api/agents/partner/setup-auto`
    2. 雇佣员工: `POST /api/agents/partner/hire`
    3. 分配任务: `POST /api/tasks`
    4. 查看工作流: `GET /api/workflows`
    """,
    version="0.6.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    contact={
        "name": "OpenClaw OPC Team",
        "url": "https://github.com/ZhaofanQiu/openclaw-opc",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)
app.state.limiter = limiter
app.state.limiter = limiter

# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded."""
    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        method=request.method,
        client=get_remote_address(request),
    )
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )

# Validation error handler
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )

# Value error handler
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions."""
    logger.warning(
        "value_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Add rate limiting middleware
app.add_middleware(SlowAPIMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# User context middleware (adds current user to request context)
from src.middleware.context import UserContextMiddleware
app.add_middleware(UserContextMiddleware)

# Include routers with optional API key auth
def get_router_dependencies():
    """Get router dependencies based on auth config."""
    if API_KEY_AUTH_ENABLED:
        return [Depends(require_read_permission)]
    return []

# Include routers with optional auth
app.include_router(
    agents.router, 
    prefix="/api/agents", 
    tags=["agents"],
    dependencies=get_router_dependencies()
)
app.include_router(
    agent_interaction_logs.router,
    tags=["agent-logs"],
    dependencies=get_router_dependencies()
)
app.include_router(
    tasks.router, 
    prefix="/api/tasks", 
    tags=["tasks"],
    dependencies=get_router_dependencies()
)
app.include_router(
    budget.router, 
    prefix="/api/budget", 
    tags=["budget"],
    dependencies=get_router_dependencies()
)
app.include_router(
    config.router, 
    prefix="/api/config", 
    tags=["config"],
    dependencies=get_router_dependencies()
)
app.include_router(
    monitor.router, 
    prefix="/api/monitor", 
    tags=["monitor"],
    dependencies=get_router_dependencies()
)
app.include_router(
    notifications.router, 
    prefix="/api/notifications", 
    tags=["notifications"],
    dependencies=get_router_dependencies()
)
app.include_router(
    skills.router, 
    prefix="/api/skills", 
    tags=["skills"],
    dependencies=get_router_dependencies()
)
app.include_router(
    reports.router, 
    prefix="/api/reports", 
    tags=["reports"],
    dependencies=get_router_dependencies()
)
# API Keys router - requires admin for management but has its own auth endpoints
app.include_router(api_keys.router, tags=["API Keys"])
# Share links router
app.include_router(share.router, tags=["Share Links"])
# Fuse events router
app.include_router(fuse.router)
# Avatar router
app.include_router(avatars.router)
# Communication router
app.include_router(communication.router)
# Async Messages router
app.include_router(async_messages.router)
# Sub-tasks router (v0.4.0)
app.include_router(
    sub_tasks.router,
    dependencies=get_router_dependencies()
)
# Task dependencies router (v0.4.0)
app.include_router(
    task_dependencies.router,
    dependencies=get_router_dependencies()
)
# Approval workflow router (v0.4.0)
app.include_router(
    approvals.router,
    dependencies=get_router_dependencies()
)
# Skill growth router (v0.4.0)
app.include_router(
    skill_growth.router,
    dependencies=get_router_dependencies()
)
# Shared memory router (v0.4.0)
app.include_router(
    shared_memory.router,
    dependencies=get_router_dependencies()
)
# Workflow engine router (v0.5.0)
app.include_router(
    workflows.router,
    dependencies=get_router_dependencies()
)
# Workflow extensions router (v0.5.3)
app.include_router(
    workflow_extensions.router,
    dependencies=get_router_dependencies()
)
# Workflow templates router (v0.5.4)
app.include_router(
    workflow_templates.router,
    dependencies=get_router_dependencies()
)
# Agent skill paths router (v0.5.5)
app.include_router(
    agent_skill_paths.router,
    dependencies=get_router_dependencies()
)
# Workflow detail router (v0.5.8)
app.include_router(
    workflow_details.router,
    dependencies=get_router_dependencies()
)
# Optimized workflow router (v0.6.1)
app.include_router(
    workflows_optimized.router,
    dependencies=get_router_dependencies()
)
# Task assignment router (v0.6.2)
app.include_router(
    task_assignment.router,
    dependencies=get_router_dependencies()
)
# Task steps router (v0.6.3) - Chat-based collaboration
app.include_router(
    task_steps.router,
    dependencies=get_router_dependencies()
)
# Manuals router (v0.6.3) - Task manual system
app.include_router(
    manuals.router,
    dependencies=get_router_dependencies()
)
# WebSocket router (v0.5.6)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    logger.info("root_endpoint_called")
    return {
        "name": "OpenClaw OPC",
        "version": "0.2.0-alpha",
        "status": "running",
        "dashboard": "/dashboard",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    db_info = get_database_info()
    return {
        "status": "healthy",
        "database": {
            "type": db_info["type"],
            "connected": db_info["connected"],
        },
        "version": "0.2.0-alpha",
    }


# Mount static files (dashboard UI)
web_dir = os.path.join(PROJECT_ROOT, "web")
if os.path.exists(web_dir):
    # Explicit route for pixel-office (before mounting static files)
    from fastapi.responses import FileResponse
    
    @app.get("/dashboard/pixel-office", include_in_schema=False)
    async def pixel_office():
        """Serve pixel office HTML file."""
        return FileResponse(os.path.join(web_dir, "pixel-office.html"))
    
    app.mount("/dashboard", StaticFiles(directory=web_dir, html=True), name="dashboard")
    logger.info("dashboard_mounted", path="/dashboard")
    logger.info("pixel_office_mounted", path="/dashboard/pixel-office")

# Mount avatars directory - use web/avatars for direct access
avatars_dir = os.path.join(PROJECT_ROOT, "web", "avatars")
if not os.path.exists(avatars_dir):
    # Fallback to data/avatars if web/avatars doesn't exist
    avatars_dir = os.path.join(PROJECT_ROOT, "data", "avatars")
os.makedirs(avatars_dir, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=avatars_dir), name="avatars")
logger.info("avatars_mounted", path="/avatars", directory=avatars_dir)
