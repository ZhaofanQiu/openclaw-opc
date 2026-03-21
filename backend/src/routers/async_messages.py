"""
异步消息 API 路由

支持长时间运行的Agent通信
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import AsyncMessage, AsyncMessageStatus, AsyncMessageType, Agent
from src.services.async_message_service import AsyncMessageService
from src.utils.openclaw_config import send_message_to_agent
from src.utils.logging_config import get_logger
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/async-messages", tags=["Async Messages"])
logger = get_logger(__name__)


# 请求/响应模型

class SendMessageRequest(BaseModel):
    """发送异步消息请求"""
    recipient_id: str = Field(..., description="接收者Agent内部ID")
    content: str = Field(..., min_length=1, description="消息内容")
    subject: str = Field(default="", description="消息主题")
    message_type: str = Field(default="chat", description="消息类型: chat/task/system")
    related_task_id: Optional[str] = Field(None, description="关联任务ID")
    timeout_seconds: int = Field(default=1800, description="超时时间（秒），默认30分钟")


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool
    message_id: str
    status: str
    created_at: str
    check_url: str


class MessageStatusResponse(BaseModel):
    """消息状态响应"""
    id: str
    status: str
    sender_name: str
    recipient_name: str
    content: str
    created_at: str
    elapsed_seconds: float
    timeout_seconds: int
    response_content: Optional[str] = None
    response_summary: Optional[str] = None
    error_message: Optional[str] = None


class MessageListResponse(BaseModel):
    """消息列表响应"""
    messages: List[dict]
    total: int
    pending_count: int


# 后台处理任务

async def process_message_async(message_id: str, db_session=None):
    """
    后台处理消息发送
    
    这是真正的发送逻辑，在后台执行，不阻塞API响应
    """
    # 创建新的数据库会话
    from src.database import SessionLocal
    
    if db_session is None:
        db = SessionLocal()
    else:
        db = db_session
    
    try:
        service = AsyncMessageService(db)
        message = service.get_message(message_id)
        
        if not message:
            logger.error(f"Message {message_id} not found")
            return
        
        # 更新状态为发送中
        service.update_status(message_id, AsyncMessageStatus.SENDING.value)
        logger.info(f"Processing message {message_id} to agent {message.recipient_agent_id}")
        
        # 调用 OpenClaw 发送消息
        try:
            result = send_message_to_agent(
                agent_id=message.recipient_agent_id,
                message=message.content,
                timeout=message.timeout_seconds,
            )
            
            if result and result.get("text"):
                # 成功收到回复
                service.save_response(
                    message_id=message_id,
                    response_content=result.get("text"),
                    tokens_input=result.get("tokens_input", 0),
                    tokens_output=result.get("tokens_output", 0),
                )
                logger.info(f"Message {message_id} received response")
            else:
                # 发送成功但没有回复内容
                service.update_status(
                    message_id=message_id,
                    status=AsyncMessageStatus.FAILED.value,
                    error_message="No response from agent",
                )
                logger.warning(f"Message {message_id} no response")
                
        except Exception as e:
            # 发送失败
            error_msg = str(e)
            logger.error(f"Failed to send message {message_id}: {error_msg}")
            
            # 检查是否需要重试
            message = service.get_message(message_id)
            if message.retry_count < message.max_retries:
                message.retry_count += 1
                db.commit()
                logger.info(f"Retrying message {message_id}, attempt {message.retry_count}")
                # 递归重试
                await process_message_async(message_id, db)
            else:
                service.update_status(
                    message_id=message_id,
                    status=AsyncMessageStatus.FAILED.value,
                    error_message=error_msg,
                )
    
    except Exception as e:
        logger.error(f"Error in process_message_async: {e}")
    
    finally:
        if db_session is None:
            db.close()


# API 路由

@router.post("/send", response_model=SendMessageResponse)
@limiter.limit(RATE_LIMITS["create"])
async def send_message(
    request: Request,
    data: SendMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    发送异步消息给Agent
    
    立即返回消息ID，后台处理发送。
    用户可以通过查询接口查看状态和回复。
    
    **特点**:
    - 不阻塞UI，发送后可关闭窗口
    - 30分钟超时容忍
    - 支持重试机制
    
    **示例请求**:
    ```json
    {
        "recipient_id": "agent_abc123",
        "content": "请帮我分析这个数据",
        "subject": "数据分析请求"
    }
    ```
    
    **示例响应**:
    ```json
    {
        "success": true,
        "message_id": "msg_xyz789",
        "status": "pending",
        "created_at": "2026-03-22T05:30:00",
        "check_url": "/api/async-messages/msg_xyz789"
    }
    ```
    """
    service = AsyncMessageService(db)
    
    # 获取当前用户信息（从session或API key）
    # TODO: 实现用户认证
    sender_id = "user_001"  # 临时
    sender_name = "用户"  # 临时
    
    try:
        # 创建消息记录
        message = service.create_message(
            sender_id=sender_id,
            sender_type="user",
            sender_name=sender_name,
            recipient_id=data.recipient_id,
            content=data.content,
            message_type=data.message_type,
            subject=data.subject,
            related_task_id=data.related_task_id,
            timeout_seconds=data.timeout_seconds,
        )
        
        # 提交后台任务
        background_tasks.add_task(process_message_async, message.id)
        
        logger.info(f"Created async message {message.id}, queued for processing")
        
        return {
            "success": True,
            "message_id": message.id,
            "status": message.status,
            "created_at": message.created_at.isoformat(),
            "check_url": f"/api/async-messages/{message.id}",
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        raise HTTPException(status_code=500, detail="Failed to create message")


@router.get("/{message_id}", response_model=MessageStatusResponse)
async def get_message_status(
    message_id: str,
    db: Session = Depends(get_db),
):
    """
    获取消息状态和回复
    
    查询消息的处理状态，如果已回复则包含回复内容。
    
    **状态说明**:
    - `pending`: 待发送
    - `sending`: 发送中
    - `sent`: 已发送
    - `responded`: 已回复（可查看response_content）
    - `failed`: 发送失败
    - `timeout`: 超时（30分钟无回复）
    """
    service = AsyncMessageService(db)
    message = service.get_message(message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return service.to_dict(message)


@router.get("/user/{user_id}", response_model=MessageListResponse)
async def get_user_messages(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    获取用户的消息列表
    
    支持按状态筛选，查看历史消息。
    """
    service = AsyncMessageService(db)
    messages = service.get_messages_for_user(user_id, status, limit)
    
    pending_count = len([m for m in messages if m.status in ["pending", "sending", "sent"]])
    
    return {
        "messages": [service.to_dict(m) for m in messages],
        "total": len(messages),
        "pending_count": pending_count,
    }


@router.get("/agent/{agent_id}", response_model=MessageListResponse)
async def get_agent_messages(
    agent_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    获取Agent收到的消息列表
    """
    query = db.query(AsyncMessage).filter(AsyncMessage.recipient_id == agent_id)
    
    if status:
        query = query.filter(AsyncMessage.status == status)
    
    messages = query.order_by(AsyncMessage.created_at.desc()).limit(limit).all()
    
    service = AsyncMessageService(db)
    pending_count = len([m for m in messages if m.status in ["pending", "sending", "sent"]])
    
    return {
        "messages": [service.to_dict(m) for m in messages],
        "total": len(messages),
        "pending_count": pending_count,
    }


@router.post("/{message_id}/retry")
async def retry_message(
    message_id: str,
    db: Session = Depends(get_db),
):
    """
    重试失败的消息
    
    只有状态为 `failed` 或 `timeout` 的消息可以重试。
    """
    service = AsyncMessageService(db)
    message = service.get_message(message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.status not in [AsyncMessageStatus.FAILED.value, AsyncMessageStatus.TIMEOUT.value]:
        raise HTTPException(status_code=400, detail=f"Cannot retry message with status: {message.status}")
    
    # 重置状态
    message.status = AsyncMessageStatus.PENDING.value
    message.retry_count = 0
    message.error_message = None
    db.commit()
    
    # 重新提交后台任务
    from fastapi import BackgroundTasks
    background_tasks = BackgroundTasks()
    background_tasks.add_task(process_message_async, message.id)
    
    return {
        "success": True,
        "message_id": message_id,
        "status": "pending",
    }


@router.delete("/{message_id}")
async def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
):
    """删除消息"""
    service = AsyncMessageService(db)
    
    if not service.get_message(message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    
    service.delete_message(message_id)
    
    return {"success": True, "message_id": message_id}


@router.post("/cleanup/expired")
async def cleanup_expired_messages(
    db: Session = Depends(get_db),
):
    """
    清理超时消息
    
    检查所有待处理消息，将超过30分钟的标记为超时。
    可由定时任务调用。
    """
    service = AsyncMessageService(db)
    expired = service.check_expired_messages()
    
    return {
        "success": True,
        "expired_count": len(expired),
        "expired_ids": [m.id for m in expired],
    }
