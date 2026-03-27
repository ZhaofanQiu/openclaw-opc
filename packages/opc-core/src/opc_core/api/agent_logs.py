"""
opc-core: Agent 日志 API 路由

提供 Agent 交互日志的查询和管理接口

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.5
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ..services.agent_log_service import AgentLogService

router = APIRouter(prefix="/agent-logs", tags=["Agent Logs"])


# ============ 响应模型 ============

class LogEntry(BaseModel):
    """日志条目"""
    id: str
    agent_id: str
    agent_name: Optional[str]
    interaction_type: str
    direction: str
    content: str
    response: Optional[str]
    task_id: Optional[str]
    metadata: dict
    created_at: str


class LogsResponse(BaseModel):
    """日志列表响应"""
    logs: list[LogEntry]
    total: int
    limit: int
    offset: int


class LogStats(BaseModel):
    """日志统计"""
    total_logs: int
    success_count: int
    success_rate: float
    agents: list[dict]
    types: dict
    hours: int


class ClearLogsResponse(BaseModel):
    """清空日志响应"""
    success: bool
    cleared_count: int
    message: str


# ============ API 端点 ============

@router.get("", response_model=LogsResponse)
async def get_agent_logs(
    agent_id: Optional[str] = Query(None, description="按 Agent ID 筛选"),
    interaction_type: Optional[str] = Query(None, description="按交互类型筛选 (partner_chat/task_assignment/assist_employee/assist_task/assist_workflow/assist_manual)"),
    direction: Optional[str] = Query(None, description="按方向筛选 (outgoing/incoming)"),
    task_id: Optional[str] = Query(None, description="按任务ID筛选"),
    hours: Optional[int] = Query(None, description="最近多少小时内的日志"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取 Agent 交互日志列表
    
    支持按 Agent、交互类型、方向、任务ID筛选，支持分页
    """
    # 计算时间范围
    start_time = None
    end_time = None
    if hours:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        end_time = datetime.utcnow()
    
    result = await AgentLogService.get_logs(
        agent_id=agent_id,
        interaction_type=interaction_type,
        direction=direction,
        task_id=task_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    
    return LogsResponse(**result)


@router.get("/stats", response_model=LogStats)
async def get_agent_logs_stats(
    agent_id: Optional[str] = Query(None, description="按 Agent ID 筛选"),
    hours: int = Query(24, ge=1, le=168, description="统计最近多少小时")
):
    """
    获取 Agent 交互日志统计
    
    返回总交互数、成功率、涉及的Agent列表、交互类型分布
    """
    stats = await AgentLogService.get_stats(
        agent_id=agent_id,
        hours=hours
    )
    
    return LogStats(**stats)


@router.get("/{log_id}")
async def get_log_detail(log_id: str):
    """
    获取单条日志详情
    
    返回完整的 content 和 response 内容
    """
    log = await AgentLogService.get_log_by_id(log_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return log


@router.delete("", response_model=ClearLogsResponse)
async def clear_agent_logs(
    agent_id: Optional[str] = Query(None, description="如果指定，只清空该Agent的日志")
):
    """
    清空交互日志
    
    如果不指定 agent_id，则清空所有日志。此操作不可恢复！
    """
    cleared_count = await AgentLogService.clear_logs(agent_id=agent_id)
    
    if agent_id:
        message = f"已清空 Agent {agent_id} 的 {cleared_count} 条日志"
    else:
        message = f"已清空所有 {cleared_count} 条日志"
    
    return ClearLogsResponse(
        success=True,
        cleared_count=cleared_count,
        message=message
    )
