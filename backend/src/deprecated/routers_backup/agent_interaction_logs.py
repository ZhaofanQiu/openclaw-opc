"""
Agent Interaction Log Router
Agent交互日志路由
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.agent_interaction_log_service import AgentInteractionLogService
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/agent-logs", tags=["agent-logs"])


class LogResponse(BaseModel):
    """日志响应"""
    id: str
    agent_id: str
    agent_name: str
    interaction_type: str
    direction: str
    content: str
    response: Optional[str] = None
    metadata: Optional[dict] = None
    timestamp: str
    duration_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None


class LogsListResponse(BaseModel):
    """日志列表响应"""
    logs: list[LogResponse]
    total: int
    limit: int
    offset: int


class ClearLogsRequest(BaseModel):
    """清空日志请求"""
    agent_id: Optional[str] = Field(None, description="如果指定，只清空该Agent的日志")


class ClearLogsResponse(BaseModel):
    """清空日志响应"""
    success: bool
    cleared_count: int
    message: str


class LogStatsResponse(BaseModel):
    """日志统计响应"""
    total_logs: int
    agents: list[dict]
    types: dict
    success_rate: float


@router.get(
    "",
    response_model=LogsListResponse,
    summary="获取Agent交互日志",
    description="获取与OpenClaw Agent的所有交互日志，支持筛选和分页"
)
async def get_agent_logs(
    agent_id: Optional[str] = Query(None, description="筛选特定Agent"),
    interaction_type: Optional[str] = Query(None, description="筛选交互类型 (message/cli/api/session_send)"),
    direction: Optional[str] = Query(None, description="筛选方向 (outgoing/incoming)"),
    limit: int = Query(100, ge=1, le=500, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """获取Agent交互日志"""
    service = AgentInteractionLogService(db)
    
    result = service.get_logs(
        agent_id=agent_id,
        interaction_type=interaction_type,
        direction=direction,
        limit=limit,
        offset=offset
    )
    
    return result


@router.delete(
    "",
    response_model=ClearLogsResponse,
    summary="清空日志",
    description="清空交互日志。如果不指定agent_id，则清空所有日志"
)
async def clear_agent_logs(
    agent_id: Optional[str] = Query(None, description="如果指定，只清空该Agent的日志"),
    db: Session = Depends(get_db)
):
    """清空Agent交互日志"""
    service = AgentInteractionLogService(db)
    
    cleared_count = service.clear_logs(agent_id=agent_id)
    
    message = f"已清空 {cleared_count} 条日志"
    if agent_id:
        message = f"已清空 Agent {agent_id} 的 {cleared_count} 条日志"
    
    return {
        "success": True,
        "cleared_count": cleared_count,
        "message": message
    }


@router.get(
    "/stats",
    response_model=LogStatsResponse,
    summary="获取日志统计",
    description="获取交互日志的统计信息，包括各Agent的日志数量、成功率等"
)
async def get_agent_logs_stats(
    db: Session = Depends(get_db)
):
    """获取Agent交互日志统计"""
    service = AgentInteractionLogService(db)
    
    stats = service.get_stats()
    return stats


@router.get(
    "/export",
    summary="导出日志",
    description="导出所有日志为JSON或TXT格式"
)
async def export_agent_logs(
    format: str = Query("json", description="导出格式 (json/txt)"),
    db: Session = Depends(get_db)
):
    """导出Agent交互日志"""
    service = AgentInteractionLogService(db)
    
    try:
        content = service.export_logs(format=format)
        
        from fastapi.responses import PlainTextResponse, JSONResponse
        
        if format == "txt":
            return PlainTextResponse(
                content=content,
                headers={
                    "Content-Disposition": "attachment; filename=agent_logs.txt"
                }
            )
        else:
            return JSONResponse(
                content=json.loads(content),
                headers={
                    "Content-Disposition": "attachment; filename=agent_logs.json"
                }
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to export logs: {e}")
        raise HTTPException(status_code=500, detail="导出失败")


# 用于其他服务记录日志的便捷函数
def log_agent_interaction(
    agent_id: str,
    agent_name: str,
    interaction_type: str,
    direction: str,
    content: str,
    response: str = None,
    metadata: dict = None,
    duration_ms: int = None,
    success: bool = True,
    error_message: str = None
):
    """
    便捷函数 - 记录Agent交互
    
    其他服务可以直接调用此函数记录交互
    """
    service = AgentInteractionLogService()
    
    service.log_interaction(
        agent_id=agent_id,
        agent_name=agent_name,
        interaction_type=interaction_type,
        direction=direction,
        content=content,
        response=response,
        metadata=metadata,
        duration_ms=duration_ms,
        success=success,
        error_message=error_message
    )
