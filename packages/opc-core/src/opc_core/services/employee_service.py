"""
opc-core: 员工服务

员工业务逻辑服务

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from opc_database.repositories import EmployeeRepository
from opc_database.models import Employee, AgentStatus


class EmployeeService:
    """
    员工业务服务
    
    封装员工相关的业务逻辑
    """
    
    def __init__(self, repo: EmployeeRepository):
        self.repo = repo
    
    async def can_accept_task(self, employee_id: str, estimated_cost: float) -> bool:
        """
        检查员工是否可以接受任务
        
        Args:
            employee_id: 员工ID
            estimated_cost: 预估成本
            
        Returns:
            是否可以接受
        """
        employee = await self.repo.get_by_id(employee_id)
        if not employee:
            return False
        
        return employee.can_accept_task(estimated_cost)
    
    async def get_available_employees(self, estimated_cost: float = 0.0) -> list[Employee]:
        """
        获取可接受任务的员工列表
        
        Args:
            estimated_cost: 预估成本
            
        Returns:
            可用员工列表
        """
        return await self.repo.get_available_for_task(estimated_cost)
    
    async def release_from_task(self, employee_id: str):
        """
        释放员工从当前任务
        
        Args:
            employee_id: 员工ID
        """
        await self.repo.update_status(employee_id, AgentStatus.IDLE)
