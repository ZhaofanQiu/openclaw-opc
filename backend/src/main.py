"""
OpenClaw OPC Core Service
FastAPI application for managing AI employees and tasks.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from pydantic import ValidationError

from src.database import init_db
from src.routers import agents, budget, config, monitor, notifications, reports, skills, tasks, api_keys
from src.utils.logging_config import configure_logging, get_logger
from src.utils.rate_limit import limiter, RATE_LIMITS

# Get project root (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
json_format = os.getenv("LOG_FORMAT", "text").lower() == "json"
configure_logging(log_level, json_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Application starting")
    init_db()
    logger.info("Application ready")
    yield
    # Shutdown
    logger.info("Application stopping")


app = FastAPI(
    title="OpenClaw OPC",
    description="One-Person Company management system for OpenClaw Agents",
    version="0.2.0-alpha",
    lifespan=lifespan,
)
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

# Include routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(budget.router, prefix="/api/budget", tags=["budget"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["monitor"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(api_keys.router, tags=["API Keys"])


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
    return {"status": "healthy"}


# Mount static files (dashboard UI)
web_dir = os.path.join(PROJECT_ROOT, "web")
if os.path.exists(web_dir):
    app.mount("/dashboard", StaticFiles(directory=web_dir, html=True), name="dashboard")
    logger.info("dashboard_mounted", path="/dashboard")
    logger.info("pixel_office_mounted", path="/dashboard/pixel-office")
