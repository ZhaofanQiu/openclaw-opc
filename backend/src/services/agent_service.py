"""
Agent service layer.
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import Agent, AgentStatus, BudgetTransaction, Task, TaskStatus, TransactionType


class AgentService:
    """Agent service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_agent(
        self,
        name: str,
        agent_id: str,
        emoji: str = "🧑‍💻",
        monthly_budget: float = 2000.0,
    ) -> Agent:
        """Create a new agent."""
        # Check if agent_id already exists
        existing = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if existing:
            raise ValueError(f"Agent with agent_id '{agent_id}' already exists")
        
        agent = Agent(
            id=str(uuid.uuid4())[:8],
            name=name,
            agent_id=agent_id,
            emoji=emoji,
            monthly_budget=monthly_budget,
            used_budget=0.0,
            status=AgentStatus.IDLE.value,
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by agent_id."""
        return self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    def list_agents(self) -> List[Agent]:
        """List all agents."""
        return self.db.query(Agent).all()
    
    def get_pending_task(self, agent_id: str) -> Optional[Task]:
        """Get pending task assigned to agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        return self.db.query(Task).filter(
            Task.agent_id == agent.id,
            Task.status.in_([TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value])
        ).first()
    
    def report_task_completion(
        self,
        agent_id: str,
        task_id: str,
        token_used: int,
        result_summary: str,
        status: str,
    ) -> dict:
        """Process task completion report from agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found")
        
        if task.agent_id != agent.id:
            raise ValueError("Task not assigned to this agent")
        
        # Calculate cost (1 OC币 = 100 tokens for MVP)
        cost = token_used / 100.0
        
        # Check budget
        if cost > agent.remaining_budget:
            # Budget exceeded - fuse the task
            task.status = TaskStatus.FUSED.value
            self.db.commit()
            return {
                "success": False,
                "fused": True,
                "message": f"Budget exceeded. Task cost {cost:.2f} OC币, remaining {agent.remaining_budget:.2f} OC币",
            }
        
        # Update task
        task.actual_cost = cost
        task.result_summary = result_summary
        task.status = TaskStatus.COMPLETED.value if status == "completed" else TaskStatus.FAILED.value
        task.completed_at = __import__('datetime').datetime.utcnow()
        
        # Update agent budget
        agent.used_budget += cost
        agent.completed_tasks += 1
        agent.status = AgentStatus.IDLE.value
        agent.current_task_id = None
        
        # Log transaction
        transaction = BudgetTransaction(
            id=str(uuid.uuid4())[:8],
            agent_id=agent.id,
            task_id=task.id,
            transaction_type=TransactionType.TASK_CONSUMPTION.value,
            amount=-cost,
            description=f"Task '{task.title}' consumption",
        )
        self.db.add(transaction)
        
        self.db.commit()
        
        # Create notification
        from src.services.notification_service import NotificationService
        notification_service = NotificationService(self.db)
        
        if task.status == TaskStatus.COMPLETED.value:
            notification_service.notify_task_completed(
                task_id=task.id,
                task_title=task.title,
                agent_name=agent.name
            )
        else:
            notification_service.notify_task_failed(
                task_id=task.id,
                task_title=task.title,
                agent_name=agent.name,
                reason=result_summary
            )
        
        return {
            "success": True,
            "fused": False,
            "cost": cost,
            "remaining_budget": agent.remaining_budget,
            "message": f"Task completed. Consumed {cost:.2f} OC币.",
        }
