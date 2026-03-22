"""
Sub-task Service for v0.4.0

管理子任务的创建、分配、依赖处理和状态同步
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import SubTask, SubTaskStatus, Task, TaskStatus, Agent
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SubTaskService:
    """Service for managing sub-tasks."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_sub_task(
        self,
        parent_task_id: str,
        title: str,
        description: str = "",
        estimated_cost: float = 0.0,
        sequence_order: int = 0,
        depends_on: List[str] = None,
        is_critical: bool = False,
    ) -> SubTask:
        """
        Create a new sub-task for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            title: Sub-task title
            description: Sub-task description
            estimated_cost: Estimated budget cost
            sequence_order: Execution order (lower = earlier)
            depends_on: List of sub-task IDs this task depends on
            is_critical: Whether this is on the critical path
        
        Returns:
            Created sub-task
        """
        # Verify parent task exists
        parent = self.db.query(Task).filter(Task.id == parent_task_id).first()
        if not parent:
            raise ValueError(f"Parent task '{parent_task_id}' not found")
        
        sub_task = SubTask(
            id=str(uuid.uuid4())[:8],
            parent_task_id=parent_task_id,
            title=title,
            description=description,
            estimated_cost=estimated_cost,
            sequence_order=sequence_order,
            depends_on=json.dumps(depends_on or []),
            is_critical="true" if is_critical else "false",
            status=SubTaskStatus.PENDING.value,
        )
        
        self.db.add(sub_task)
        
        # Update parent task
        parent.is_parent_task = "true"
        parent.sub_task_count = (parent.sub_task_count or 0) + 1
        
        self.db.commit()
        self.db.refresh(sub_task)
        
        logger.info(
            "sub_task_created",
            sub_task_id=sub_task.id,
            parent_task_id=parent_task_id,
            title=title,
        )
        
        return sub_task
    
    def split_task(
        self,
        task_id: str,
        sub_tasks_config: List[Dict],
    ) -> List[SubTask]:
        """
        Split a task into multiple sub-tasks.
        
        Args:
            task_id: Task to split
            sub_tasks_config: List of sub-task configs
                Each config: {title, description, estimated_cost, sequence_order}
        
        Returns:
            List of created sub-tasks
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task '{task_id}' not found")
        
        if task.status not in [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value]:
            raise ValueError(f"Cannot split task with status '{task.status}'")
        
        created_sub_tasks = []
        
        for i, config in enumerate(sub_tasks_config):
            sub_task = self.create_sub_task(
                parent_task_id=task_id,
                title=config["title"],
                description=config.get("description", ""),
                estimated_cost=config.get("estimated_cost", 0.0),
                sequence_order=config.get("sequence_order", i),
            )
            created_sub_tasks.append(sub_task)
        
        # Update parent task status
        task.status = TaskStatus.SPLIT.value
        
        self.db.commit()
        
        logger.info(
            "task_split",
            task_id=task_id,
            sub_task_count=len(created_sub_tasks),
        )
        
        return created_sub_tasks
    
    def assign_sub_task(
        self,
        sub_task_id: str,
        agent_id: str,
    ) -> SubTask:
        """
        Assign a sub-task to an agent.
        
        Args:
            sub_task_id: Sub-task ID
            agent_id: Agent ID to assign to
        
        Returns:
            Updated sub-task
        """
        sub_task = self.db.query(SubTask).filter(SubTask.id == sub_task_id).first()
        if not sub_task:
            raise ValueError(f"Sub-task '{sub_task_id}' not found")
        
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # Check dependencies
        if not self._check_dependencies_met(sub_task):
            raise ValueError("Dependencies not met for this sub-task")
        
        sub_task.agent_id = agent_id
        sub_task.status = SubTaskStatus.ASSIGNED.value
        sub_task.assigned_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(sub_task)
        
        logger.info(
            "sub_task_assigned",
            sub_task_id=sub_task_id,
            agent_id=agent_id,
            agent_name=agent.name,
        )
        
        return sub_task
    
    def _check_dependencies_met(self, sub_task: SubTask) -> bool:
        """Check if all dependencies for a sub-task are completed."""
        try:
            depends_on = json.loads(sub_task.depends_on or "[]")
        except json.JSONDecodeError:
            return True
        
        if not depends_on:
            return True
        
        for dep_id in depends_on:
            dep_task = self.db.query(SubTask).filter(SubTask.id == dep_id).first()
            if not dep_task:
                logger.warning(f"Dependency '{dep_id}' not found for sub-task '{sub_task.id}'")
                return False
            if dep_task.status != SubTaskStatus.COMPLETED.value:
                return False
        
        return True
    
    def update_sub_task_status(
        self,
        sub_task_id: str,
        status: str,
        result_summary: str = "",
        actual_cost: float = None,
    ) -> SubTask:
        """
        Update sub-task status.
        
        Args:
            sub_task_id: Sub-task ID
            status: New status
            result_summary: Task result description
            actual_cost: Actual cost (if completed)
        
        Returns:
            Updated sub-task
        """
        sub_task = self.db.query(SubTask).filter(SubTask.id == sub_task_id).first()
        if not sub_task:
            raise ValueError(f"Sub-task '{sub_task_id}' not found")
        
        old_status = sub_task.status
        sub_task.status = status
        
        if status == SubTaskStatus.IN_PROGRESS.value:
            sub_task.started_at = datetime.utcnow()
        
        if status == SubTaskStatus.COMPLETED.value:
            sub_task.completed_at = datetime.utcnow()
            sub_task.result_summary = result_summary
            if actual_cost is not None:
                sub_task.actual_cost = actual_cost
            
            # Update parent task progress
            self._update_parent_progress(sub_task.parent_task_id)
        
        if status == SubTaskStatus.FAILED.value:
            sub_task.result_summary = result_summary
        
        self.db.commit()
        self.db.refresh(sub_task)
        
        logger.info(
            "sub_task_status_updated",
            sub_task_id=sub_task_id,
            old_status=old_status,
            new_status=status,
        )
        
        # Check if we can unblock dependent tasks
        if status == SubTaskStatus.COMPLETED.value:
            self._check_and_unblock_dependent_tasks(sub_task_id)
        
        return sub_task
    
    def _update_parent_progress(self, parent_task_id: str):
        """Update parent task completion progress."""
        parent = self.db.query(Task).filter(Task.id == parent_task_id).first()
        if not parent:
            return
        
        total = self.db.query(SubTask).filter(
            SubTask.parent_task_id == parent_task_id
        ).count()
        
        completed = self.db.query(SubTask).filter(
            SubTask.parent_task_id == parent_task_id,
            SubTask.status == SubTaskStatus.COMPLETED.value
        ).count()
        
        parent.sub_task_count = total
        parent.completed_sub_task_count = completed
        
        # If all sub-tasks completed, mark parent as completed
        if total > 0 and completed == total:
            parent.status = TaskStatus.COMPLETED.value
            parent.completed_at = datetime.utcnow()
            
            # Calculate total actual cost from sub-tasks
            total_cost = self.db.query(SubTask).filter(
                SubTask.parent_task_id == parent_task_id
            ).with_entities(SubTask.actual_cost).all()
            
            parent.actual_cost = sum(cost[0] for cost in total_cost if cost[0])
        
        self.db.commit()
        
        logger.info(
            "parent_task_progress_updated",
            task_id=parent_task_id,
            completed=completed,
            total=total,
        )
    
    def _check_and_unblock_dependent_tasks(self, completed_sub_task_id: str):
        """Check and unblock tasks that depend on the completed task."""
        dependent_tasks = self.db.query(SubTask).filter(
            SubTask.depends_on.like(f'%"{completed_sub_task_id}"%')
        ).all()
        
        for task in dependent_tasks:
            if task.status == SubTaskStatus.BLOCKED.value:
                if self._check_dependencies_met(task):
                    task.status = SubTaskStatus.PENDING.value
                    logger.info(
                        "sub_task_unblocked",
                        sub_task_id=task.id,
                        unblocked_by=completed_sub_task_id,
                    )
        
        self.db.commit()
    
    def get_sub_tasks(
        self,
        parent_task_id: str = None,
        agent_id: str = None,
        status: str = None,
    ) -> List[SubTask]:
        """
        Get sub-tasks with optional filtering.
        
        Args:
            parent_task_id: Filter by parent task
            agent_id: Filter by assigned agent
            status: Filter by status
        
        Returns:
            List of sub-tasks
        """
        query = self.db.query(SubTask)
        
        if parent_task_id:
            query = query.filter(SubTask.parent_task_id == parent_task_id)
        
        if agent_id:
            query = query.filter(SubTask.agent_id == agent_id)
        
        if status:
            query = query.filter(SubTask.status == status)
        
        return query.order_by(SubTask.sequence_order).all()
    
    def get_sub_task(self, sub_task_id: str) -> Optional[SubTask]:
        """Get a single sub-task by ID."""
        return self.db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    
    def delete_sub_task(self, sub_task_id: str):
        """Delete a sub-task."""
        sub_task = self.db.query(SubTask).filter(SubTask.id == sub_task_id).first()
        if not sub_task:
            raise ValueError(f"Sub-task '{sub_task_id}' not found")
        
        parent_id = sub_task.parent_task_id
        
        self.db.delete(sub_task)
        self.db.commit()
        
        # Update parent progress
        self._update_parent_progress(parent_id)
        
        logger.info("sub_task_deleted", sub_task_id=sub_task_id)
    
    def get_next_executable_sub_task(self, parent_task_id: str) -> Optional[SubTask]:
        """
        Get the next sub-task that can be executed (dependencies met).
        
        Args:
            parent_task_id: Parent task ID
        
        Returns:
            Next executable sub-task or None
        """
        sub_tasks = self.db.query(SubTask).filter(
            SubTask.parent_task_id == parent_task_id,
            SubTask.status.in_([SubTaskStatus.PENDING.value, SubTaskStatus.BLOCKED.value])
        ).order_by(SubTask.sequence_order).all()
        
        for sub_task in sub_tasks:
            if self._check_dependencies_met(sub_task):
                return sub_task
        
        return None
    
    def get_sub_task_stats(self, parent_task_id: str) -> Dict:
        """
        Get sub-task statistics for a parent task.
        
        Returns:
            Stats dict with counts by status
        """
        sub_tasks = self.db.query(SubTask).filter(
            SubTask.parent_task_id == parent_task_id
        ).all()
        
        stats = {
            "total": len(sub_tasks),
            "pending": 0,
            "assigned": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
            "progress_percentage": 0.0,
        }
        
        for st in sub_tasks:
            if st.status in stats:
                stats[st.status] += 1
        
        if stats["total"] > 0:
            stats["progress_percentage"] = (stats["completed"] / stats["total"]) * 100
        
        return stats
