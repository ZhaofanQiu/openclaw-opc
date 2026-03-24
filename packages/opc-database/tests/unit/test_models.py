"""
模型定义测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from opc_database.models import Employee, CompanyBudget, Task, TaskMessage
from opc_database.models.employee import AgentStatus, PositionLevel
from opc_database.models.task import TaskStatus, TaskPriority


@pytest.mark.asyncio
class TestEmployeeModel:
    """Employee 模型测试"""
    
    async def test_employee_creation(self, db_session: AsyncSession):
        """测试员工创建"""
        emp = Employee(
            id=str(uuid.uuid4()),
            name="测试员工",
            emoji="🤖",
            position_level=PositionLevel.SPECIALIST,
            monthly_budget=1000.0,
            status=AgentStatus.IDLE
        )
        
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)
        
        assert emp.id is not None
        assert emp.name == "测试员工"
        assert emp.position_level == PositionLevel.SPECIALIST.value
    
    async def test_employee_budget_properties(self, db_session: AsyncSession):
        """测试员工预算属性"""
        emp = Employee(
            id=str(uuid.uuid4()),
            name="测试",
            monthly_budget=1000.0,
            used_budget=300.0
        )
        
        # 剩余预算 = 1000 - 300 = 700
        assert emp.remaining_budget == 700.0
        # 剩余百分比 = 700 / 1000 * 100 = 70%
        assert emp.budget_percentage == 70.0
    
    async def test_employee_default_values(self, db_session: AsyncSession):
        """测试默认值"""
        emp = Employee(id=str(uuid.uuid4()), name="测试")
        
        # 先提交到数据库以获取默认值
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)
        
        # 检查数据库默认值
        assert emp.position_level == PositionLevel.INTERN.value
        assert emp.completed_tasks == 0
        assert emp.used_budget == 0.0


@pytest.mark.asyncio
class TestCompanyModel:
    """Company 模型测试"""
    
    async def test_company_creation(self, db_session: AsyncSession):
        """测试公司创建"""
        from datetime import datetime
        
        company = CompanyBudget(
            id=str(uuid.uuid4()),
            total_budget=10000.0,
            month=datetime.now().strftime("%Y-%m")  # 需要 month 字段
        )
        
        db_session.add(company)
        await db_session.commit()
        
        assert company.id is not None
        assert company.total_budget == 10000.0
    
    async def test_company_budget_properties(self, db_session: AsyncSession):
        """测试公司预算属性"""
        company = CompanyBudget(
            id=str(uuid.uuid4()),
            total_budget=10000.0,
            used_budget=2500.0
        )
        
        assert company.remaining_budget == 7500.0


@pytest.mark.asyncio
class TestTaskModel:
    """Task 模型测试"""
    
    async def test_task_creation(self, db_session: AsyncSession):
        """测试任务创建"""
        task = Task(
            id=str(uuid.uuid4()),
            title="测试任务",
            description="描述",
            priority=TaskPriority.HIGH,
            estimated_cost=500.0
        )
        
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        assert task.id is not None
        assert task.title == "测试任务"
        assert task.status == TaskStatus.PENDING.value
    
    async def test_task_default_priority(self, db_session: AsyncSession):
        """测试默认优先级"""
        task = Task(id=str(uuid.uuid4()), title="测试")
        
        # 先提交到数据库以获取默认值
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        # 默认优先级应该是 normal
        assert task.priority == TaskPriority.NORMAL.value
    
    async def test_task_can_rework(self, db_session: AsyncSession):
        """测试返工检查"""
        task = Task(id=str(uuid.uuid4()), title="测试")
        
        # 先提交到数据库以获取默认值
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)
        
        # 初始可以返工 (rework_count=0, max_rework=2)
        assert task.can_rework() is True
        
        # 设置返工次数超过限制
        task.rework_count = 3
        assert task.can_rework() is False


@pytest.mark.asyncio
class TestTaskMessageModel:
    """TaskMessage 模型测试"""
    
    async def test_message_creation(self, db_session: AsyncSession):
        """测试消息创建"""
        msg = TaskMessage(
            id=str(uuid.uuid4()),
            task_id="task_123",
            sender_type="agent",
            content="测试消息"
        )
        
        db_session.add(msg)
        await db_session.commit()
        await db_session.refresh(msg)
        
        assert msg.id is not None
        assert msg.task_id == "task_123"
        assert msg.sender_type == "agent"
        assert msg.content == "测试消息"
