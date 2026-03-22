"""
Skill API routes.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.skill_service import SkillService

router = APIRouter()


class SkillAssign(BaseModel):
    """Assign skill to agent request."""
    skill_id: str
    proficiency: float = Field(50.0, ge=0, le=100)


class TaskSkillRequirementCreate(BaseModel):
    """Create task skill requirement request."""
    skill_id: str
    required_proficiency: float = Field(50.0, ge=0, le=100)
    weight: int = Field(5, ge=1, le=10)


@router.get("")
async def list_skills(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all available skills."""
    service = SkillService(db)
    skills = service.list_skills(category=category)
    
    return {
        "count": len(skills),
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "icon": s.icon,
            }
            for s in skills
        ]
    }


@router.post("/init-defaults")
async def initialize_default_skills(
    db: Session = Depends(get_db),
):
    """Initialize system with default skills."""
    service = SkillService(db)
    skills = service.initialize_default_skills()
    
    return {
        "success": True,
        "message": f"Initialized {len(skills)} default skills",
        "skills": [{"id": s.id, "name": s.name} for s in skills]
    }


# Agent Skills

@router.get("/agents/{agent_id}")
async def get_agent_skills(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Get all skills for an agent."""
    service = SkillService(db)
    skills = service.get_agent_skills(agent_id)
    
    return {
        "agent_id": agent_id,
        "skill_count": len(skills),
        "skills": skills
    }


@router.post("/agents/{agent_id}/assign")
async def assign_skill_to_agent(
    agent_id: str,
    assign: SkillAssign,
    db: Session = Depends(get_db),
):
    """Assign a skill to an agent."""
    service = SkillService(db)
    success = service.assign_skill_to_agent(
        agent_id=agent_id,
        skill_id=assign.skill_id,
        proficiency=assign.proficiency
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent or skill not found")
    
    return {
        "success": True,
        "message": f"Skill {assign.skill_id} assigned to agent {agent_id}",
        "proficiency": assign.proficiency
    }


# Task Skill Requirements

@router.get("/tasks/{task_id}/requirements")
async def get_task_skill_requirements(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get skill requirements for a task."""
    service = SkillService(db)
    requirements = service.get_task_skill_requirements(task_id)
    
    return {
        "task_id": task_id,
        "requirement_count": len(requirements),
        "requirements": requirements
    }


@router.post("/tasks/{task_id}/requirements")
async def set_task_skill_requirement(
    task_id: str,
    req: TaskSkillRequirementCreate,
    db: Session = Depends(get_db),
):
    """Set a skill requirement for a task."""
    service = SkillService(db)
    
    try:
        requirement = service.set_task_skill_requirement(
            task_id=task_id,
            skill_id=req.skill_id,
            required_proficiency=req.required_proficiency,
            weight=req.weight
        )
        
        return {
            "success": True,
            "requirement": {
                "task_id": requirement.task_id,
                "skill_id": requirement.skill_id,
                "required_proficiency": requirement.required_proficiency,
                "weight": requirement.weight,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Skill Matching

@router.get("/match/{task_id}/{agent_id}")
async def calculate_match_score(
    task_id: str,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Calculate skill match score between agent and task."""
    service = SkillService(db)
    result = service.calculate_agent_task_match_score(agent_id, task_id)
    
    return {
        "task_id": task_id,
        "agent_id": agent_id,
        **result
    }


@router.get("/match/{task_id}/best")
async def find_best_agent(
    task_id: str,
    available_only: bool = True,
    db: Session = Depends(get_db),
):
    """Find the best agent for a task based on skill match."""
    service = SkillService(db)
    result = service.find_best_agent_for_task(task_id, available_only=available_only)
    
    if not result:
        return {
            "success": False,
            "message": "No suitable agent found for this task"
        }
    
    return {
        "success": True,
        "best_match": result
    }