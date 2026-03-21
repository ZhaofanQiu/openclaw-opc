"""
Fuse Event Service

Manages budget fuse events and post-fuse actions.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from src.models import BudgetFuseEvent, FuseAction, FuseEventStatus


class FuseService:
    """Service for managing budget fuse events."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_fuse_event(
        self,
        agent_id: str,
        fuse_type: str,
        threshold_percentage: float,
        budget_used: float,
        budget_total: float,
        task_id: Optional[str] = None,
        additional_data: Optional[Dict] = None,
    ) -> BudgetFuseEvent:
        """
        Record a new fuse event.
        
        Args:
            agent_id: Agent ID that triggered the fuse
            fuse_type: warning, pause, or fuse
            threshold_percentage: The percentage threshold that was hit
            budget_used: Amount of budget used
            budget_total: Total budget available
            task_id: Optional associated task ID
            additional_data: Additional JSON data
        
        Returns:
            Created fuse event
        """
        import json
        
        event = BudgetFuseEvent(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            task_id=task_id,
            fuse_type=fuse_type,
            threshold_percentage=threshold_percentage,
            budget_used=budget_used,
            budget_total=budget_total,
            status=FuseEventStatus.PENDING.value,
            additional_data=json.dumps(additional_data) if additional_data else None,
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        return event
    
    def get_pending_events(
        self,
        agent_id: Optional[str] = None,
    ) -> List[BudgetFuseEvent]:
        """
        Get pending fuse events.
        
        Args:
            agent_id: Optional filter by agent
        
        Returns:
            List of pending fuse events
        """
        query = self.db.query(BudgetFuseEvent).filter(
            BudgetFuseEvent.status.in_([
                FuseEventStatus.TRIGGERED.value,
                FuseEventStatus.PENDING.value,
            ])
        )
        
        if agent_id:
            query = query.filter(BudgetFuseEvent.agent_id == agent_id)
        
        return query.order_by(BudgetFuseEvent.created_at.desc()).all()
    
    def get_event(self, event_id: str) -> Optional[BudgetFuseEvent]:
        """Get a specific fuse event."""
        return self.db.query(BudgetFuseEvent).filter(
            BudgetFuseEvent.id == event_id
        ).first()
    
    def resolve_event(
        self,
        event_id: str,
        action: str,
        resolved_by: str,
        resolution_note: Optional[str] = None,
        additional_data: Optional[Dict] = None,
    ) -> Optional[BudgetFuseEvent]:
        """
        Resolve a fuse event with an action.
        
        Args:
            event_id: Fuse event ID
            action: FuseAction value
            resolved_by: Employee ID who resolved
            resolution_note: Optional note
            additional_data: Additional resolution data
        
        Returns:
            Updated event or None if not found
        """
        import json
        
        event = self.get_event(event_id)
        if not event:
            return None
        
        event.status = FuseEventStatus.RESOLVED.value
        event.resolved_action = action
        event.resolved_by = resolved_by
        event.resolved_at = datetime.utcnow()
        event.resolution_note = resolution_note
        
        if additional_data:
            # Merge with existing additional_data
            existing = {}
            if event.additional_data:
                import json
                existing = json.loads(event.additional_data)
            existing.update(additional_data)
            event.additional_data = json.dumps(existing)
        
        self.db.commit()
        self.db.refresh(event)
        
        return event
    
    def add_budget_resolution(
        self,
        event_id: str,
        additional_budget: float,
        reason: str,
        resolved_by: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve fuse event by adding budget.
        
        Args:
            event_id: Fuse event ID
            additional_budget: Amount to add
            reason: Reason for adding budget
            resolved_by: Employee ID
        
        Returns:
            Resolution result with updated budget info
        """
        from src.models import Agent, BudgetTransaction
        
        event = self.get_event(event_id)
        if not event:
            return None
        
        # Get agent
        agent = self.db.query(Agent).filter(Agent.id == event.agent_id).first()
        if not agent:
            return None
        
        old_budget = agent.monthly_budget
        agent.monthly_budget += additional_budget
        
        # Create budget adjustment transaction
        transaction = BudgetTransaction(
            id=str(uuid.uuid4())[:8],
            agent_id=agent.id,
            task_id=event.task_id,
            transaction_type="adjustment",
            amount=additional_budget,
            description=f"追加预算: {reason}",
        )
        self.db.add(transaction)
        
        # Resolve the event
        self.resolve_event(
            event_id=event_id,
            action=FuseAction.ADD_BUDGET.value,
            resolved_by=resolved_by,
            resolution_note=reason,
            additional_data={
                "additional_budget": additional_budget,
                "old_budget": old_budget,
                "new_budget": agent.monthly_budget,
            }
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "old_budget": old_budget,
            "additional_budget": additional_budget,
            "new_budget": agent.monthly_budget,
            "remaining_budget": agent.remaining_budget,
        }
    
    def reassign_resolution(
        self,
        event_id: str,
        new_agent_id: str,
        reason: str,
        resolved_by: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve fuse event by reassigning task to another agent.
        
        Args:
            event_id: Fuse event ID
            new_agent_id: New agent ID to assign
            reason: Reason for reassignment
            resolved_by: Employee ID
        
        Returns:
            Resolution result
        """
        from src.models import Agent, Task
        
        event = self.get_event(event_id)
        if not event:
            return None
        
        if not event.task_id:
            return {"error": "No task associated with this fuse event"}
        
        # Get task
        task = self.db.query(Task).filter(Task.id == event.task_id).first()
        if not task:
            return None
        
        # Get new agent
        new_agent = self.db.query(Agent).filter(Agent.id == new_agent_id).first()
        if not new_agent:
            return {"error": f"Agent '{new_agent_id}' not found"}
        
        old_agent_id = task.assigned_to
        old_agent = None
        if old_agent_id:
            old_agent = self.db.query(Agent).filter(Agent.id == old_agent_id).first()
        
        # Reassign task
        task.assigned_to = new_agent_id
        task.status = "pending"  # Reset to pending for new agent
        
        # Update agent statuses
        if old_agent:
            old_agent.status = "idle"
            old_agent.current_task_id = None
        
        new_agent.status = "busy"
        new_agent.current_task_id = task.id
        
        # Resolve the event
        self.resolve_event(
            event_id=event_id,
            action=FuseAction.REASSIGN.value,
            resolved_by=resolved_by,
            resolution_note=f"重新分配给 {new_agent.name}: {reason}",
            additional_data={
                "old_agent_id": old_agent_id,
                "new_agent_id": new_agent_id,
                "new_agent_name": new_agent.name,
                "task_id": task.id,
            }
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "task_id": task.id,
            "task_title": task.title,
            "old_agent": old_agent.name if old_agent else None,
            "new_agent": new_agent.name,
            "reason": reason,
        }
    
    def split_task_resolution(
        self,
        event_id: str,
        sub_tasks: List[Dict[str, Any]],
        reason: str,
        resolved_by: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve fuse event by splitting task into sub-tasks.
        
        Args:
            event_id: Fuse event ID
            sub_tasks: List of sub-task definitions
            reason: Reason for splitting
            resolved_by: Employee ID
        
        Returns:
            Resolution result
        """
        from src.models import Agent, Task
        
        event = self.get_event(event_id)
        if not event:
            return None
        
        if not event.task_id:
            return {"error": "No task associated with this fuse event"}
        
        # Get original task
        original_task = self.db.query(Task).filter(Task.id == event.task_id).first()
        if not original_task:
            return None
        
        created_tasks = []
        for i, sub_task_def in enumerate(sub_tasks):
            sub_task = Task(
                id=str(uuid.uuid4())[:8],
                title=f"{original_task.title} (子任务 {i+1})",
                description=sub_task_def.get("description", ""),
                estimated_cost=sub_task_def.get("estimated_cost", original_task.estimated_cost / len(sub_tasks)),
                required_skills=original_task.required_skills,
                priority=original_task.priority,
                parent_task_id=original_task.id,
                status="pending",
            )
            self.db.add(sub_task)
            created_tasks.append({
                "id": sub_task.id,
                "title": sub_task.title,
                "estimated_cost": sub_task.estimated_cost,
            })
        
        # Mark original task as split
        original_task.status = "split"
        original_task.description = f"[已拆分] {original_task.description}"
        
        # Release agent
        if original_task.assigned_to:
            agent = self.db.query(Agent).filter(Agent.id == original_task.assigned_to).first()
            if agent:
                agent.status = "idle"
                agent.current_task_id = None
        
        original_task.assigned_to = None
        
        # Resolve the event
        self.resolve_event(
            event_id=event_id,
            action=FuseAction.SPLIT_TASK.value,
            resolved_by=resolved_by,
            resolution_note=f"拆分为 {len(sub_tasks)} 个子任务: {reason}",
            additional_data={
                "original_task_id": original_task.id,
                "sub_task_count": len(sub_tasks),
                "sub_tasks": created_tasks,
            }
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "original_task_id": original_task.id,
            "original_task_title": original_task.title,
            "sub_task_count": len(created_tasks),
            "sub_tasks": created_tasks,
        }
    
    def get_fuse_stats(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get fuse event statistics.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Statistics dict
        """
        from datetime import datetime, timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        events = self.db.query(BudgetFuseEvent).filter(
            BudgetFuseEvent.created_at >= cutoff
        ).all()
        
        total = len(events)
        resolved = len([e for e in events if e.status == FuseEventStatus.RESOLVED.value])
        pending = len([e for e in events if e.status in [
            FuseEventStatus.TRIGGERED.value,
            FuseEventStatus.PENDING.value,
        ]])
        
        by_type = {}
        for e in events:
            by_type[e.fuse_type] = by_type.get(e.fuse_type, 0) + 1
        
        by_action = {}
        for e in events:
            if e.resolved_action:
                by_action[e.resolved_action] = by_action.get(e.resolved_action, 0) + 1
        
        return {
            "period_days": days,
            "total_events": total,
            "resolved": resolved,
            "pending": pending,
            "resolution_rate": (resolved / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "by_action": by_action,
        }
