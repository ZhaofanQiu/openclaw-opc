"""
Task Dependency Service for v0.4.0

管理任务间的依赖关系，实现工作流自动化
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Task, TaskStatus, TaskDependency, TaskDependencyStatus, SubTask, SubTaskStatus
from src.services.task_service import TaskService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskDependencyService:
    """Service for managing task dependencies."""
    
    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
    
    def create_dependency(
        self,
        upstream_task_id: str,
        downstream_task_id: str = None,
        downstream_task_template: Dict = None,
        trigger_condition: str = "completed",
        delay_minutes: int = 0,
    ) -> TaskDependency:
        """
        Create a dependency between two tasks.
        
        Args:
            upstream_task_id: Task that triggers the dependency
            downstream_task_id: Task to be triggered (optional if using template)
            downstream_task_template: Template for creating downstream task
            trigger_condition: completed/failed/any
            delay_minutes: Delay before triggering
        
        Returns:
            Created dependency
        """
        # Verify upstream task exists
        upstream = self.db.query(Task).filter(Task.id == upstream_task_id).first()
        if not upstream:
            raise ValueError(f"Upstream task '{upstream_task_id}' not found")
        
        # Verify downstream task if provided
        if downstream_task_id:
            downstream = self.db.query(Task).filter(Task.id == downstream_task_id).first()
            if not downstream:
                raise ValueError(f"Downstream task '{downstream_task_id}' not found")
        
        dependency = TaskDependency(
            id=str(uuid.uuid4())[:8],
            upstream_task_id=upstream_task_id,
            downstream_task_id=downstream_task_id,
            downstream_task_template=json.dumps(downstream_task_template or {}),
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
            downstream_task_id=downstream_task_id,
            trigger_condition=trigger_condition,
        )
        
        return dependency
    
    def check_and_trigger_dependencies(self, task_id: str, task_status: str):
        """
        Check if a task completion should trigger downstream tasks.
        
        Args:
            task_id: Completed task ID
            task_status: Status of the completed task (completed/failed)
        """
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.upstream_task_id == task_id,
            TaskDependency.status == TaskDependencyStatus.ACTIVE.value,
        ).all()
        
        for dep in dependencies:
            # Check trigger condition
            if not self._should_trigger(dep, task_status):
                continue
            
            try:
                self._trigger_dependency(dep)
            except Exception as e:
                logger.error(
                    "failed_to_trigger_dependency",
                    dependency_id=dep.id,
                    error=str(e),
                )
    
    def _should_trigger(self, dependency: TaskDependency, task_status: str) -> bool:
        """Check if dependency should be triggered based on condition."""
        condition = dependency.trigger_condition
        
        if condition == "completed" and task_status == TaskStatus.COMPLETED.value:
            return True
        if condition == "failed" and task_status == TaskStatus.FAILED.value:
            return True
        if condition == "any" and task_status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
            return True
        
        return False
    
    def _trigger_dependency(self, dependency: TaskDependency):
        """Trigger a dependency."""
        # Handle delay
        if dependency.delay_minutes > 0:
            # For now, just log. In production, use Celery or similar
            logger.info(
                "dependency_delayed",
                dependency_id=dependency.id,
                delay_minutes=dependency.delay_minutes,
            )
            # TODO: Schedule delayed execution
        
        # If downstream task exists, activate it
        if dependency.downstream_task_id:
            downstream = self.db.query(Task).filter(
                Task.id == dependency.downstream_task_id
            ).first()
            
            if downstream and downstream.status == TaskStatus.PENDING.value:
                # Update status to ready (or similar)
                logger.info(
                    "dependency_triggered",
                    dependency_id=dependency.id,
                    downstream_task_id=downstream.id,
                )
        
        # If using template, create new task
        else:
            try:
                template = json.loads(dependency.downstream_task_template or "{}")
                if template:
                    new_task = self._create_task_from_template(template, dependency.upstream_task_id)
                    dependency.downstream_task_id = new_task.id
                    
                    logger.info(
                        "task_created_from_template",
                        dependency_id=dependency.id,
                        new_task_id=new_task.id,
                    )
            except json.JSONDecodeError:
                logger.error(
                    "invalid_task_template",
                    dependency_id=dependency.id,
                )
        
        # Update dependency status
        dependency.status = TaskDependencyStatus.TRIGGERED.value
        dependency.triggered_at = datetime.utcnow()
        self.db.commit()
    
    def _create_task_from_template(self, template: Dict, upstream_task_id: str) -> Task:
        """Create a new task from template."""
        # Get upstream task for context
        upstream = self.db.query(Task).filter(Task.id == upstream_task_id).first()
        
        title = template.get("title", "Follow-up Task")
        description = template.get("description", "")
        
        # Add context from upstream task
        if upstream:
            description = f"Triggered by task '{upstream.title}' (ID: {upstream_task_id})\n\n{description}"
        
        # Create task using task service
        from src.models import TaskPriority
        
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            estimated_cost=template.get("estimated_cost", 100),
            priority=template.get("priority", TaskPriority.NORMAL.value),
            status=TaskStatus.PENDING.value,
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def get_dependencies(
        self,
        task_id: str = None,
        status: str = None,
        as_upstream: bool = True,
    ) -> List[TaskDependency]:
        """
        Get dependencies.
        
        Args:
            task_id: Filter by task ID
            status: Filter by status
            as_upstream: If True, get where task is upstream; else where task is downstream
        
        Returns:
            List of dependencies
        """
        query = self.db.query(TaskDependency)
        
        if task_id:
            if as_upstream:
                query = query.filter(TaskDependency.upstream_task_id == task_id)
            else:
                query = query.filter(TaskDependency.downstream_task_id == task_id)
        
        if status:
            query = query.filter(TaskDependency.status == status)
        
        return query.all()
    
    def get_dependency(self, dependency_id: str) -> Optional[TaskDependency]:
        """Get a single dependency by ID."""
        return self.db.query(TaskDependency).filter(TaskDependency.id == dependency_id).first()
    
    def cancel_dependency(self, dependency_id: str):
        """Cancel a dependency."""
        dep = self.get_dependency(dependency_id)
        if not dep:
            raise ValueError(f"Dependency '{dependency_id}' not found")
        
        dep.status = TaskDependencyStatus.CANCELLED.value
        self.db.commit()
        
        logger.info("dependency_cancelled", dependency_id=dependency_id)
    
    def delete_dependency(self, dependency_id: str):
        """Delete a dependency."""
        dep = self.get_dependency(dependency_id)
        if not dep:
            raise ValueError(f"Dependency '{dependency_id}' not found")
        
        self.db.delete(dep)
        self.db.commit()
        
        logger.info("dependency_deleted", dependency_id=dependency_id)
    
    def get_dependency_chain(self, task_id: str) -> Dict:
        """
        Get the full dependency chain for a task.
        
        Returns:
            Dict with upstream and downstream chains
        """
        upstream_deps = self.get_dependencies(task_id, as_upstream=False)
        downstream_deps = self.get_dependencies(task_id, as_upstream=True)
        
        return {
            "task_id": task_id,
            "upstream": [
                {
                    "dependency_id": d.id,
                    "task_id": d.upstream_task_id,
                    "status": d.status,
                }
                for d in upstream_deps
            ],
            "downstream": [
                {
                    "dependency_id": d.id,
                    "task_id": d.downstream_task_id,
                    "status": d.status,
                }
                for d in downstream_deps
            ],
        }
    
    def build_workflow(self, start_task_id: str) -> List[Dict]:
        """
        Build a workflow starting from a task.
        
        Returns:
            List of tasks in execution order
        """
        workflow = []
        visited = set()
        
        def visit(task_id: str):
            if task_id in visited:
                return
            visited.add(task_id)
            
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return
            
            # Visit upstream dependencies first
            upstream_deps = self.get_dependencies(task_id, as_upstream=False)
            for dep in upstream_deps:
                if dep.upstream_task_id:
                    visit(dep.upstream_task_id)
            
            workflow.append({
                "task_id": task.id,
                "title": task.title,
                "status": task.status,
            })
            
            # Visit downstream
            downstream_deps = self.get_dependencies(task_id, as_upstream=True)
            for dep in downstream_deps:
                if dep.downstream_task_id:
                    visit(dep.downstream_task_id)
        
        visit(start_task_id)
        return workflow
