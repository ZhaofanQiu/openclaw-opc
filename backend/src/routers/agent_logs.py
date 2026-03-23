"""
Agent Logs Router (v2.0)

Agent交互日志API - 记录所有与OpenClaw Agent的交互
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.agent_interaction_log_service_v2 import AgentInteractionLogService
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Agent Logs"])


# ============ 数据模型 ============

class ClearLogsRequest(BaseModel):
    agent_id: Optional[str] = None


class ClearLogsResponse(BaseModel):
    success: bool
    cleared_count: int
    message: str


# ============ API 端点 ============

@router.get("")
def get_agent_logs(
    agent_id: Optional[str] = Query(None, description="筛选特定Agent"),
    interaction_type: Optional[str] = Query(None, description="筛选交互类型 (message/cli/api/callback)"),
    direction: Optional[str] = Query(None, description="筛选方向 (outgoing/incoming)"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取Agent交互日志
    
    支持筛选和分页，返回所有与OpenClaw Agent的交互记录
    """
    result = AgentInteractionLogService.get_logs(
        agent_id=agent_id,
        interaction_type=interaction_type,
        direction=direction,
        limit=limit,
        offset=offset
    )
    
    return result


@router.get("/stats")
def get_agent_logs_stats():
    """
    获取日志统计信息
    
    返回总交互数、涉及的Agent列表、交互类型分布、成功率
    """
    return AgentInteractionLogService.get_stats()


@router.delete("", response_model=ClearLogsResponse)
def clear_agent_logs(
    agent_id: Optional[str] = Query(None, description="如果指定，只清空该Agent的日志")
):
    """
    清空交互日志
    
    如果不指定agent_id，则清空所有日志
    """
    cleared_count = AgentInteractionLogService.clear_logs(agent_id=agent_id)
    
    if agent_id:
        message = f"已清空 Agent {agent_id} 的 {cleared_count} 条日志"
    else:
        message = f"已清空所有 {cleared_count} 条日志"
    
    return ClearLogsResponse(
        success=True,
        cleared_count=cleared_count,
        message=message
    )


@router.get("/{log_id}")
def get_log_detail(log_id: str):
    """
    获取单条日志详情
    """
    log = AgentInteractionLogService.get_log_by_id(log_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return log.to_dict()