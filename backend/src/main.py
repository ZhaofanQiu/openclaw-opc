"""
OpenClaw OPC Core Service
FastAPI application for managing AI employees and tasks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import init_db
from src.routers import agents, budget, tasks


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
    version="0.1.0-alpha",
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "OpenClaw OPC",
        "version": "0.1.0-alpha",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
