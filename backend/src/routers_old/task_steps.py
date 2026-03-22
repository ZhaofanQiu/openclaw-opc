"""
任务步骤 API 路由
离线聊天协作系统的核心 API
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.task_step_service import TaskStepService
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/task-steps", tags=["Task Steps"])


# ============ 请求/响应模型 ============

class CreateStepRequest(BaseModel):
    """创建任务步骤请求"""
    task_id: str = Field(..., description="任务ID")
    step_index: int = Field(default=0, description="步骤序号")
    step_name: str = Field(..., description="步骤名称")
    assigner_id: str = Field(..., description="分配者ID")
    assigner_type: str = Field(default="user", description="分配者类型: user|agent")
    assigner_name: str = Field(default="", description="分配者名称")
    executor_id: str = Field(..., description="执行员工ID")
    step_description: str = Field(default="", description="步骤描述")
    input_context: Optional[dict] = Field(default=None, description="输入上下文")
    budget_tokens: int = Field(default=1000, description="Token预算")
    prev_step_id: Optional[str] = Field(default=None, description="上一步ID")
    next_step_id: Optional[str] = Field(default=None, description="下一步ID")


class AssignStepRequest(BaseModel):
    """分配任务请求"""
    assignment_content: str = Field(..., description="任务分配内容（完整消息）")
    sender_type: str = Field(default="user", description="发送者类型")
    sender_id: str = Field(default="system", description="发送者ID")
    sender_name: str = Field(default="系统", description="发送者名称")


class AddMessageRequest(BaseModel):
    """添加消息请求"""
    sender_id: str = Field(..., description="发送者ID")
    sender_type: str = Field(..., description="发送者类型: user|agent|system")
    sender_name: str = Field(..., description="发送者名称")
    content: str = Field(..., description="消息内容")
    message_type: str = Field(default="reply", description="消息类型")
    attachments: Optional[List[dict]] = Field(default=None, description="附件列表")


class CompleteStepRequest(BaseModel):
    """完成任务请求"""
    result_summary: str = Field(..., description="结果摘要")
    output_result: Optional[dict] = Field(default=None, description="结构化输出结果")


class ReworkRequest(BaseModel):
    """返工请求"""
    rework_reason: str = Field(..., description="返工原因")
    suggestions: str = Field(default="", description="改进建议")
    requester_id: str = Field(..., description="请求者ID")
    requester_type: str = Field(default="agent", description="请求者类型")


class FailStepRequest(BaseModel):
    """任务失败请求"""
    fail_reason: str = Field(..., description="失败原因")
    error_details: str = Field(default="", description="错误详情")


class SettleStepRequest(BaseModel):
    """结算任务请求"""
    score: int = Field(..., ge=1, le=5, description="评分 1-5")
    feedback: str = Field(default="", description="文字反馈")
    settled_by: str = Field(..., description="结算人ID")
    bonus_tokens: int = Field(default=0, description="奖励token数")


class StepResponse(BaseModel):
    """步骤响应"""
    id: str
    task_id: str
    step_index: int
    step_name: str
    step_description: str
    assigner_id: str
    assigner_type: str
    assigner_name: str
    executor_id: str
    status: str
    next_step_id: Optional[str]
    prev_step_id: Optional[str]
    rework_count: int
    max_rework: int
    budget_tokens: int
    actual_tokens: int
    score: Optional[int]
    settled: bool
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    step_id: str
    sender_id: str
    sender_type: str
    sender_name: str
    content: str
    message_type: str
    attachments: List[dict]
    is_read: bool
    created_at: str


class StepDetailResponse(BaseModel):
    """步骤详情响应（包含聊天记录）"""
    step: StepResponse
    messages: List[MessageResponse]
    unread_count: int


class CompleteResponse(BaseModel):
    """完成响应"""
    step: StepResponse
    next_step: Optional[StepResponse]
    is_final: bool


# ============ API 端点 ============

@router.post("/create", response_model=StepResponse)
@limiter.limit(RATE_LIMITS["create"])
async def create_step(
    request: Request,  # Required by slowapi
    data: CreateStepRequest,
    db: Session = Depends(get_db),
):
    """
    创建任务步骤
    
    **示例请求**:
    ```json
    {
        "task_id": "task_xxx",
        "step_name": "数据分析",
        "assigner_id": "user_xxx",
        "assigner_type": "user",
        "executor_id": "agent_xxx",
        "step_description": "分析销售数据并生成报告",
        "budget_tokens": 2000
    }
    ```
    """
    service = TaskStepService(db)
    step = service.create_step(
        task_id=data.task_id,
        step_index=data.step_index,
        step_name=data.step_name,
        assigner_id=data.assigner_id,
        assigner_type=data.assigner_type,
        assigner_name=data.assigner_name,
        executor_id=data.executor_id,
        step_description=data.step_description,
        input_context=data.input_context,
        budget_tokens=data.budget_tokens,
        prev_step_id=data.prev_step_id,
        next_step_id=data.next_step_id,
    )
    return step.to_dict()


@router.post("/{step_id}/assign")
async def assign_step(
    step_id: str,
    request: AssignStepRequest,
    db: Session = Depends(get_db),
):
    """
    分配任务给员工（发送第一条消息）
    
    这会创建任务分配消息并通知员工。
    """
    service = TaskStepService(db)
    message = service.assign_step(
        step_id=step_id,
        assignment_content=request.assignment_content,
        sender_type=request.sender_type,
        sender_id=request.sender_id,
        sender_name=request.sender_name,
    )
    return {"success": True, "message": message.to_dict()}


@router.get("/{step_id}", response_model=StepDetailResponse)
async def get_step_detail(
    step_id: str,
    reader_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    获取任务步骤详情（包含聊天记录）
    
    如果提供 reader_id，会自动标记该用户的消息为已读。
    """
    service = TaskStepService(db)
    step = service.get_step(step_id)
    
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # 获取消息
    messages = service.get_step_messages(step_id)
    
    # 标记已读
    if reader_id:
        service.mark_messages_read(step_id, reader_id)
        unread_count = 0
    else:
        unread_count = service.get_unread_count(step_id, reader_id or "")
    
    return {
        "step": step.to_dict(),
        "messages": [m.to_dict() for m in messages],
        "unread_count": unread_count,
    }


@router.get("/task/{task_id}")
async def get_task_steps(
    task_id: str,
    db: Session = Depends(get_db),
):
    """获取任务的所有步骤"""
    service = TaskStepService(db)
    steps = service.get_task_steps(task_id)
    return {"steps": [s.to_dict() for s in steps], "total": len(steps)}


@router.post("/{step_id}/messages", response_model=MessageResponse)
async def add_message(
    step_id: str,
    request: AddMessageRequest,
    db: Session = Depends(get_db),
):
    """
    添加消息到聊天记录
    
    支持员工回复、发布者反馈、系统消息等。
    """
    service = TaskStepService(db)
    message = service.add_message(
        step_id=step_id,
        sender_id=request.sender_id,
        sender_type=request.sender_type,
        sender_name=request.sender_name,
        content=request.content,
        message_type=request.message_type,
        attachments=request.attachments,
    )
    return message.to_dict()


@router.get("/{step_id}/messages")
async def get_messages(
    step_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """获取步骤的聊天记录"""
    service = TaskStepService(db)
    messages = service.get_step_messages(step_id, limit=limit)
    return {"messages": [m.to_dict() for m in messages], "total": len(messages)}


@router.post("/{step_id}/start", response_model=StepResponse)
async def start_execution(
    step_id: str,
    db: Session = Depends(get_db),
):
    """
    员工开始执行任务
    
    状态从 assigned 变为 in_progress。
    """
    service = TaskStepService(db)
    try:
        step = service.start_execution(step_id)
        return step.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{step_id}/complete", response_model=CompleteResponse)
async def complete_step(
    step_id: str,
    request: CompleteStepRequest,
    db: Session = Depends(get_db),
):
    """
    员工完成任务步骤
    
    - 如果是最后一步，通知任务发布者评价
    - 如果有下一步，自动推进并通知下一个员工
    """
    service = TaskStepService(db)
    try:
        result = service.complete_step(
            step_id=step_id,
            result_summary=request.result_summary,
            output_result=request.output_result,
        )
        return {
            "step": result["step"].to_dict(),
            "next_step": result["next_step"].to_dict() if result["next_step"] else None,
            "is_final": result["is_final"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{step_id}/rework", response_model=StepResponse)
async def request_rework(
    step_id: str,
    request: ReworkRequest,
    db: Session = Depends(get_db),
):
    """
    请求返工（退回上一步）
    
    当前步骤必须是 in_progress 状态。
    """
    service = TaskStepService(db)
    try:
        prev_step = service.request_rework(
            step_id=step_id,
            rework_reason=request.rework_reason,
            suggestions=request.suggestions,
            requester_id=request.requester_id,
            requester_type=request.requester_type,
        )
        return prev_step.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{step_id}/fail", response_model=StepResponse)
async def fail_step(
    step_id: str,
    request: FailStepRequest,
    db: Session = Depends(get_db),
):
    """
    员工报告任务失败
    
    任务将暂停，通知任务发布者介入。
    """
    service = TaskStepService(db)
    try:
        step = service.fail_step(
            step_id=step_id,
            fail_reason=request.fail_reason,
            error_details=request.error_details,
        )
        return step.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{step_id}/settle", response_model=StepResponse)
async def settle_step(
    step_id: str,
    request: SettleStepRequest,
    db: Session = Depends(get_db),
):
    """
    发布者评价并结算任务
    
    评分 1-5 分，可选文字反馈和奖励。
    """
    service = TaskStepService(db)
    try:
        step = service.settle_step(
            step_id=step_id,
            score=request.score,
            feedback=request.feedback,
            settled_by=request.settled_by,
            bonus_tokens=request.bonus_tokens,
        )
        return step.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agent/{agent_id}")
async def get_agent_steps(
    agent_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    获取员工的任务步骤列表
    
    可用于员工的"我的任务"页面。
    """
    service = TaskStepService(db)
    steps = service.get_agent_steps(agent_id, status=status, limit=limit)
    return {
        "steps": [s.to_dict() for s in steps],
        "total": len(steps),
        "status_filter": status,
    }


@router.get("/{step_id}/unread")
async def get_unread_count(
    step_id: str,
    reader_id: str,
    db: Session = Depends(get_db),
):
    """获取未读消息数"""
    service = TaskStepService(db)
    count = service.get_unread_count(step_id, reader_id)
    return {"unread_count": count}


@router.post("/{step_id}/read")
async def mark_read(
    step_id: str,
    reader_id: str,
    db: Session = Depends(get_db),
):
    """标记消息为已读"""
    service = TaskStepService(db)
    count = service.mark_messages_read(step_id, reader_id)
    return {"marked_count": count}
