"""
Notification API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.notification_service import NotificationService

router = APIRouter()


class NotificationCreate(BaseModel):
    """Create notification request."""
    type: str
    title: str
    message: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None


@router.get("")
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get notifications."""
    service = NotificationService(db)
    notifications = service.get_notifications(unread_only=unread_only, limit=limit)
    
    return {
        "count": len(notifications),
        "unread_count": service.get_unread_count(),
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "task_id": n.task_id,
                "agent_id": n.agent_id,
                "is_read": n.is_read == "true",
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]
    }


@router.get("/count")
async def get_unread_count(
    db: Session = Depends(get_db),
):
    """Get unread notification count."""
    service = NotificationService(db)
    return {
        "unread_count": service.get_unread_count()
    }


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    service = NotificationService(db)
    success = service.mark_as_read(notification_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.post("/read-all")
async def mark_all_as_read(
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    service = NotificationService(db)
    count = service.mark_all_as_read()
    
    return {
        "success": True,
        "message": f"{count} notifications marked as read",
        "count": count
    }