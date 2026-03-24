"""
opc-database: 员工模型单元测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
import uuid

from opc_database.models import Employee, AgentStatus, PositionLevel


class TestEmployeeModel:
    """员工模型测试"""
    
    def test_employee_creation(self):
        """测试员工创建"""
        employee = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="测试员工",
            emoji="🤖",
            position_level=PositionLevel.SPECIALIST.value,
            monthly_budget=5000.0,
        )
        
        assert employee.name == "测试员工"
        assert employee.emoji == "🤖"
        assert employee.status == AgentStatus.IDLE.value
        assert employee.remaining_budget == 5000.0
    
    def test_remaining_budget_calculation(self):
        """测试剩余预算计算"""
        employee = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="测试员工",
            monthly_budget=1000.0,
            used_budget=300.0,
        )
        
        assert employee.remaining_budget == 700.0
        assert employee.budget_percentage == 70.0
    
    def test_mood_emoji(self):
        """测试心情表情"""
        # 预算充足
        emp1 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="员工1",
            monthly_budget=1000.0,
            used_budget=100.0,  # 90%
        )
        assert emp1.mood_emoji == "😊"
        
        # 预算紧张
        emp2 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="员工2",
            monthly_budget=1000.0,
            used_budget=950.0,  # 5%
        )
        assert emp2.mood_emoji == "🚨"
    
    def test_can_accept_task(self):
        """测试是否能接受任务"""
        # 空闲且预算充足
        emp1 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="员工1",
            status=AgentStatus.IDLE.value,
            monthly_budget=1000.0,
            used_budget=0.0,
        )
        assert emp1.can_accept_task(estimated_cost=500.0) is True
        
        # 预算不足
        emp2 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="员工2",
            status=AgentStatus.IDLE.value,
            monthly_budget=1000.0,
            used_budget=900.0,
        )
        assert emp2.can_accept_task(estimated_cost=500.0) is False
        
        # 离线状态
        emp3 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="员工3",
            status=AgentStatus.OFFLINE.value,
            monthly_budget=1000.0,
            used_budget=0.0,
        )
        assert emp3.can_accept_task() is False


class TestEmployeeRepository:
    """员工仓库测试"""
    
    @pytest.mark.asyncio
    async def test_create_and_get(self, db_session):
        """测试创建和查询"""
        from opc_database.repositories import EmployeeRepository
        
        repo = EmployeeRepository(db_session)
        
        # 创建员工
        emp_id = f"emp_{uuid.uuid4().hex[:8]}"
        employee = Employee(
            id=emp_id,
            name="测试员工",
            monthly_budget=5000.0,
        )
        
        created = await repo.create(employee)
        assert created.id == emp_id
        assert created.name == "测试员工"
        
        # 查询
        found = await repo.get_by_id(emp_id)
        assert found is not None
        assert found.name == "测试员工"
    
    @pytest.mark.asyncio
    async def test_update_budget(self, db_session):
        """测试更新预算"""
        from opc_database.repositories import EmployeeRepository
        
        repo = EmployeeRepository(db_session)
        
        # 创建员工
        emp_id = f"emp_{uuid.uuid4().hex[:8]}"
        employee = Employee(
            id=emp_id,
            name="测试员工",
            monthly_budget=1000.0,
            used_budget=0.0,
        )
        await repo.create(employee)
        
        # 使用预算
        updated = await repo.update_budget(emp_id, 300.0, operation="use")
        assert updated is not None
        assert updated.used_budget == 300.0
        assert updated.remaining_budget == 700.0
    
    @pytest.mark.asyncio
    async def test_get_available_for_task(self, db_session):
        """测试获取可用员工"""
        from opc_database.repositories import EmployeeRepository
        
        repo = EmployeeRepository(db_session)
        
        # 创建可用员工
        emp1 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="可用员工1",
            status=AgentStatus.IDLE.value,
            monthly_budget=1000.0,
            used_budget=0.0,
        )
        await repo.create(emp1)
        
        # 创建离线员工
        emp2 = Employee(
            id=f"emp_{uuid.uuid4().hex[:8]}",
            name="离线员工",
            status=AgentStatus.OFFLINE.value,
            monthly_budget=1000.0,
            used_budget=0.0,
        )
        await repo.create(emp2)
        
        # 查询
        available = await repo.get_available_for_task(estimated_cost=500.0)
        assert len(available) == 1
        assert available[0].name == "可用员工1"
