"""
Partner Auto-Assignment Service

This module handles automatic task assignment by Partner Agent.
"""

from typing import Optional

from sqlalchemy.orm import Session

from src.models import Agent, Task, TaskStatus
from src.services.task_service import TaskService


class AssignmentStrategy:
    """Task assignment strategies."""
    
    @staticmethod
    def by_budget(agent: Agent, task) -> float:
        """
        Score agent based on remaining budget.
        Higher score = better candidate.
        """
        if agent.remaining_budget < task.estimated_cost:
            return 0.0  # Can't afford
        
        # Score based on budget ratio (higher remaining = better)
        budget_ratio = agent.remaining_budget / agent.monthly_budget
        return budget_ratio
    
    @staticmethod
    def by_workload(agent: Agent, db: Session = None) -> float:
        """
        Score agent based on current workload.
        Lower workload = better candidate.
        Score ranges from 0.0 (max workload) to 1.0 (no workload)
        """
        if db:
            # Count active tasks for this agent
            active_tasks = db.query(Task).filter(
                Task.agent_id == agent.id,
                Task.status.in_(["assigned", "in_progress"])
            ).count()
            
            # Max concurrent tasks assumption: 3
            max_tasks = 3
            workload_ratio = min(active_tasks / max_tasks, 1.0)
            return 1.0 - workload_ratio  # Inverse: less workload = higher score
        
        return 1.0  # Default: assume no workload if db not available
    
    @staticmethod
    def combined(agent: Agent, task, db: Session = None) -> float:
        """
        Combined scoring strategy.
        Weights: 40% budget, 30% workload, 30% skill match
        """
        # Budget score (40%)
        budget_score = AssignmentStrategy.by_budget(agent, task)
        if budget_score == 0.0:
            return 0.0  # Can't afford the task
        
        # Workload score (30%) - inverse of current workload
        workload_score = AssignmentStrategy.by_workload(agent, db)
        
        # Skill match score (30%)
        skill_score = 0.5  # Default neutral score if no skill data
        if db:
            try:
                skill_score = AssignmentStrategy.by_skill(agent, task, db)
            except Exception:
                skill_score = 0.5  # Fallback to neutral if skill calc fails
        
        # Weighted combination
        return budget_score * 0.4 + workload_score * 0.3 + skill_score * 0.3
    
    @staticmethod
    def by_skill(agent: Agent, task, db: Session) -> float:
        """
        Score agent based on skill match with task requirements.
        Uses SkillService to calculate match score.
        """
        from src.services.skill_service import SkillService
        
        skill_service = SkillService(db)
        match_result = skill_service.calculate_agent_task_match_score(agent.id, task.id)
        
        # Return match score (0-100) normalized to 0-1
        return match_result["score"] / 100.0


class PartnerService:
    """
    Service for Partner Agent operations.
    
    Handles automatic task assignment and coordination.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
    
    def find_best_agent(self, task_id: str, strategy: str = "budget") -> Optional[Agent]:
        """
        Find the best agent to assign a task.
        
        Args:
            task_id: Task ID to assign
            strategy: Scoring strategy ("budget", "workload", "combined", "skill")
        
        Returns:
            Best agent or None if no suitable agent found
        """
        # Get task
        task = self.task_service.get_task(task_id)
        if not task:
            return None
        
        if task.status != TaskStatus.PENDING.value:
            return None  # Task already assigned or completed
        
        # Get all active agents (excluding Partner)
        # Status can be "idle" or "busy" (both are considered active/working)
        agents = self.db.query(Agent).filter(
            Agent.status.in_(["idle", "busy"]),
            Agent.position_level < 5  # Exclude Partner (Lv.5)
        ).all()
        
        if not agents:
            return None
        
        # Score each agent
        if strategy == "skill":
            # Special handling for skill strategy
            best_agent = None
            best_score = -1
            
            for agent in agents:
                score = AssignmentStrategy.by_skill(agent, task, self.db)
                # Also check budget constraint
                if agent.remaining_budget < task.estimated_cost:
                    score = 0.0
                if score > best_score:
                    best_score = score
                    best_agent = agent
            
            return best_agent if best_score > 0 else None
        else:
            best_agent = None
            best_score = -1
            
            for agent in agents:
                # Special handling for strategies that need db
                if strategy == "combined":
                    score = AssignmentStrategy.combined(agent, task, self.db)
                elif strategy == "workload":
                    score = AssignmentStrategy.by_workload(agent, self.db)
                else:
                    strategy_fn = getattr(AssignmentStrategy, strategy, AssignmentStrategy.by_budget)
                    score = strategy_fn(agent, task)
                
                if score > best_score:
                    best_score = score
                    best_agent = agent
            
            return best_agent if best_score > 0 else None
    
    def auto_assign(self, task_id: str, strategy: str = "budget") -> dict:
        """
        Automatically assign a task to the best agent.
        
        Args:
            task_id: Task ID to assign
            strategy: Scoring strategy
        
        Returns:
            Assignment result
        """
        # Find best agent
        best_agent = self.find_best_agent(task_id, strategy)
        
        if not best_agent:
            return {
                "success": False,
                "message": "No suitable agent found for this task",
                "reason": "insufficient_budget_or_no_employees"
            }
        
        # Assign task
        try:
            result = self.task_service.assign_task(task_id, best_agent.agent_id)
            return {
                "success": True,
                "message": f"Task assigned to {best_agent.name}",
                "task_id": task_id,
                "assigned_to": {
                    "id": best_agent.id,
                    "name": best_agent.name,
                    "agent_id": best_agent.agent_id,
                },
                "strategy": strategy
            }
        except ValueError as e:
            return {
                "success": False,
                "message": str(e),
                "reason": "assignment_failed"
            }
    
    def get_pending_tasks(self) -> list:
        """
        Get all pending tasks waiting for assignment.
        
        Returns:
            List of pending tasks
        """
        return self.task_service.list_tasks(status="pending")
    
    def assign_all_pending(self, strategy: str = "budget") -> list:
        """
        Assign all pending tasks to best available agents.
        
        Args:
            strategy: Scoring strategy
        
        Returns:
            List of assignment results
        """
        pending = self.get_pending_tasks()
        results = []
        
        for task in pending:
            result = self.auto_assign(task.id, strategy)
            results.append(result)
        
        return results
    
    def get_company_status(self) -> dict:
        """
        Get comprehensive company status for Partner.
        
        Returns:
            Company status summary
        """
        # Count agents by status
        agents = self.db.query(Agent).all()
        total_agents = len(agents)
        active_agents = sum(1 for a in agents if a.status in ["idle", "busy"])
        
        # Count tasks by status
        from src.models import Task
        tasks = self.db.query(Task).all()
        pending_count = sum(1 for t in tasks if t.status == TaskStatus.PENDING.value)
        assigned_count = sum(1 for t in tasks if t.status == TaskStatus.ASSIGNED.value)
        completed_count = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED.value)
        fused_count = sum(1 for t in tasks if t.status == TaskStatus.FUSED.value)
        
        # Calculate total budget
        total_budget = sum(a.monthly_budget for a in agents)
        total_remaining = sum(a.remaining_budget for a in agents)
        
        return {
            "agents": {
                "total": total_agents,
                "active": active_agents,
            },
            "tasks": {
                "total": len(tasks),
                "pending": pending_count,
                "assigned": assigned_count,
                "completed": completed_count,
                "fused": fused_count,
            },
            "budget": {
                "total": total_budget,
                "remaining": total_remaining,
                "usage_percentage": ((total_budget - total_remaining) / total_budget * 100) if total_budget > 0 else 0,
            },
            "ready_for_assignment": pending_count > 0 and active_agents > 0
        }
    
    def get_company_summary(self) -> dict:
        """
        Get company status summary for Partner welcome message.
        
        Returns:
            Summary with budget, tasks, alerts, and good news
        """
        from datetime import datetime, timedelta
        from src.models import Task, TaskStatus
        
        # Budget info
        agents = self.db.query(Agent).filter(Agent.position_level < 5).all()
        total_budget = sum(a.monthly_budget for a in agents)
        total_used = sum(a.used_budget for a in agents)
        total_remaining = sum(a.remaining_budget for a in agents)
        budget_pct = (total_used / total_budget * 100) if total_budget > 0 else 0
        
        # Task counts
        tasks = self.db.query(Task).all()
        pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING.value)
        assigned = sum(1 for t in tasks if t.status == TaskStatus.ASSIGNED.value)
        in_progress = sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS.value)
        completed_today = sum(1 for t in tasks 
                             if t.status == TaskStatus.COMPLETED.value 
                             and t.completed_at 
                             and t.completed_at > datetime.utcnow() - timedelta(days=1))
        
        # Overdue tasks
        overdue = sum(1 for t in tasks 
                     if t.status in [TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value]
                     and t.due_date 
                     and t.due_date < datetime.utcnow())
        
        # Generate alerts (negative things to note)
        alerts = []
        for agent in agents:
            remaining_pct = (agent.remaining_budget / agent.monthly_budget * 100) if agent.monthly_budget > 0 else 100
            if remaining_pct < 20:
                alerts.append(f"{agent.name} 预算不足20%")
        
        if overdue > 0:
            alerts.append(f"{overdue}个任务已逾期")
        
        for agent in agents:
            if agent.status == "fused":
                alerts.append(f"{agent.name} 预算熔断")
        
        # Generate good news (positive things)
        good_news = []
        if completed_today > 0:
            good_news.append(f"今天完成了{completed_today}个任务")
        
        low_budget_count = sum(1 for a in agents if a.remaining_budget < a.monthly_budget * 0.2)
        if low_budget_count == 0:
            good_news.append("所有员工预算充足")
        
        if pending == 0 and len(tasks) > 0:
            good_news.append("所有任务都已分配")
        
        return {
            "budget": {
                "total": total_budget,
                "used": total_used,
                "remaining": total_remaining,
                "used_percentage": budget_pct,
            },
            "tasks": {
                "total": len(tasks),
                "pending": pending,
                "assigned": assigned,
                "in_progress": in_progress,
                "completed_today": completed_today,
                "overdue": overdue,
            },
            "agents": {
                "total": len(agents),
                "idle": sum(1 for a in agents if a.status == "idle"),
                "busy": sum(1 for a in agents if a.status == "busy"),
            },
            "alerts": alerts,
            "good_news": good_news,
            "timestamp": datetime.utcnow().isoformat()
        }