"""
opc-core: 工作流统计 API (v0.4.2-P2)

工作流统计和分析 REST API 路由

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from opc_database import get_session
from opc_database.repositories import EmployeeRepository, TaskRepository

from ..services import WorkflowAnalyticsService, WorkflowTimelineService

router = APIRouter(tags=["workflow-analytics"])


# ========================================
# Pydantic 模型
# ========================================

class DateRangeParams(BaseModel):
    """日期范围参数"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ========================================
# 依赖注入
# ========================================

async def get_analytics_service():
    """获取统计服务"""
    async with get_session() as session:
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        yield WorkflowAnalyticsService(task_repo, emp_repo)


async def get_timeline_service():
    """获取时间线服务"""
    async with get_session() as session:
        task_repo = TaskRepository(session)
        yield WorkflowTimelineService(task_repo)


# ========================================
# 整体统计
# ========================================

@router.get("/analytics/workflows", response_model=dict)
async def get_workflow_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: Optional[int] = Query(None, description="最近N天的统计"),
    service: WorkflowAnalyticsService = Depends(get_analytics_service),
):
    """获取工作流整体统计"""
    # 如果指定了days，计算日期范围
    if days and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
    
    stats = await service.get_workflow_stats(start_date, end_date)
    return {"success": True, "data": service.format_stats_for_api(stats)}


@router.get("/analytics/workflows/step-analysis", response_model=dict)
async def get_step_analysis(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: Optional[int] = Query(None),
    service: WorkflowAnalyticsService = Depends(get_analytics_service),
):
    """获取步骤耗时分析"""
    if days and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
    
    stats = await service.get_step_analysis(start_date, end_date)
    return {"success": True, "data": service.format_step_stats_for_api(stats)}


@router.get("/analytics/workflows/daily-trend", response_model=dict)
async def get_daily_trend(
    days: int = Query(30, ge=1, le=90),
    service: WorkflowAnalyticsService = Depends(get_analytics_service),
):
    """获取每日趋势"""
    stats = await service.get_daily_trend(days)
    return {"success": True, "data": service.format_daily_stats_for_api(stats)}


# ========================================
# 员工排名
# ========================================

@router.get("/analytics/workflows/employee-ranking", response_model=dict)
async def get_employee_rankings(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    service: WorkflowAnalyticsService = Depends(get_analytics_service),
):
    """获取员工效率排名"""
    if days and not end_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
    
    rankings = await service.get_employee_rankings(start_date, end_date, limit)
    return {"success": True, "data": service.format_employee_stats_for_api(rankings)}


# ========================================
# 单工作流统计
# ========================================

@router.get("/workflows/{workflow_id}/stats", response_model=dict)
async def get_single_workflow_stats(
    workflow_id: str,
    service: WorkflowAnalyticsService = Depends(get_analytics_service),
):
    """获取单个工作流统计"""
    stats = await service.get_single_workflow_stats(workflow_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "data": stats}


# ========================================
# 时间线
# ========================================

@router.get("/workflows/{workflow_id}/timeline", response_model=dict)
async def get_workflow_timeline(
    workflow_id: str,
    service: WorkflowTimelineService = Depends(get_timeline_service),
):
    """获取工作流执行时间线"""
    events = await service.build_timeline(workflow_id)
    if not events:
        raise HTTPException(status_code=404, detail="Workflow not found or no events")
    return {"success": True, "data": service.format_timeline_for_api(events)}


@router.get("/workflows/{workflow_id}/timeline/summary", response_model=dict)
async def get_workflow_timeline_summary(
    workflow_id: str,
    service: WorkflowTimelineService = Depends(get_timeline_service),
):
    """获取工作流时间线摘要"""
    summary = await service.get_timeline_summary(workflow_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "data": service.format_summary_for_api(summary)}
