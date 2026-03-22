"""
Optimized Workflow Router
优化后的工作流路由 - 支持分页
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from services.optimized_workflow_query_service import OptimizedWorkflowQueryService
from utils.pagination import PaginationHelper
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflows-optimized", tags=["workflows-optimized"])


@router.get("/{workflow_id}")
async def get_workflow_detail_optimized(
    workflow_id: str,
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    获取工作流详情（优化版本）
    
    - 使用joinedload预加载assignee信息
    - 单次聚合查询统计信息
    - 限制历史记录返回50条
    """
    service = OptimizedWorkflowQueryService(db)
    
    try:
        result = service.get_workflow_detail_optimized(workflow_id, agent_id)
        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get workflow detail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("")
async def list_workflows_optimized(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大100"),
    db: Session = Depends(get_db)
):
    """
    获取工作流列表（优化版本）
    
    - 支持分页
    - 支持按员工筛选
    - 支持按状态筛选
    - 批量获取统计信息
    """
    service = OptimizedWorkflowQueryService(db)
    
    try:
        result = service.get_workflow_list_optimized(
            agent_id=agent_id,
            status=status,
            page=page,
            page_size=page_size
        )
        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agent/{agent_id}/pending-optimized")
async def get_agent_pending_workflows_optimized(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    获取员工待办工作流（优化版本）
    
    - 使用JOIN一次性获取工作流和步骤
    """
    service = OptimizedWorkflowQueryService(db)
    
    try:
        result = service.get_agent_pending_workflows_optimized(agent_id)
        return {
            "success": True,
            "workflows": result,
            "count": len(result)
        }
    except Exception as e:
        logger.error(f"Failed to get pending workflows: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
