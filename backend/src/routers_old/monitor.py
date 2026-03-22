"""
Task monitoring API routes.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.task_monitor_service import TaskMonitorService

router = APIRouter()


@router.get("/overdue")
async def get_overdue_tasks(
    db: Session = Depends(get_db),
):
    """
    Get all overdue tasks.
    
    Tasks are overdue if assigned but not started within the configured timeout.
    """
    service = TaskMonitorService(db)
    overdue = service.get_overdue_tasks()
    
    return {
        "overdue_count": len(overdue),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "assigned_at": task.assigned_at.isoformat() if task.assigned_at else None,
                "agent_id": task.agent_id,
            }
            for task in overdue
        ]
    }


@router.post("/check")
async def check_overdue_tasks(
    db: Session = Depends(get_db),
):
    """
    Check for new overdue tasks.
    
    This will scan all assigned tasks and mark those that have exceeded
the configured timeout as overdue.
    
    Returns:
        List of newly detected overdue tasks.
    """
    service = TaskMonitorService(db)
    newly_overdue = service.check_overdue_tasks()
    
    return {
        "checked": True,
        "newly_overdue_count": len(newly_overdue),
        "newly_overdue": newly_overdue,
    }


@router.get("/summary")
async def get_task_status_summary(
    db: Session = Depends(get_db),
):
    """Get summary of all task statuses including overdue count."""
    service = TaskMonitorService(db)
    summary = service.get_task_status_summary()
    
    return summary


@router.post("/{task_id}/acknowledge")
async def acknowledge_overdue(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Acknowledge an overdue task (mark as notified)."""
    service = TaskMonitorService(db)
    success = service.acknowledge_overdue(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "success": True,
        "message": f"Task {task_id} acknowledged",
    }


@router.post("/{task_id}/clear-overdue")
async def clear_overdue_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Clear overdue status for a task."""
    service = TaskMonitorService(db)
    success = service.clear_overdue_status(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "success": True,
        "message": f"Overdue status cleared for task {task_id}",
    }