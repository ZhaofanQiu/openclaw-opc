"""
opc-database: 任务模型单元测试

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
import uuid
from datetime import datetime

from opc_database.models import Task, TaskMessage, TaskStatus, TaskPriority


class TestTaskModel:
    """任务模型测试"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="测试任务",
            description="这是一个测试任务",
            estimated_cost=1000.0,
        )
        
        assert task.title == "测试任务"
        assert task.status == TaskStatus.PENDING.value
        assert task.priority == TaskPriority.NORMAL.value
        assert task.remaining_budget == 1000.0
    
    def test_task_budget_calculation(self):
        """测试任务预算计算"""
        task = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="测试任务",
            estimated_cost=1000.0,
            actual_cost=300.0,
        )
        
        assert task.remaining_budget == 700.0
        assert task.is_completed is False
    
    def test_is_completed(self):
        """测试完成状态判断"""
        task_pending = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="待处理任务",
            status=TaskStatus.PENDING.value,
        )
        assert task_pending.is_completed is False
        
        task_completed = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="已完成任务",
            status=TaskStatus.COMPLETED.value,
        )
        assert task_completed.is_completed is True
    
    def test_total_tokens(self):
        """测试Token统计"""
        task = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="测试任务",
            tokens_input=100,
            tokens_output=50,
        )
        
        assert task.total_tokens == 150
    
    def test_can_rework(self):
        """测试返工判断"""
        # 未返工
        task1 = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="任务1",
            rework_count=0,
            max_rework=3,
        )
        assert task1.can_rework() is True
        
        # 已返工2次
        task2 = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="任务2",
            rework_count=2,
            max_rework=3,
        )
        assert task2.can_rework() is True
        
        # 已达到最大返工次数
        task3 = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="任务3",
            rework_count=3,
            max_rework=3,
        )
        assert task3.can_rework() is False


class TestTaskRepository:
    """任务仓库测试"""
    
    @pytest.mark.asyncio
    async def test_create_and_assign(self, db_session):
        """测试创建和分配任务"""
        from opc_database.repositories import TaskRepository
        
        repo = TaskRepository(db_session)
        
        # 创建任务
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(
            id=task_id,
            title="测试任务",
            estimated_cost=1000.0,
        )
        
        created = await repo.create(task)
        assert created.id == task_id
        assert created.status == TaskStatus.PENDING.value
        
        # 分配任务
        assigned = await repo.assign_task(task_id, "emp_123", assigned_by="user_1")
        assert assigned is not None
        assert assigned.assigned_to == "emp_123"
        assert assigned.status == TaskStatus.ASSIGNED.value
        assert assigned.assigned_at is not None
    
    @pytest.mark.asyncio
    async def test_complete_task(self, db_session):
        """测试完成任务"""
        from opc_database.repositories import TaskRepository
        
        repo = TaskRepository(db_session)
        
        # 创建任务
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(
            id=task_id,
            title="测试任务",
            estimated_cost=1000.0,
        )
        await repo.create(task)
        
        # 完成任务
        completed = await repo.complete_task(
            task_id,
            result="任务执行结果",
            actual_cost=500.0,
            tokens_input=100,
            tokens_output=50,
        )
        
        assert completed is not None
        assert completed.status == TaskStatus.COMPLETED.value
        assert completed.result == "任务执行结果"
        assert completed.actual_cost == 500.0
        assert completed.tokens_input == 100
        assert completed.tokens_output == 50
        assert completed.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_get_by_employee(self, db_session):
        """测试按员工获取任务"""
        from opc_database.repositories import TaskRepository
        
        repo = TaskRepository(db_session)
        
        # 创建多个任务
        emp_id = "emp_test"
        
        task1 = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="任务1",
            assigned_to=emp_id,
            status=TaskStatus.COMPLETED.value,
        )
        await repo.create(task1)
        
        task2 = Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            title="任务2",
            assigned_to=emp_id,
            status=TaskStatus.IN_PROGRESS.value,
        )
        await repo.create(task2)
        
        # 查询所有
        all_tasks = await repo.get_by_employee(emp_id)
        assert len(all_tasks) == 2
        
        # 按状态筛选
        completed_tasks = await repo.get_by_employee(emp_id, status=TaskStatus.COMPLETED)
        assert len(completed_tasks) == 1
        assert completed_tasks[0].title == "任务1"


class TestTaskMessageRepository:
    """任务消息仓库测试"""
    
    @pytest.mark.asyncio
    async def test_add_message(self, db_session):
        """测试添加消息"""
        from opc_database.repositories import TaskMessageRepository
        
        repo = TaskMessageRepository(db_session)
        
        # 添加消息
        message = await repo.add_message(
            task_id="task_123",
            sender_type="user",
            content="请完成这个任务",
            sender_id="user_1",
        )
        
        assert message.task_id == "task_123"
        assert message.sender_type == "user"
        assert message.content == "请完成这个任务"
        assert message.sender_id == "user_1"
    
    @pytest.mark.asyncio
    async def test_get_by_task(self, db_session):
        """测试获取任务消息"""
        from opc_database.repositories import TaskMessageRepository
        
        repo = TaskMessageRepository(db_session)
        
        # 添加多条消息
        await repo.add_message("task_456", "user", "消息1")
        await repo.add_message("task_456", "agent", "消息2")
        await repo.add_message("task_456", "user", "消息3")
        
        # 查询
        messages = await repo.get_by_task("task_456")
        assert len(messages) == 3
        assert messages[0].content == "消息1"
        assert messages[1].content == "消息2"
        assert messages[2].content == "消息3"
