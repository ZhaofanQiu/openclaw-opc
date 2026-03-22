"""
Skill Growth Router for v0.4.0

API endpoints for skill growth management
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.skill_growth_service import SkillGrowthService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/skill-growth", tags=["skill-growth"])


# ============== Request/Response Models ==============

class ExperienceAdd(BaseModel):
    """Add experience request."""
    experience: int = Field(..., gt=0, description="经验值")
    reason: str = Field(default="", description="原因")


class SkillGrowthResponse(BaseModel):
    """Skill growth response."""
    skill_id: str
    skill_name: str
    skill_category: str
    skill_icon: str
    level: int
    experience: int
    experience_to_next: int
    progress_percentage: float
    total_tasks_completed: int
    total_experience_earned: int
    is_max_level: bool


class SkillGrowthDetailResponse(SkillGrowthResponse):
    """Detailed skill growth response."""
    skill_description: str
    first_acquired_at: Optional[str]
    last_improved_at: Optional[str]
    recent_history: List[dict]


class ExperienceResult(BaseModel):
    """Experience gain result."""
    agent_id: str
    skill_id: str
    experience_gained: int
    level_before: int
    level_after: int
    level_ups: int
    current_experience: int
    experience_to_next: int
    progress_percentage: float
    is_max_level: bool


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""
    rank: int
    agent_id: str
    agent_name: str
    agent_emoji: str
    level: int
    experience: int
    total_experience_earned: int
    total_tasks_completed: int


class OverallLeaderboardEntry(BaseModel):
    """Overall leaderboard entry."""
    rank: int
    agent_id: str
    agent_name: str
    agent_emoji: str
    total_level: int
    total_experience: int


class GrowthStatsResponse(BaseModel):
    """Growth statistics response."""
    total_skill_records: int
    average_level: float
    highest_level: int
    max_level_count: int
    total_experience_earned: int
    total_tasks_completed: int


# ============== API Endpoints ==============

@router.get("/agent/{agent_id}", response_model=List[SkillGrowthResponse])
async def get_agent_skills(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取员工的所有技能成长数据。"""
    service = SkillGrowthService(db)
    skills = service.get_agent_skills(agent_id)
    return skills


@router.get("/agent/{agent_id}/skill/{skill_id}", response_model=SkillGrowthDetailResponse)
async def get_skill_details(
    agent_id: str,
    skill_id: str,
    db: Session = Depends(get_db),
):
    """获取员工特定技能的详细成长数据。"""
    service = SkillGrowthService(db)
    details = service.get_skill_details(agent_id, skill_id)
    if not details:
        raise HTTPException(status_code=404, detail="Skill growth record not found")
    return details


@router.post("/agent/{agent_id}/skill/{skill_id}/add-exp", response_model=ExperienceResult)
async def add_experience(
    agent_id: str,
    skill_id: str,
    data: ExperienceAdd,
    db: Session = Depends(get_db),
):
    """为员工技能添加经验值。"""
    service = SkillGrowthService(db)
    try:
        result = service.add_experience(
            agent_id=agent_id,
            skill_id=skill_id,
            experience=data.experience,
            reason=data.reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/leaderboard", response_model=List[OverallLeaderboardEntry])
async def get_overall_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取综合技能排行榜。"""
    service = SkillGrowthService(db)
    leaderboard = service.get_skill_leaderboard(skill_id=None, limit=limit)
    return leaderboard


@router.get("/leaderboard/{skill_id}", response_model=List[LeaderboardEntry])
async def get_skill_leaderboard(
    skill_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取特定技能排行榜。"""
    service = SkillGrowthService(db)
    leaderboard = service.get_skill_leaderboard(skill_id=skill_id, limit=limit)
    return leaderboard


@router.get("/stats", response_model=GrowthStatsResponse)
async def get_growth_stats(
    db: Session = Depends(get_db),
):
    """获取整体技能成长统计。"""
    service = SkillGrowthService(db)
    stats = service.get_growth_stats()
    return stats


@router.get("/config")
async def get_growth_config():
    """获取技能成长配置。"""
    from src.models.skill_growth import SKILL_GROWTH_CONFIG
    return SKILL_GROWTH_CONFIG


# ============== Integration Endpoints ==============

@router.post("/award-task-completion/{agent_id}")
async def award_task_completion(
    agent_id: str,
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    为任务完成发放经验值。
    
    此端点通常由任务完成流程自动调用
    """
    from src.models import Task
    
    service = SkillGrowthService(db)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    results = service.award_task_completion_exp(agent_id, task)
    
    return {
        "success": True,
        "agent_id": agent_id,
        "task_id": task_id,
        "skills_awarded": len(results),
        "details": results,
    }
