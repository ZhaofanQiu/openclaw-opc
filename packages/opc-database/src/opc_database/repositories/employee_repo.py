"""
opc-database: 员工仓库

提供员工相关的数据访问操作

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#EmployeeRepository
"""

from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.employee import AgentStatus, Employee, PositionLevel
from .base import BaseRepository


class EmployeeRepository(BaseRepository[Employee]):
    """
    员工数据仓库
    
    封装所有员工相关的数据库操作
    
    使用示例:
        async with get_session() as session:
            repo = EmployeeRepository(session)
            employee = await repo.get_by_id("emp_xxx")
            employees = await repo.get_available_for_task(estimated_cost=100.0)
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Employee)
    
    async def get_by_openclaw_id(self, openclaw_id: str) -> Optional[Employee]:
        """
        根据OpenClaw Agent ID获取员工
        
        Args:
            openclaw_id: OpenClaw Agent ID
            
        Returns:
            员工实例或None
        """
        result = await self.session.execute(
            select(Employee).where(Employee.openclaw_agent_id == openclaw_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_status(self, status: AgentStatus) -> List[Employee]:
        """
        根据状态获取员工列表
        
        Args:
            status: 员工状态
            
        Returns:
            员工列表
        """
        result = await self.session.execute(
            select(Employee).where(Employee.status == status.value)
        )
        return list(result.scalars().all())
    
    async def get_available_for_task(
        self, 
        estimated_cost: float = 0.0,
        limit: int = 10
    ) -> List[Employee]:
        """
        获取可接受任务的员工列表
        
        条件：
        - 状态不是 offline
        - 剩余预算 >= 预估成本
        
        Args:
            estimated_cost: 预估任务成本
            limit: 返回数量限制
            
        Returns:
            可用员工列表
        """
        result = await self.session.execute(
            select(Employee)
            .where(Employee.status != AgentStatus.OFFLINE.value)
            .where((Employee.monthly_budget - Employee.used_budget) >= estimated_cost)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_budget(
        self, 
        employee_id: str, 
        amount: float,
        operation: str = "add"
    ) -> Optional[Employee]:
        """
        更新员工预算
        
        Args:
            employee_id: 员工ID
            amount: 变动金额
            operation: "add" 增加预算, "use" 使用预算, "set" 设置预算
            
        Returns:
            更新后的员工或None
        """
        employee = await self.get_by_id(employee_id)
        if not employee:
            return None
        
        if operation == "add":
            employee.monthly_budget += amount
        elif operation == "use":
            employee.used_budget += amount
        elif operation == "set":
            employee.monthly_budget = amount
        
        await self.session.flush()
        return employee
    
    async def update_status(
        self,
        employee_id: str,
        status: AgentStatus,
        current_task_id: Optional[str] = None
    ) -> Optional[Employee]:
        """
        更新员工状态
        
        Args:
            employee_id: 员工ID
            status: 新状态
            current_task_id: 当前任务ID（可选）
            
        Returns:
            更新后的员工或None
        """
        employee = await self.get_by_id(employee_id)
        if not employee:
            return None
        
        employee.status = status.value
        if current_task_id is not None:
            employee.current_task_id = current_task_id
        
        await self.session.flush()
        return employee
    
    async def bind_openclaw_agent(
        self,
        employee_id: str,
        openclaw_agent_id: str
    ) -> Optional[Employee]:
        """
        绑定OpenClaw Agent
        
        Args:
            employee_id: 员工ID
            openclaw_agent_id: OpenClaw Agent ID
            
        Returns:
            更新后的员工或None
        """
        employee = await self.get_by_id(employee_id)
        if not employee:
            return None
        
        employee.openclaw_agent_id = openclaw_agent_id
        employee.is_bound = "true"
        
        await self.session.flush()
        return employee
    
    async def increment_completed_tasks(self, employee_id: str) -> Optional[Employee]:
        """
        增加已完成任务计数
        
        Args:
            employee_id: 员工ID
            
        Returns:
            更新后的员工或None
        """
        employee = await self.get_by_id(employee_id)
        if not employee:
            return None
        
        employee.completed_tasks += 1
        await self.session.flush()
        return employee
    
    async def get_budget_stats(self) -> dict:
        """
        获取预算统计信息
        
        Returns:
            统计字典
        """
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.sum(Employee.monthly_budget).label("total_budget"),
                func.sum(Employee.used_budget).label("total_used"),
                func.avg(Employee.monthly_budget - Employee.used_budget).label("avg_remaining"),
            )
        )
        row = result.one()
        
        return {
            "total_employees": row.total or 0,
            "total_budget": float(row.total_budget or 0),
            "total_used": float(row.total_used or 0),
            "avg_remaining": float(row.avg_remaining or 0),
        }
