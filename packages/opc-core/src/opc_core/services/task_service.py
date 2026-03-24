"""
opc-core: 任务服务

任务业务逻辑服务

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from opc_database.repositories import EmployeeRepository, TaskRepository
from opc_database.models import Task, TaskStatus


class TaskService:
    """
    任务业务服务
    
    封装任务相关的业务逻辑
    """
    
    def __init__(
        self,
        task_repo: TaskRepository,
        emp_repo: EmployeeRepository
    ):
        self.task_repo = task_repo
        self.emp_repo = emp_repo
    
    async def get_task_with_employee(self, task_id: str) -> tuple[Task, dict] | None:
        """
        获取任务及分配的员工信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            (Task, employee_dict) 或 None
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return None
        
        employee = None
        if task.assigned_to:
            employee = await self.emp_repo.get_by_id(task.assigned_to)
        
        return task, employee.to_dict() if employee else {}
    
    async def get_pending_tasks(self, limit: int = 100) -> list[Task]:
        """
        获取待处理任务
        
        Args:
            limit: 数量限制
            
        Returns:
            任务列表
        """
        return await self.task_repo.get_by_status(TaskStatus.PENDING, limit)
    
    async def get_employee_workload(self, employee_id: str) -> dict:
        """
        获取员工工作负载
        
        Args:
            employee_id: 员工ID
            
        Returns:
            负载统计
        """
        tasks = await self.task_repo.get_by_employee(employee_id)
        
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS.value]
        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED.value]
        
        return {
            "total": len(tasks),
            "in_progress": len(in_progress),
            "completed": len(completed),
            "total_cost": sum(t.actual_cost for t in tasks)
        }
