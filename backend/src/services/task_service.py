"""
Task service layer.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import Agent, AgentStatus, Task, TaskStatus


class TaskService:
    """Task service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "normal",
        estimated_cost: float = 0.0,
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            priority=priority,
            estimated_cost=estimated_cost,
            status=TaskStatus.PENDING.value,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.db.query(Task).filter(Task.id == task_id).first()
    
    def list_tasks(
        self,
        status: str = None,
        agent_id: str = None,
    ) -> List[Task]:
        """List tasks with filters."""
        query = self.db.query(Task)
        
        if status:
            query = query.filter(Task.status == status)
        
        if agent_id:
            agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
            if agent:
                query = query.filter(Task.agent_id == agent.id)
        
        return query.order_by(Task.created_at.desc()).all()
    
    def assign_task(self, task_id: str, agent_id: str) -> Task:
        """Assign task to agent."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found")
        
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Check agent has enough budget
        if task.estimated_cost > agent.remaining_budget:
            raise ValueError(
                f"Agent '{agent.name}' budget insufficient. "
                f"Required: {task.estimated_cost:.2f}, Remaining: {agent.remaining_budget:.2f}"
            )
        
        # Check agent is idle
        if agent.status != AgentStatus.IDLE.value:
            raise ValueError(f"Agent '{agent.name}' is not idle (status: {agent.status})")
        
        task.agent_id = agent.id
        task.status = TaskStatus.ASSIGNED.value
        task.assigned_at = datetime.utcnow()  # Record assignment time
        task.is_overdue = "false"  # Reset overdue status
        task.overdue_notified_at = None
        agent.status = AgentStatus.WORKING.value
        agent.current_task_id = task.id
        
        self.db.commit()
        self.db.refresh(task)
        
        # Create notification
        from src.services.notification_service import NotificationService
        notification_service = NotificationService(self.db)
        notification_service.notify_task_assigned(
            task_id=task.id,
            task_title=task.title,
            agent_name=agent.name
        )
        
        # Send task to Agent via execution service (v0.3.0 P0 - execution loop)
        try:
            from src.services.task_execution_service import TaskExecutionService
            execution_service = TaskExecutionService(self.db)
            result = execution_service.send_task_to_agent(task_id, agent_id)
            
            if result.get("success"):
                logger.info(
                    "task_auto_sent_to_agent",
                    task_id=task_id,
                    agent_id=agent_id,
                    session_id=result.get("session_id")
                )
            else:
                logger.warning(
                    "task_auto_send_failed",
                    task_id=task_id,
                    agent_id=agent_id,
                    error=result.get("error")
                )
                # Don't fail the assignment, just log the error
                # The task is still assigned, and the Agent can check via opc_check_task
        except Exception as e:
            logger.error(
                "task_auto_send_exception",
                task_id=task_id,
                agent_id=agent_id,
                error=str(e)
            )
            # Don't fail the assignment
        
        return task
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Task:
        """Update task details."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task '{task_id}' not found")
        
        # Update fields if provided
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if status is not None:
            task.status = status
        
        task.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(task)
        return task
