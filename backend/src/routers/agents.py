"""
Agent API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from typing import List

from src.database import get_db
from src.models import Agent, AgentStatus, PositionLevel
from src.services.agent_service import AgentService
from src.utils.openclaw_config import read_openclaw_agents, get_agent_details
from src.services.partner_service import PartnerService
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter()


class AgentCreate(BaseModel):
    """Create agent request."""
    name: str = Field(..., min_length=1, max_length=50)
    agent_id: str = Field(..., description="OpenClaw agent ID")
    emoji: str = "🧑‍💻"
    monthly_budget: float = 2000.0


class PartnerSetup(BaseModel):
    """Setup partner from existing OpenClaw agent."""
    openclaw_agent_id: str = Field(..., description="Existing OpenClaw agent ID")
    monthly_budget: float = 10000.0


class CompanyInit(BaseModel):
    """Initialize company with partner and first employee."""
    partner_agent_id: str
    company_name: str = "My OPC"


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
    total_budget: float
    remaining_budget: float
    
    class Config:
        from_attributes = True


@router.get("/openclaw/agents")
@limiter.limit(RATE_LIMITS["default"])
async def list_openclaw_agents(request: Request):
    """
    List existing agents from OpenClaw configuration.
    User selects one of these to be the Partner.
    """
    agents = read_openclaw_agents()
    return {
        "agents": agents,
        "count": len(agents),
        "message": "Select one agent as your Partner" if agents else "No OpenClaw agents found"
    }


@router.post("/partner/setup")
@limiter.limit(RATE_LIMITS["create"])
async def setup_partner(
    request: Request,
    setup: PartnerSetup,
    db: Session = Depends(get_db),
):
    """
    Setup Partner from existing OpenClaw agent.
    This is the first step in company initialization.
    """
    # Verify the OpenClaw agent exists
    oc_agent = get_agent_details(setup.openclaw_agent_id)
    if not oc_agent:
        raise HTTPException(
            status_code=404,
            detail=f"OpenClaw agent '{setup.openclaw_agent_id}' not found"
        )
    
    service = AgentService(db)
    
    # Check if partner already exists
    existing = service.get_agent(setup.openclaw_agent_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{setup.openclaw_agent_id}' is already registered"
        )
    
    # Create Partner agent
    partner = service.create_agent(
        name=f"{oc_agent['name']} (Partner)",
        agent_id=setup.openclaw_agent_id,
        emoji="👑",
        monthly_budget=setup.monthly_budget,
    )
    
    # Update to Partner level
    partner.position_level = PositionLevel.PARTNER.value
    partner.position_title = "合伙人"
    db.commit()
    db.refresh(partner)
    
    return {
        "success": True,
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "agent_id": partner.agent_id,
            "position": "合伙人",
            "monthly_budget": partner.monthly_budget,
        },
        "message": f"Partner '{partner.name}' is ready to help you build your company!"
    }


@router.post("/company/init")
async def initialize_company(
    init: CompanyInit,
    db: Session = Depends(get_db),
):
    """
    Initialize company with Partner.
    Partner will assist in creating the first employee.
    """
    service = AgentService(db)
    
    # Verify partner exists
    partner = service.get_agent(init.partner_agent_id)
    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Partner not found. Please setup partner first."
        )
    
    return {
        "success": True,
        "company_name": init.company_name,
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "agent_id": partner.agent_id,
        },
        "next_steps": [
            "1. Partner will help you hire your first employee",
            "2. Define employee role and budget",
            "3. Create first project",
            "4. Start collaborating!"
        ],
        "message": f"Welcome to {init.company_name}! Your Partner '{partner.name}' is ready to assist you."
    }


@router.post("/partner/hire")
@limiter.limit(RATE_LIMITS["create"])
async def partner_hire_employee(
    request: Request,
    employee: AgentCreate,
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Partner assists in hiring a new employee.
    Validates partner permissions and creates employee.
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can hire employees")
    
    # Create employee
    try:
        new_employee = service.create_agent(
            name=employee.name,
            agent_id=employee.agent_id,
            emoji=employee.emoji,
            monthly_budget=employee.monthly_budget,
        )
        
        return {
            "success": True,
            "employee": {
                "id": new_employee.id,
                "name": new_employee.name,
                "agent_id": new_employee.agent_id,
                "position": new_employee.position_title,
                "monthly_budget": new_employee.monthly_budget,
            },
            "hired_by": partner.name,
            "message": f"{partner.name} successfully hired {new_employee.name} as {new_employee.position_title}!"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report")
@limiter.limit(RATE_LIMITS["create"])
async def report_task_completion(
    request: Request,
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
    available_only: bool = False,
    db: Session = Depends(get_db),
):
    """
    List all agents.
    
    Args:
        available_only: If true, only return agents that are IDLE (available for assignment)
    """
    service = AgentService(db)
    agents = service.list_agents()
    
    if available_only:
        # Filter for agents that are idle
        agents = [a for a in agents if a.status == AgentStatus.IDLE.value]
    
    return agents


@router.post("/partner/heartbeat")
async def partner_heartbeat(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Partner Agent heartbeat - reports that it's still alive.
    Should be called every 30 seconds by Partner Agent.
    """
    from datetime import datetime
    
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can send heartbeat")
    
    # Update heartbeat
    partner.last_heartbeat = datetime.utcnow()
    partner.is_online = "online"
    db.commit()
    
    return {
        "success": True,
        "message": "Heartbeat received",
        "timestamp": partner.last_heartbeat.isoformat()
    }


@router.get("/partner/health")
async def partner_health_status(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Check Partner Agent health status.
    Returns online/offline status based on last heartbeat.
    """
    from datetime import datetime, timedelta
    
    service = AgentService(db)
    
    partner = service.get_agent(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Check if heartbeat is recent (within 60 seconds)
    is_online = False
    seconds_since_heartbeat = None
    
    if partner.last_heartbeat:
        delta = datetime.utcnow() - partner.last_heartbeat
        seconds_since_heartbeat = delta.total_seconds()
        is_online = seconds_since_heartbeat < 60
    
    # Update is_online status
    partner.is_online = "online" if is_online else "offline"
    db.commit()
    
    return {
        "partner_id": partner_id,
        "name": partner.name,
        "is_online": is_online,
        "status": "online" if is_online else "offline",
        "last_heartbeat": partner.last_heartbeat.isoformat() if partner.last_heartbeat else None,
        "seconds_since_heartbeat": seconds_since_heartbeat,
        "warning": not is_online and partner.last_heartbeat is not None
    }


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


# Partner auto-assignment endpoints

@router.get("/partner/status")
async def partner_company_status(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Get company status for Partner.
    Shows pending tasks, agent availability, budget status.
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can view company status")
    
    partner_service = PartnerService(db)
    status = partner_service.get_company_status()
    
    return {
        "success": True,
        "partner": partner.name,
        "company_status": status
    }


@router.post("/partner/assign/{task_id}")
async def partner_auto_assign(
    task_id: str,
    partner_id: str,
    strategy: str = "budget",
    db: Session = Depends(get_db),
):
    """
    Partner auto-assigns a task to the best available agent.
    
    Strategies:
    - budget: Prioritize agents with highest remaining budget ratio
    - workload: Prioritize agents with lowest workload
    - combined: Weighted combination (70% budget + 30% workload)
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can assign tasks")
    
    partner_service = PartnerService(db)
    result = partner_service.auto_assign(task_id, strategy)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/partner/assign-all")
async def partner_assign_all_pending(
    partner_id: str,
    strategy: str = "budget",
    db: Session = Depends(get_db),
):
    """
    Partner assigns all pending tasks to best available agents.
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can assign tasks")
    
    partner_service = PartnerService(db)
    results = partner_service.assign_all_pending(strategy)
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    return {
        "success": True,
        "summary": {
            "total": len(results),
            "successful": successful,
            "failed": failed
        },
        "assignments": results
    }
