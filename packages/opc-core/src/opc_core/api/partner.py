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


# ========== Phase 2: 智能辅助请求/响应模型 ==========


class EmployeeAssistRequest(BaseModel):
    """辅助创建员工请求"""
    name: str = Field(..., min_length=1, max_length=50, description="员工姓名")
    job_type: str = Field(..., min_length=1, description="工种/岗位类型")
    user_intent: str = Field(..., min_length=1, description="用户需求描述")


class EmployeeAssistResponse(BaseModel):
    """辅助创建员工响应"""
    name: str
    job_type: str
    background: str
    personality: str
    working_style: str
    skills: List[str]
    suggested_avatar_emoji: str
    suggested_budget: float
    manual_content: str


class TaskAssistRequest(BaseModel):
    """辅助创建任务请求"""
    title: str = Field(..., min_length=1, max_length=100, description="任务标题")
    description: str = Field(..., min_length=1, description="任务描述")
    employee_id: Optional[str] = Field(None, description="指定员工ID（可选）")


class TaskAssistResponse(BaseModel):
    """辅助创建任务响应"""
    refined_title: str
    refined_description: str
    execution_steps: List[str]
    estimated_cost: float
    cost_reasoning: str
    suggested_employee_id: str
    suggested_employee_name: str
    employee_reasoning: str
    manual_content: str


class WorkflowAssistRequest(BaseModel):
    """辅助创建工作流请求"""
    description: str = Field(..., min_length=1, description="自然语言描述")


class WorkflowStepAssistResponse(BaseModel):
    """工作流步骤响应"""
    title: str
    description: str
    assigned_to: str
    employee_name: str
    estimated_cost: float
    cost_reasoning: str


class WorkflowAssistResponse(BaseModel):
    """辅助创建工作流响应"""
    name: str
    description: str
    steps: List[WorkflowStepAssistResponse]
    total_estimated_cost: float
    workflow_reasoning: str


class UpdateManualRequest(BaseModel):
    """更新手册请求"""
    current_content: str = Field(..., min_length=1, description="当前手册内容")
    user_request: str = Field(..., min_length=1, description="用户修改请求")


class UpdateManualResponse(BaseModel):
    """更新手册响应"""
    updated_content: str
    changes_summary: str


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


# ========== Phase 2: 智能辅助 API ==========


@router.post("/assist/create-employee", response_model=EmployeeAssistResponse)
async def assist_create_employee(
    request: EmployeeAssistRequest,
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> EmployeeAssistResponse:
    """
    智能辅助创建员工
    
    Partner 会阅读手册后设计员工形象，包括：
    - 背景故事
    - 性格特点
    - 行事风格
    - 技能列表
    - 推荐预算
    - 员工手册内容
    """
    try:
        result = await partner_service.assist_create_employee(
            name=request.name,
            job_type=request.job_type,
            user_intent=request.user_intent
        )
        return EmployeeAssistResponse(
            name=result.name,
            job_type=result.job_type,
            background=result.background,
            personality=result.personality,
            working_style=result.working_style,
            skills=result.skills,
            suggested_avatar_emoji=result.suggested_avatar_emoji,
            suggested_budget=result.suggested_budget,
            manual_content=result.manual_content
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
                "error": "ASSIST_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"辅助创建失败: {str(e)}"
            }
        )


@router.post("/assist/create-task", response_model=TaskAssistResponse)
async def assist_create_task(
    request: TaskAssistRequest,
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> TaskAssistResponse:
    """
    智能辅助创建任务
    
    Partner 会：
    - 细化任务需求和验收标准
    - 拆分执行步骤
    - 预估成本
    - 推荐员工
    - 生成任务手册
    """
    try:
        result = await partner_service.assist_create_task(
            title=request.title,
            description=request.description,
            employee_id=request.employee_id
        )
        return TaskAssistResponse(
            refined_title=result.refined_title,
            refined_description=result.refined_description,
            execution_steps=result.execution_steps,
            estimated_cost=result.estimated_cost,
            cost_reasoning=result.cost_reasoning,
            suggested_employee_id=result.suggested_employee_id,
            suggested_employee_name=result.suggested_employee_name,
            employee_reasoning=result.employee_reasoning,
            manual_content=result.manual_content
        )
    except PartnerNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PARTNER_NOT_FOUND",
                "message": str(e)
            }
        )
    except PartnerChatError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ASSIST_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"辅助创建失败: {str(e)}"
            }
        )


@router.post("/assist/create-workflow", response_model=WorkflowAssistResponse)
async def assist_create_workflow(
    request: WorkflowAssistRequest,
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> WorkflowAssistResponse:
    """
    一句话创建工作流
    
    用户输入: "帮我做一个内容创作流程，从选题到发布"
    
    Partner 会：
    - 拆分为合理步骤（3-5步）
    - 为每步匹配最佳员工
    - 预估每步成本
    - 返回可预览的工作流配置
    """
    try:
        result = await partner_service.assist_create_workflow(
            natural_language_description=request.description
        )
        return WorkflowAssistResponse(
            name=result.name,
            description=result.description,
            steps=[
                WorkflowStepAssistResponse(
                    title=step.title,
                    description=step.description,
                    assigned_to=step.assigned_to,
                    employee_name=step.employee_name,
                    estimated_cost=step.estimated_cost,
                    cost_reasoning=step.cost_reasoning
                )
                for step in result.steps
            ],
            total_estimated_cost=result.total_estimated_cost,
            workflow_reasoning=result.workflow_reasoning
        )
    except PartnerNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PARTNER_NOT_FOUND",
                "message": str(e)
            }
        )
    except PartnerChatError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ASSIST_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"辅助创建失败: {str(e)}"
            }
        )


@router.post("/assist/update-manual", response_model=UpdateManualResponse)
async def assist_update_company_manual(
    request: UpdateManualRequest,
    partner_service: PartnerService = Depends(get_partner_service),
    _: str = Depends(verify_api_key)
) -> UpdateManualResponse:
    """
    智能修改公司手册
    
    Partner 会：
    - 阅读现有公司手册
    - 根据用户请求修改内容
    - 返回更新后的完整手册
    """
    try:
        result = await partner_service.assist_update_company_manual(
            current_content=request.current_content,
            user_request=request.user_request
        )
        return UpdateManualResponse(
            updated_content=result.updated_content,
            changes_summary=result.changes_summary
        )
    except PartnerNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PARTNER_NOT_FOUND",
                "message": str(e)
            }
        )
    except PartnerChatError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ASSIST_ERROR",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": f"辅助更新失败: {str(e)}"
            }
        )
