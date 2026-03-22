"""
Agent Skill Path Router v0.5.5

技能成长路径API
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.agent_skill_path import AgentSkillPathService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/agent-skill-paths", tags=["agent-skill-paths"])


class CompareRequest(BaseModel):
    agent_ids: List[str] = Field(..., min_items=2, max_items=10)


@router.get("/paths")
async def get_all_paths():
    """获取所有成长路径"""
    # 不需要db，直接返回定义
    from src.services.agent_skill_path import AgentSkillPathService
    service = AgentSkillPathService(None)
    return {"paths": service.get_all_paths()}


@router.get("/agent/{agent_id}")
async def get_agent_skill_path(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    获取员工技能成长路径
    
    包含：
    - 当前技能
    - 推荐路径
    - 路径可视化
    - 下一个里程碑
    - 成长建议
    """
    service = AgentSkillPathService(db)
    try:
        return service.get_agent_skill_path(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/compare")
async def compare_agents(
    data: CompareRequest,
    db: Session = Depends(get_db),
):
    """对比多个员工的成长路径"""
    service = AgentSkillPathService(db)
    return service.compare_agents(data.agent_ids)


@router.get("/agent/{agent_id}/dashboard")
async def get_agent_dashboard(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取员工成长仪表盘"""
    from src.models import Agent, WorkflowStep
    from sqlalchemy import func
    
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # 统计完成的任务
    completed_steps = db.query(WorkflowStep).filter(
        WorkflowStep.assignee_id == agent_id,
        WorkflowStep.status == "completed"
    ).count()
    
    # 统计各类型任务
    step_types = db.query(WorkflowStep.step_type, func.count()).filter(
        WorkflowStep.assignee_id == agent_id,
        WorkflowStep.status == "completed"
    ).group_by(WorkflowStep.step_type).all()
    
    # 返工统计
    rework_count = db.query(WorkflowStep).filter(
        WorkflowStep.assignee_id == agent_id,
        WorkflowStep.rework_count > 0
    ).count()
    
    rework_rate = (rework_count / completed_steps * 100) if completed_steps > 0 else 0
    
    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "level": agent.level,
            "skills": [s.id for s in agent.skills],
        },
        "statistics": {
            "completed_steps": completed_steps,
            "step_type_distribution": {t: c for t, c in step_types},
            "rework_count": rework_count,
            "rework_rate": round(rework_rate, 1),
        },
        "path_summary": await get_agent_skill_path(agent_id, db),
    }
