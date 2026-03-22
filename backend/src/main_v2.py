"""
OpenClaw OPC Core Service v2.0 (重构版)
简化架构，核心优先
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

from database import init_db, check_database_connection, get_database_info
from routers import agents, tasks, manuals, budget, approvals, reports, config, skill_api
from utils.logging_config import configure_logging, get_logger
from utils.rate_limit import limiter
from utils.api_auth import require_read_permission

# Get project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API key auth
API_KEY_AUTH_ENABLED = os.getenv("API_KEY_AUTH_ENABLED", "true").lower() == "true"

# Logging
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(log_level)
logger = get_logger(__name__)

OPENAPI_TAGS = [
    {"name": "Agents", "description": "员工管理 - 创建、查询、绑定 OpenClaw Agent"},
    {"name": "Tasks", "description": "任务管理 - 创建、分配、执行"},
    {"name": "Manuals", "description": "手册管理 - 任务/岗位/公司手册"},
    {"name": "Budget", "description": "预算管理 - OC币分配和统计"},
    {"name": "Skill API", "description": "Skill 接口 - opc-bridge skill 调用"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting OPC Core Service v2.0")
    
    # Check database
    db_info = get_database_info()
    if not db_info["connected"]:
        logger.error("Database connection failed")
        raise RuntimeError(f"Database connection failed: {db_info['url']}")
    
    init_db()
    logger.info(f"Database ready: {db_info['type']}")
    
    # Check skill installation
    try:
        from core.skill_installer import check_skill_installed
        if check_skill_installed():
            logger.info("✓ opc-bridge skill installed")
        else:
            logger.warning("✗ opc-bridge skill not installed")
            logger.info("  Run: python -m core.skill_installer")
    except Exception as e:
        logger.warning(f"Skill check failed: {e}")
    
    yield
    logger.info("Stopping OPC Core Service")


# Create FastAPI app
app = FastAPI(
    title="OpenClaw OPC API v2.0",
    description="""
    # OpenClaw OPC - One-Person Company (重构版)
    
    将 OpenClaw Agent 作为员工管理的虚拟一人公司系统。
    
    ## 核心功能 (v2.0)
    
    - **员工管理**: 雇佣、绑定、管理 AI Agent 员工
    - **任务系统**: 创建、分配、执行、完成
    - **手册系统**: 任务/岗位/公司手册指导 Agent
    - **预算控制**: OC币预算管理，防止超支
    - **Skill 集成**: 通过 opc-bridge skill 实现 Agent 交互
    
    ## 架构
    
    v2.0 采用 Skill 驱动架构：
    - OPC 通过 `sessions_send` 分配任务
    - Agent 通过 `opc-bridge` skill 获取信息、报告结果
    
    ## 快速开始
    
    1. 安装 opc-bridge skill
    2. 创建员工: `POST /api/agents`
    3. 创建任务: `POST /api/tasks`
    4. 分配任务: `POST /api/tasks/{id}/assign`
    """,
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)
app.state.limiter = limiter


# Exception handlers
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning("Rate limit exceeded", path=request.url.path)
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Middleware
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Router dependencies
def get_router_deps():
    if API_KEY_AUTH_ENABLED:
        return [Depends(require_read_permission)]
    return []


# Include routers (简化版 - 8个核心 router)
routers_config = [
    (agents, "/api/agents", "Agents"),
    (tasks, "/api/tasks", "Tasks"),
    (manuals, "/api/manuals", "Manuals"),
    (budget, "/api/budget", "Budget"),
    (approvals, "/api/approvals", "Approvals"),
    (reports, "/api/reports", "Reports"),
    (config, "/api/config", "Config"),
    (skill_api, "/api/skill", "Skill API"),
]

for router_module, prefix, tag in routers_config:
    try:
        app.include_router(
            router_module.router,
            prefix=prefix,
            tags=[tag],
            dependencies=get_router_deps()
        )
        logger.debug(f"✓ Router registered: {tag} at {prefix}")
    except Exception as e:
        logger.error(f"✗ Failed to register {tag}: {e}")


# Static files
static_dirs = [
    ("web", "/"),
    ("data/avatars", "/avatars"),
]

for dir_name, url_path in static_dirs:
    static_path = os.path.join(PROJECT_ROOT, dir_name)
    if os.path.exists(static_path):
        app.mount(url_path, StaticFiles(directory=static_path), name=dir_name)


# Health check
@app.get("/health")
def health_check():
    db_info = get_database_info()
    return {
        "status": "ok",
        "version": "2.0.0",
        "database": db_info["type"] if db_info["connected"] else "disconnected"
    }


# Root redirect
@app.get("/")
def root():
    return {"message": "OpenClaw OPC v2.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
