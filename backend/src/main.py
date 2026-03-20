"""
OpenClaw OPC Core Service
FastAPI application for managing AI employees and tasks.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.database import init_db
from src.routers import agents, budget, config, monitor, notifications, reports, skills, tasks


# Get project root (parent of backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    print("✓ Database initialized")
    yield
    # Shutdown
    print("✓ Shutting down...")


app = FastAPI(
    title="OpenClaw OPC",
    description="One-Person Company management system for OpenClaw Agents",
    version="0.2.0-alpha",
    lifespan=lifespan,
)

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


@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    return {
        "name": "OpenClaw OPC",
        "version": "0.1.0-alpha",
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
    print(f"✓ Dashboard mounted at /dashboard")
    print(f"✓ Pixel Office at /dashboard/pixel-office")
