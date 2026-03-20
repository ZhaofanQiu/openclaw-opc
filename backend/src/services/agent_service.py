"""
Agent service layer.
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models import Agent, AgentStatus, BudgetTransaction, Task, TaskStatus, TransactionType
from src.utils.openclaw_config import read_openclaw_agents


class AgentService:
    """Agent service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_agent(
        self,
        name: str,
        agent_id: Optional[str] = None,
        emoji: str = "🧑‍💻",
        monthly_budget: float = 2000.0,
    ) -> Agent:
        """
        Create a new agent (employee).
        
        Args:
            name: Employee name
            agent_id: OpenClaw agent ID (optional, if None creates unbound employee)
            emoji: Employee emoji
            monthly_budget: Monthly budget in OC币
        
        Returns:
            Created agent
        """
        # If agent_id provided, check if already exists
        if agent_id:
            existing = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
            if existing:
                raise ValueError(f"Agent with agent_id '{agent_id}' already exists")
        
        agent = Agent(
            id=str(uuid.uuid4())[:8],
            name=name,
            agent_id=agent_id,
            is_bound="true" if agent_id else "false",
            emoji=emoji,
            monthly_budget=monthly_budget,
            used_budget=0.0,
            status=AgentStatus.IDLE.value if agent_id else "unbound",  # Unbound employees can't work
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent
    
    def bind_agent(self, employee_id: str, agent_id: str) -> Agent:
        """
        Bind an existing employee to an OpenClaw agent.
        
        Args:
            employee_id: OPC employee ID
            agent_id: OpenClaw agent ID to bind
        
        Returns:
            Updated agent
        """
        # Get employee
        employee = self.db.query(Agent).filter(Agent.id == employee_id).first()
        if not employee:
            raise ValueError(f"Employee '{employee_id}' not found")
        
        # Check if agent_id already bound to another employee
        existing = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if existing and existing.id != employee_id:
            raise ValueError(f"Agent '{agent_id}' is already bound to employee '{existing.name}'")
        
        # Update binding
        employee.agent_id = agent_id
        employee.is_bound = "true"
        if employee.status == "unbound":
            employee.status = AgentStatus.IDLE.value
        
        self.db.commit()
        self.db.refresh(employee)
        return employee
    
    def unbind_agent(self, employee_id: str, archive_agent: bool = False) -> Agent:
        """
        Unbind an employee from its OpenClaw agent.
        
        Args:
            employee_id: OPC employee ID
            archive_agent: If True, archive the OpenClaw agent config
        
        Returns:
            Updated agent
        """
        employee = self.db.query(Agent).filter(Agent.id == employee_id).first()
        if not employee:
            raise ValueError(f"Employee '{employee_id}' not found")
        
        if employee.is_bound != "true":
            raise ValueError(f"Employee '{employee_id}' is not bound to any agent")
        
        # Archive OpenClaw agent if requested
        if archive_agent and employee.agent_id:
            # TODO: Call AgentLifecycleService to archive agent config
            pass
        
        # Unbind
        old_agent_id = employee.agent_id
        employee.agent_id = None
        employee.is_bound = "false"
        employee.status = "unbound"
        
        self.db.commit()
        self.db.refresh(employee)
        return employee
    
    def get_available_openclaw_agents(self) -> List[dict]:
        """
        Get list of available OpenClaw agents that are not yet bound.
        
        Returns:
            List of available agents from openclaw.json that aren't bound
        """
        # Get all OpenClaw agents from config
        all_agents = read_openclaw_agents()
        
        # Get already bound agent_ids
        bound_ids = {
            agent.agent_id for agent in self.db.query(Agent).all()
            if agent.agent_id and agent.is_bound == "true"
        }
        
        # Filter out bound agents
        available = [
            {
                "id": agent["id"],
                "name": agent["name"],
                "model": agent.get("model", "default"),
            }
            for agent in all_agents
            if agent["id"] not in bound_ids
        ]
        
        return available
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by agent_id (OpenClaw agent ID)."""
        return self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    def get_agent_by_id(self, id: str) -> Optional[Agent]:
        """Get agent by internal ID."""
        return self.db.query(Agent).filter(Agent.id == id).first()
    
    def list_agents(self, include_unbound: bool = True) -> List[Agent]:
        """
        List all agents.
        
        Args:
            include_unbound: If False, only return bound agents
        """
        query = self.db.query(Agent)
        if not include_unbound:
            query = query.filter(Agent.is_bound == "true")
        return query.all()
    
    def list_working_agents(self) -> List[Agent]:
        """List only agents that can work (bound agents)."""
        return self.db.query(Agent).filter(Agent.is_bound == "true").all()
    
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
        
        if agent.is_bound != "true":
            raise ValueError(f"Agent '{agent_id}' is not bound and cannot report tasks")
        
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
