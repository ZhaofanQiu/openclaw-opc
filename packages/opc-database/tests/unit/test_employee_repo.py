"""
EmployeeRepository 测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

# Add tests directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))

from opc_database.models import Employee, AgentStatus, PositionLevel
from opc_database.repositories import EmployeeRepository
from tests.utils import create_test_employee


@pytest.mark.asyncio
class TestEmployeeRepository:
    """EmployeeRepository 测试类"""
    
    async def test_create_employee(self, db_session: AsyncSession):
        """测试创建员工"""
        repo = EmployeeRepository(db_session)
        
        employee = await create_test_employee(db_session)
        
        assert employee.id is not None
        assert employee.name == "测试员工"
        assert employee.status == AgentStatus.IDLE.value
        assert employee.monthly_budget == 1000.0
    
    async def test_get_by_id(self, db_session: AsyncSession):
        """测试根据ID获取员工"""
        repo = EmployeeRepository(db_session)
        
        # 创建员工
        created = await create_test_employee(db_session, name="员工A")
        
        # 查询
        found = await repo.get_by_id(created.id)
        
        assert found is not None
        assert found.id == created.id
        assert found.name == "员工A"
    
    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """测试获取不存在的员工"""
        repo = EmployeeRepository(db_session)
        
        found = await repo.get_by_id("non_existent_id")
        
        assert found is None
    
    async def test_get_by_openclaw_id(self, db_session: AsyncSession):
        """测试根据OpenClaw ID获取员工"""
        repo = EmployeeRepository(db_session)
        
        created = await create_test_employee(
            db_session, 
            openclaw_agent_id="agent_special"
        )
        
        found = await repo.get_by_openclaw_id("agent_special")
        
        assert found is not None
        assert found.id == created.id
    
    async def test_get_by_status(self, db_session: AsyncSession):
        """测试根据状态获取员工"""
        repo = EmployeeRepository(db_session)
        
        # 创建不同状态的员工
        emp1 = await create_test_employee(db_session, name="员工1")
        emp1.status = AgentStatus.IDLE.value
        await db_session.flush()
        
        # 查询
        idle_employees = await repo.get_by_status(AgentStatus.IDLE)
        
        assert len(idle_employees) >= 1
        assert all(isinstance(e, Employee) for e in idle_employees)
        assert all(e.status == AgentStatus.IDLE.value for e in idle_employees)
    
    async def test_get_available_for_task(self, db_session: AsyncSession):
        """测试获取可接受任务的员工"""
        repo = EmployeeRepository(db_session)
        
        # 创建可用员工（预算充足）
        emp_available = await create_test_employee(
            db_session,
            name="可用员工",
            monthly_budget=1000.0,
            openclaw_agent_id="agent_1"
        )
        emp_available.used_budget = 100.0  # 剩余 900
        
        # 创建不可用员工（预算不足）
        emp_unavailable = await create_test_employee(
            db_session,
            name="预算不足",
            monthly_budget=1000.0,
            openclaw_agent_id="agent_2"
        )
        emp_unavailable.used_budget = 950.0  # 剩余 50
        
        await db_session.flush()
        
        # 查询需要 100 预算的任务可用员工
        available = await repo.get_available_for_task(estimated_cost=100.0)
        
        # 可用员工应该在列表中
        assert any(e.id == emp_available.id for e in available)
    
    async def test_update_budget(self, db_session: AsyncSession):
        """测试更新预算"""
        repo = EmployeeRepository(db_session)
        
        emp = await create_test_employee(db_session, monthly_budget=1000.0)
        
        # 增加预算
        updated = await repo.update_budget(emp.id, 500.0, operation="add")
        
        assert updated is not None
        assert updated.monthly_budget == 1500.0
        
        # 使用预算
        updated = await repo.update_budget(emp.id, 200.0, operation="use")
        
        assert updated.used_budget == 200.0
    
    async def test_update_status(self, db_session: AsyncSession):
        """测试更新状态"""
        repo = EmployeeRepository(db_session)
        
        emp = await create_test_employee(db_session)
        
        updated = await repo.update_status(
            emp.id, 
            AgentStatus.WORKING,
            current_task_id="task_123"
        )
        
        assert updated is not None
        assert updated.status == AgentStatus.WORKING.value
        assert updated.current_task_id == "task_123"
    
    async def test_bind_openclaw_agent(self, db_session: AsyncSession):
        """测试绑定Agent"""
        repo = EmployeeRepository(db_session)
        
        emp = await create_test_employee(db_session)
        
        updated = await repo.bind_openclaw_agent(emp.id, "new_agent_id")
        
        assert updated is not None
        assert updated.openclaw_agent_id == "new_agent_id"
        assert updated.is_bound == "true"
    
    async def test_increment_completed_tasks(self, db_session: AsyncSession):
        """测试增加完成任务计数"""
        repo = EmployeeRepository(db_session)
        
        emp = await create_test_employee(db_session)
        original_count = emp.completed_tasks
        
        updated = await repo.increment_completed_tasks(emp.id)
        
        assert updated is not None
        assert updated.completed_tasks == original_count + 1
    
    async def test_get_budget_stats(self, db_session: AsyncSession):
        """测试获取预算统计"""
        repo = EmployeeRepository(db_session)
        
        # 创建测试员工
        await create_test_employee(db_session, monthly_budget=1000.0)
        await create_test_employee(db_session, monthly_budget=2000.0)
        
        stats = await repo.get_budget_stats()
        
        assert isinstance(stats, dict)
        assert "total_employees" in stats
        assert "total_budget" in stats
        assert stats["total_employees"] >= 2
        assert stats["total_budget"] >= 3000.0
    
    async def test_get_all_with_pagination(self, db_session: AsyncSession):
        """测试分页查询"""
        repo = EmployeeRepository(db_session)
        
        # 创建多个员工
        for i in range(5):
            await create_test_employee(db_session, name=f"员工{i}")
        
        # 查询全部
        all_employees = await repo.get_all()
        assert isinstance(all_employees, list)
        assert len(all_employees) >= 5
        assert all(isinstance(e, Employee) for e in all_employees)
        
        # 分页查询
        page1 = await repo.get_all(offset=0, limit=2)
        assert len(page1) == 2
        
        page2 = await repo.get_all(offset=2, limit=2)
        assert len(page2) == 2
    
    async def test_delete_employee(self, db_session: AsyncSession):
        """测试删除员工"""
        repo = EmployeeRepository(db_session)
        
        emp = await create_test_employee(db_session)
        emp_id = emp.id
        
        # 删除（需要传入实例）
        await repo.delete(emp)
        
        # 验证删除
        found = await repo.get_by_id(emp_id)
        assert found is None
