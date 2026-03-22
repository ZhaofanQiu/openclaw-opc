"""
Agent Communication API routes.

Endpoints for inter-agent messaging and notifications.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.communication_service import (
    CommunicationService, 
    MessagePriority, 
    MessageStatus
)
from src.utils.rate_limit import limiter, RATE_LIMITS
from src.utils.current_user import get_user_id_safe

router = APIRouter(prefix="/api/communication", tags=["Agent Communication"])


# Schemas

class SendMessageRequest(BaseModel):
    """Request to send a message."""
    recipient_id: str = Field(..., description="Recipient agent ID")
    content: str = Field(..., min_length=1, description="Message content")
    subject: Optional[str] = Field(None, description="Optional subject")
    priority: str = Field(default="normal", description="low/normal/high/urgent")
    related_task_id: Optional[str] = Field(None, description="Related task ID")


class BroadcastRequest(BaseModel):
    """Request to broadcast a message."""
    recipient_ids: List[str] = Field(..., min_items=1, description="List of recipient IDs")
    content: str = Field(..., min_length=1, description="Message content")
    subject: Optional[str] = Field(None, description="Optional subject")
    priority: str = Field(default="normal", description="low/normal/high/urgent")


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    sender_id: str
    sender_name: str
    recipient_id: str
    recipient_name: str
    subject: str
    content: str
    priority: str
    status: str
    related_task_id: Optional[str]
    related_type: Optional[str]
    created_at: str
    sent_at: Optional[str]
    delivered_at: Optional[str]


# Routes

@router.post("/send")
@limiter.limit(RATE_LIMITS["create"])
async def send_message(
    request: Request,
    data: SendMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message from current agent to another agent.
    
    Creates a pending message that will be delivered via Partner Agent.
    """
    # Get sender_id from authenticated user context
    sender_id = get_user_id_safe(fallback="system")
    
    service = CommunicationService(db)
    
    # Validate recipient exists
    from src.models import Agent
    recipient = db.query(Agent).filter(Agent.id == data.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    message = service.send_message(
        sender_id=sender_id,
        recipient_id=data.recipient_id,
        content=data.content,
        subject=data.subject,
        priority=data.priority,
        related_task_id=data.related_task_id,
        related_type="direct_message",
    )
    
    # Attempt immediate delivery
    result = service.deliver_message(message.id)
    
    return {
        "success": True,
        "message_id": message.id,
        "status": message.status,
        "delivery": result,
    }


@router.post("/broadcast")
@limiter.limit(RATE_LIMITS["create"])
async def broadcast_message(
    request: Request,
    data: BroadcastRequest,
    db: Session = Depends(get_db),
):
    """
    Broadcast a message to multiple agents.
    
    Creates individual messages for each recipient.
    """
    sender_id = get_user_id_safe(fallback="system")
    
    service = CommunicationService(db)
    
    messages = service.broadcast_message(
        sender_id=sender_id,
        recipient_ids=data.recipient_ids,
        content=data.content,
        subject=data.subject,
        priority=data.priority,
    )
    
    return {
        "success": True,
        "message_count": len(messages),
        "recipient_count": len(data.recipient_ids),
        "message_ids": [m.id for m in messages],
    }


@router.get("/messages")
async def get_messages(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get messages.
    
    Filter by agent involvement or status.
    """
    service = CommunicationService(db)
    messages = service.get_messages(
        agent_id=agent_id,
        status=status,
        limit=limit,
    )
    
    from src.models import Agent
    
    result = []
    for msg in messages:
        sender = db.query(Agent).filter(Agent.id == msg.sender_id).first()
        recipient = db.query(Agent).filter(Agent.id == msg.recipient_id).first()
        
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": sender.name if sender else "Unknown",
            "recipient_id": msg.recipient_id,
            "recipient_name": recipient.name if recipient else "Unknown",
            "subject": msg.subject,
            "content": msg.content,
            "priority": msg.priority,
            "status": msg.status,
            "related_task_id": msg.related_task_id,
            "related_type": msg.related_type,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
            "delivered_at": msg.delivered_at.isoformat() if msg.delivered_at else None,
        })
    
    return result


@router.get("/inbox/{agent_id}")
async def get_inbox(
    agent_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get inbox for an agent (received messages).
    """
    service = CommunicationService(db)
    messages = service.get_messages(
        recipient_id=agent_id,
        limit=limit,
    )
    
    from src.models import Agent
    
    result = []
    for msg in messages:
        sender = db.query(Agent).filter(Agent.id == msg.sender_id).first()
        
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": sender.name if sender else "Unknown",
            "sender_emoji": sender.emoji if sender else "🤖",
            "subject": msg.subject,
            "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
            "priority": msg.priority,
            "status": msg.status,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "is_read": msg.status in [MessageStatus.DELIVERED.value, MessageStatus.SENT.value],
        })
    
    return {
        "agent_id": agent_id,
        "unread_count": len([m for m in messages if m.status == MessageStatus.PENDING.value]),
        "messages": result,
    }


@router.get("/conversation/{agent1_id}/{agent2_id}")
async def get_conversation(
    agent1_id: str,
    agent2_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get conversation history between two agents.
    """
    service = CommunicationService(db)
    messages = service.get_conversation(agent1_id, agent2_id, limit)
    
    from src.models import Agent
    
    result = []
    for msg in messages:
        sender = db.query(Agent).filter(Agent.id == msg.sender_id).first()
        
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": sender.name if sender else "Unknown",
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "is_mine": msg.sender_id == agent1_id,
        })
    
    return {
        "agent1_id": agent1_id,
        "agent2_id": agent2_id,
        "messages": list(reversed(result)),  # Oldest first
    }


@router.post("/messages/{message_id}/deliver")
async def deliver_message(
    message_id: str,
    db: Session = Depends(get_db),
):
    """
    Manually trigger delivery of a pending message.
    
    This is typically called by Partner Agent.
    """
    service = CommunicationService(db)
    result = service.deliver_message(message_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/messages/{message_id}/mark-delivered")
async def mark_delivered(
    message_id: str,
    db: Session = Depends(get_db),
):
    """
    Mark a message as delivered (confirm receipt).
    
    Called by recipient agent to confirm message received.
    """
    service = CommunicationService(db)
    message = service.mark_delivered(message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {
        "success": True,
        "message_id": message.id,
        "status": message.status,
    }


@router.post("/notify/task-assignment")
async def notify_task_assignment(
    request: Request,
    agent_id: str,
    task_id: str,
    task_title: str,
    task_description: str = "",
    db: Session = Depends(get_db),
):
    """
    Send task assignment notification to an agent.
    
    This is called automatically when a task is assigned.
    """
    service = CommunicationService(db)
    
    message = service.notify_task_assignment(
        agent_id=agent_id,
        task_id=task_id,
        task_title=task_title,
        task_description=task_description,
    )
    
    # Try to deliver immediately
    result = service.deliver_message(message.id)
    
    return {
        "success": True,
        "message_id": message.id,
        "notification_sent": result.get("success"),
    }


@router.get("/stats")
async def get_communication_stats(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get communication statistics.
    """
    service = CommunicationService(db)
    stats = service.get_stats(agent_id)
    
    return stats
