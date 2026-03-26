"""
opc-core: Partner API

Partner 员工交互 API

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.4
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from opc_database.repositories import (
    EmployeeRepository,
    PartnerMessageRepository,
)

from ..api.dependencies import (
    get_db_session,
    get_employee_repo,
    verify_api_key,
)
from ..services.partner_service import (
    ChatResult,
    PartnerChatError,
    PartnerNotFoundError,
    PartnerService,
)

router = APIRouter(prefix="/partner", tags=["Partner"])


# ============ 数据模型 ============


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, description="用户消息内容")
    partner_id: Optional[str] = Field(None, description="Partner 员工ID（可选）")


class ChatResponse(BaseModel):
    """对话响应"""
    reply: str = Field(..., description="Partner 回复内容")
    action_executed: Optional[str] = Field(None, description="执行的操作类型")
    action_result: Optional[Dict[str, Any]] = Field(None, description="操作执行结果")


class ChatHistoryItem(BaseModel):
    """历史消息项"""
    id: str
    partner_id: str
    role: str
    content: str
    has_action: bool
    action_type: Optional[str]
    action_result: Optional[Dict[str, Any]]
    created_at: str


class ClearHistoryResponse(BaseModel):
    """清空历史响应"""
    deleted_count: int = Field(..., description="删除的消息数量")


class PartnerStatusResponse(BaseModel):
    """Partner 状态响应"""
    has_partner: bool = Field(..., description="是否存在 Partner 员工")
    partner_id: Optional[str] = Field(None, description="Partner 员工ID")
    partner_name: Optional[str] = Field(None, description="Partner 名称")
    is_bound: bool = Field(..., description="是否已绑定 Agent")


# ============ 依赖注入 ============


async def get_partner_message_repo(
    session=Depends(get_db_session)
) -> PartnerMessageRepository:
    """获取 PartnerMessageRepository 实例"""
    return PartnerMessageRepository(session)


async def get_partner_service(
    message_repo: PartnerMessageRepository = Depends(get_partner_message_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
) -> PartnerService:
    """获取 PartnerService 实例"""
    return PartnerService(
        message_repo=message_repo,
        employee_repo=employee_repo
    )


# ============ API 路由 ============


@router.get("/status", response_model=PartnerStatusResponse)
async def get_partner_status(
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    _: str = Depends(verify_api_key)
) -> PartnerStatusResponse:
    """
    获取 Partner 状态
    
    检查是否存在 Partner 员工及其绑定状态
    """
    from opc_database.models import PositionLevel
    
    partner = await employee_repo.get_by_position_level(
        PositionLevel.PARTNER.value
    )
    
    if not partner:
        return PartnerStatusResponse(
            has_partner=False,
            is_bound=False
        )
    
    return PartnerStatusResponse(
        has_partner=True,
        partner_id=partner.id,
        partner_name=partner.name,
        is_bound=partner.is_bound == "true" and bool(partner.openclaw_agent_id)
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_partner(
    request: ChatRequest,
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> ChatResponse:
    """
    与 Partner 对话
    
    发送消息给 Partner 员工并获取回复。
    Partner 会解析消息并可能执行操作指令。
    
    请求示例:
        {
            "message": "帮我查看公司状态",
            "partner_id": "emp_xxx"  // 可选，自动查找
        }
    
    响应示例:
        {
            "reply": "当前公司有 5 名员工...",
            "action_executed": "get_company_status",
            "action_result": {...}
        }
    """
    try:
        result = await partner_service.chat(request.message)
        return ChatResponse(
            reply=result.reply,
            action_executed=result.action_executed,
            action_result=result.action_result
        )
    except PartnerNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PARTNER_NOT_FOUND",
                "message": str(e),
                "suggestion": "请先创建一个职位等级为 5 (Partner) 的员工"
            }
        )
    except PartnerChatError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CHAT_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"对话失败: {str(e)}"
            }
        )


@router.get("/history", response_model=List[ChatHistoryItem])
async def get_chat_history(
    partner_id: str = Query(..., description="Partner 员工ID"),
    limit: int = Query(20, ge=1, le=100, description="返回消息数量上限"),
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> List[ChatHistoryItem]:
    """
    获取聊天历史
    
    获取与 Partner 的最近对话记录
    """
    try:
        history = await partner_service.get_chat_history(
            partner_id=partner_id,
            limit=limit
        )
        return [ChatHistoryItem(**msg) for msg in history]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "HISTORY_ERROR",
                "message": f"获取历史失败: {str(e)}"
            }
        )


@router.delete("/history/{partner_id}", response_model=ClearHistoryResponse)
async def clear_chat_history(
    partner_id: str,
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> ClearHistoryResponse:
    """
    清空聊天历史
    
    删除指定 Partner 的所有聊天记录
    """
    try:
        deleted_count = await partner_service.clear_chat_history(partner_id)
        return ClearHistoryResponse(deleted_count=deleted_count)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "CLEAR_ERROR",
                "message": f"清空历史失败: {str(e)}"
            }
        )
