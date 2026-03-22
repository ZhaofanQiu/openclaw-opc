"""
Workflow Extensions Router v0.5.3

扩展功能API：
- 可视化：进度、时间线、瓶颈分析
- 推荐：员工推荐、预算分配建议
- 成就：徽章系统、排行榜
- 分析：团队统计、步骤统计
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.workflow_extensions import (
    WorkflowVisualizationService,
    WorkflowRecommendationService,
    WorkflowAchievementService,
    WorkflowAnalyticsService,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["workflow-extensions"])


# ============== 可视化API ==============

@router.get("/{workflow_id}/visualization/progress")
async def get_workflow_progress(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流进度可视化"""
    service = WorkflowVisualizationService(db)
    try:
        return service.get_workflow_progress(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{workflow_id}/visualization/timeline")
async def get_workflow_timeline(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取工作流时间线"""
    service = WorkflowVisualizationService(db)
    try:
        return service.get_workflow_timeline(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{workflow_id}/visualization/bottlenecks")
async def get_bottleneck_analysis(
    workflow_id: str,
    db: Session = Depends(get_db),
):
    """获取瓶颈分析"""
    service = WorkflowVisualizationService(db)
    try:
        return service.get_bottleneck_analysis(workflow_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============== 推荐API ==============

class AgentRecommendRequest(BaseModel):
    step_type: str = Field(..., description="步骤类型")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    exclude_agents: List[str] = Field(default=[], description="排除的员工ID")
    top_k: int = Field(default=3, ge=1, le=10)


@router.post("/recommend/agents")
async def recommend_agents(
    data: AgentRecommendRequest,
    db: Session = Depends(get_db),
):
    """
    智能推荐员工
    
    基于历史表现、技能匹配、当前负载推荐
    """
    service = WorkflowRecommendationService(db)
    return service.recommend_agents_for_step(
        step_type=data.step_type,
        workflow_title=data.title,
        workflow_description=data.description,
        exclude_agents=data.exclude_agents,
        top_k=data.top_k,
    )


class BudgetRecommendRequest(BaseModel):
    total_budget: float = Field(..., gt=0)
    steps_config: List[dict] = Field(..., description="步骤配置列表")


@router.post("/recommend/budget")
async def recommend_budget_allocation(
    data: BudgetRecommendRequest,
    db: Session = Depends(get_db),
):
    """智能推荐预算分配"""
    service = WorkflowRecommendationService(db)
    allocations = service.recommend_budget_allocation(
        total_budget=data.total_budget,
        steps_config=data.steps_config,
    )
    return {
        "total_budget": data.total_budget,
        "allocations": allocations,
        "steps": [s["name"] for s in data.steps_config],
    }


# ============== 成就API ==============

@router.get("/achievements/list")
async def list_achievements():
    """列出所有成就徽章"""
    service = WorkflowAchievementService(None)
    return {
        "achievements": list(service.ACHIEVEMENTS.values()),
        "count": len(service.ACHIEVEMENTS),
    }


@router.get("/achievements/agent/{agent_id}")
async def get_agent_achievements(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """获取员工获得的成就"""
    service = WorkflowAchievementService(db)
    achievements = service.check_achievements(agent_id)
    return {
        "agent_id": agent_id,
        "achievement_count": len(achievements),
        "achievements": achievements,
        "rarity_score": service._calculate_rarity_score(achievements),
    }


@router.get("/achievements/leaderboard")
async def get_achievement_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取成就排行榜"""
    service = WorkflowAchievementService(db)
    return {
        "leaderboard": service.get_leaderboard(limit=limit),
    }


# ============== 分析API ==============

@router.get("/analytics/team")
async def get_team_statistics(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """
    获取团队统计数据
    
    - 任务完成率
    - 预算使用情况
    - 返工统计
    """
    service = WorkflowAnalyticsService(db)
    return service.get_team_statistics(days=days)


@router.get("/analytics/step-types")
async def get_step_type_statistics(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """获取各步骤类型统计"""
    service = WorkflowAnalyticsService(db)
    return {
        "statistics": service.get_step_type_statistics(days=days),
    }


# ============== Dashboard API ==============

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
):
    """获取仪表盘汇总数据"""
    from src.models import WorkflowInstance
    
    # 活跃工作流
    active = db.query(WorkflowInstance).filter(
        WorkflowInstance.status.in_(["in_progress", "rework", "budget_fused", "rework_fused"])
    ).count()
    
    # 今日完成
    from datetime import datetime, timedelta
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = db.query(WorkflowInstance).filter(
        WorkflowInstance.status == "completed",
        WorkflowInstance.completed_at >= today
    ).count()
    
    # 待处理熔断
    fused = db.query(WorkflowInstance).filter(
        WorkflowInstance.status.in_(["budget_fused", "rework_fused"])
    ).count()
    
    # 本月统计
    month_start = today.replace(day=1)
    month_workflows = db.query(WorkflowInstance).filter(
        WorkflowInstance.created_at >= month_start
    ).all()
    
    return {
        "active_workflows": active,
        "completed_today": completed_today,
        "pending_fuse": fused,
        "month_summary": {
            "total_created": len(month_workflows),
            "total_completed": sum(1 for w in month_workflows if w.status == "completed"),
            "total_budget": sum(w.total_budget for w in month_workflows),
        },
    }
