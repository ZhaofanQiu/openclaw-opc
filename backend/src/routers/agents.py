"""
Agent API routes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Agent, AgentStatus
from src.services.agent_service import AgentService

router = APIRouter()


class AgentCreate(BaseModel):
    """Create agent request."""
    name: str = Field(..., min_length=1, max_length=50)
    agent_id: str = Field(..., description="OpenClaw agent ID")
    emoji: str = "🧑‍💻"
    monthly_budget: float = 2000.0


class AgentReport(BaseModel):
    """Agent task completion report."""
    agent_id: str
    task_id: str
    token_used: int = Field(..., ge=0)
    result_summary: str = ""
    status: str = "completed"  # completed, failed


class AgentResponse(BaseModel):
    """Agent response model."""
    id: str
    name: str
    emoji: str
    position_title: str
    status: str
    mood_emoji: str
    remaining_budget: float
    
    class Config:
        from_attributes = True


@router.post("/report")
async def report_task_completion(
    report: AgentReport,
    db: Session = Depends(get_db),
):
    """
    Report task completion from Agent.
    Called by OPC Bridge Skill after task completion.
    """
    service = AgentService(db)
    try:
        result = service.report_task_completion(
            agent_id=report.agent_id,
            task_id=report.task_id,
            token_used=report.token_used,
            result_summary=report.result_summary,
            status=report.status,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/task")
async def get_agent_task(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    Get current task assigned to agent.
    Called by Partner Agent to check for new tasks.
    """
    service = AgentService(db)
    task = service.get_pending_task(agent_id)
    if task:
        return {
            "has_task": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "estimated_cost": task.estimated_cost,
            }
        }
    return {"has_task": False}


@router.post("")
async def create_agent(
    agent: AgentCreate,
    db: Session = Depends(get_db),
):
    """Create a new agent (employee)."""
    service = AgentService(db)
    try:
        new_agent = service.create_agent(
            name=agent.name,
            agent_id=agent.agent_id,
            emoji=agent.emoji,
            monthly_budget=agent.monthly_budget,
        )
        return new_agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    db: Session = Depends(get_db),
):
    """List all agents."""
    service = AgentService(db)
    return service.list_agents()


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Get agent details."""
    service = AgentService(db)
    agent = service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
