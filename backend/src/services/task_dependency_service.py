"""
Task Dependency Service for v0.4.0

管理工作流中的任务依赖关系，实现任务完成后的自动触发
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Task, TaskDependency, TaskDependencyStatus, TaskStatus
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskDependencyService:
    """Service for managing task dependencies."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_dependency(
        self,
        upstream_task_id: str,
        downstream_task_template: Dict,
        trigger_condition: str = "completed",
        delay_minutes: int = 0,
    ) -> TaskDependency:
        """
        Create a task dependency.
        
        Args:
            upstream_task_id: 上游任务ID（完成后触发）
            downstream_task_template: 下游任务模板配置
            trigger_condition: 触发条件 (completed/failed/any)
            delay_minutes: 延迟触发分钟数
        
        Returns:
            Created dependency
        """
        # Verify upstream task exists
        upstream = self.db.query(Task).filter(Task.id == upstream_task_id).first()
        if not upstream:
            raise ValueError(f"Upstream task '{upstream_task_id}' not found")
        
        # Validate trigger condition
        valid_conditions = ["completed", "failed", "any"]
        if trigger_condition not in valid_conditions:
            raise ValueError(f"Invalid trigger_condition. Must be one of: {valid_conditions}")
        
        dependency = TaskDependency(
            id=str(uuid.uuid4())[:8],
            upstream_task_id=upstream_task_id,
            downstream_task_id=None,  # Will be set when triggered
            downstream_task_template=json.dumps(downstream_task_template),
            trigger_condition=trigger_condition,
            delay_minutes=delay_minutes,
            status=TaskDependencyStatus.ACTIVE.value,
        )
        
        self.db.add(dependency)
        self.db.commit()
        self.db.refresh(dependency)
        
        logger.info(
            "dependency_created",
            dependency_id=dependency.id,
            upstream_task_id=upstream_task_id,
            trigger_condition=trigger_condition,
        )
        
        return dependency
    
    def check_and_trigger_dependencies(
        self,
        task_id: str,
        task_status: str,
    ) -> List[Task]:
        """
        Check and trigger dependencies for a completed task.
        
        Args:
            task_id: Completed task ID
            task_status: Task completion status (completed/failed)
        
        Returns:
            List of triggered downstream tasks
        """
        triggered_tasks = []
        
        # Find all active dependencies for this task
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.upstream_task_id == task_id,
            TaskDependency.status == TaskDependencyStatus.ACTIVE.value,
        ).all()
        
        for dep in dependencies:
            # Check if trigger condition is met
            if not self._should_trigger(dep, task_status):
                continue
            
            try:
                # Trigger downstream task
                task = self._trigger_downstream_task(dep)
                if task:
                    triggered_tasks.append(task)
                    
                    # Update dependency status
                    dep.status = TaskDependencyStatus.TRIGGERED.value
                    dep.triggered_at = datetime.utcnow()
                    dep.downstream_task_id = task.id
                    
                    self.db.commit()
                    
                    logger.info(
                        "dependency_triggered",
                        dependency_id=dep.id,
                        upstream_task_id=task_id,
                        downstream_task_id=task.id,
                    )
            except Exception as e:
                logger.error(
                    "dependency_trigger_failed",
                    dependency_id=dep.id,
                    error=str(e),
                )
        
        return triggered_tasks
    
    def _should_trigger(self, dependency: TaskDependency, task_status: str) -> bool:
        """Check if dependency should be triggered based on task status."""
        condition = dependency.trigger_condition
        
        if condition == "completed" and task_status == TaskStatus.COMPLETED.value:
            return True
        if condition == "failed" and task_status == TaskStatus.FAILED.value:
            return True
        if condition == "any" and task_status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
            return True
        
        return False
    
    def _trigger_downstream_task(self, dependency: TaskDependency) -> Optional[Task]:
        """Create and return downstream task from template."""
        from src.services.task_service import TaskService
        
        try:
            template = json.loads(dependency.downstream_task_template or "{}")
        except json.JSONDecodeError:
            logger.error("Invalid downstream task template", dependency_id=dependency.id)
            return None
        
        # Handle delay
        if dependency.delay_minutes > 0:
            scheduled_time = datetime.utcnow() + timedelta(minutes=dependency.delay_minutes)
            logger.info(
                "task_scheduled_with_delay",
                dependency_id=dependency.id,
                delay_minutes=dependency.delay_minutes,
                scheduled_time=scheduled_time.isoformat(),
            )
            # TODO: Implement scheduled task execution (e.g., using cron)
        
        # Create downstream task
        task_service = TaskService(self.db)
        task = task_service.create_task(
            title=template.get("title", "Auto-generated task"),
            description=template.get("description", ""),
            priority=template.get("priority", "normal"),
            estimated_cost=template.get("estimated_cost", 0.0),
            agent_id=template.get("agent_id"),
        )
        
        return task
    
    def get_dependencies(
        self,
        task_id: str = None,
        upstream_only: bool = False,
        downstream_only: bool = False,
        status: str = None,
    ) -> List[TaskDependency]:
        """
        Get dependencies with optional filtering.
        
        Args:
            task_id: Filter by task ID
            upstream_only: Only get upstream dependencies (this task depends on others)
            downstream_only: Only get downstream dependencies (others depend on this task)
            status: Filter by status
        
        Returns:
            List of dependencies
        """
        query = self.db.query(TaskDependency)
        
        if task_id:
            if upstream_only:
                query = query.filter(TaskDependency.downstream_task_id == task_id)
            elif downstream_only:
                query = query.filter(TaskDependency.upstream_task_id == task_id)
            else:
                query = query.filter(
                    (TaskDependency.upstream_task_id == task_id) |
                    (TaskDependency.downstream_task_id == task_id)
                )
        
        if status:
            query = query.filter(TaskDependency.status == status)
        
        return query.order_by(TaskDependency.created_at.desc()).all()
    
    def get_dependency(self, dependency_id: str) -> Optional[TaskDependency]:
        """Get a single dependency by ID."""
        return self.db.query(TaskDependency).filter(TaskDependency.id == dependency_id).first()
    
    def cancel_dependency(self, dependency_id: str) -> TaskDependency:
        """
        Cancel an active dependency.
        
        Args:
            dependency_id: Dependency ID to cancel
        
        Returns:
            Updated dependency
        """
        dependency = self.get_dependency(dependency_id)
        if not dependency:
            raise ValueError(f"Dependency '{dependency_id}' not found")
        
        if dependency.status != TaskDependencyStatus.ACTIVE.value:
            raise ValueError(f"Cannot cancel dependency with status '{dependency.status}'")
        
        dependency.status = TaskDependencyStatus.CANCELLED.value
        self.db.commit()
        self.db.refresh(dependency)
        
        logger.info("dependency_cancelled", dependency_id=dependency_id)
        
        return dependency
    
    def delete_dependency(self, dependency_id: str):
        """Delete a dependency."""
        dependency = self.get_dependency(dependency_id)
        if not dependency:
            raise ValueError(f"Dependency '{dependency_id}' not found")
        
        self.db.delete(dependency)
        self.db.commit()
        
        logger.info("dependency_deleted", dependency_id=dependency_id)
    
    def get_dependency_chain(self, task_id: str, direction: str = "downstream") -> List[Dict]:
        """
        Get the full dependency chain for a task.
        
        Args:
            task_id: Starting task ID
            direction: "downstream" (what this task triggers) or "upstream" (what triggers this task)
        
        Returns:
            List of tasks in the chain
        """
        chain = []
        visited = set()
        
        def traverse(current_task_id: str, depth: int = 0):
            if current_task_id in visited or depth > 10:  # Prevent infinite loops
                return
            visited.add(current_task_id)
            
            task = self.db.query(Task).filter(Task.id == current_task_id).first()
            if not task:
                return
            
            chain.append({
                "task_id": task.id,
                "title": task.title,
                "status": task.status,
                "depth": depth,
            })
            
            # Find next tasks in chain
            if direction == "downstream":
                deps = self.db.query(TaskDependency).filter(
                    TaskDependency.upstream_task_id == current_task_id,
                    TaskDependency.status == TaskDependencyStatus.TRIGGERED.value,
                ).all()
                for dep in deps:
                    if dep.downstream_task_id:
                        traverse(dep.downstream_task_id, depth + 1)
            else:  # upstream
                deps = self.db.query(TaskDependency).filter(
                    TaskDependency.downstream_task_id == current_task_id,
                    TaskDependency.status == TaskDependencyStatus.TRIGGERED.value,
                ).all()
                for dep in deps:
                    traverse(dep.upstream_task_id, depth + 1)
        
        traverse(task_id)
        return chain
    
    def get_workflow_status(self, root_task_id: str) -> Dict:
        """
        Get the status of a workflow starting from a root task.
        
        Args:
            root_task_id: Root task ID
        
        Returns:
            Workflow status summary
        """
        chain = self.get_dependency_chain(root_task_id, direction="downstream")
        
        total = len(chain)
        completed = sum(1 for t in chain if t["status"] == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in chain if t["status"] == TaskStatus.FAILED.value)
        in_progress = sum(1 for t in chain if t["status"] == TaskStatus.IN_PROGRESS.value)
        pending = total - completed - failed - in_progress
        
        return {
            "root_task_id": root_task_id,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "progress_percentage": (completed / total * 100) if total > 0 else 0,
            "is_complete": completed == total and total > 0,
            "has_failures": failed > 0,
            "chain": chain,
        }
