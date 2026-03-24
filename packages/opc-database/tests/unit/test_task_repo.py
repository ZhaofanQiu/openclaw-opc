"""
TaskRepository 测试

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

from opc_database.models import Task, TaskStatus, TaskPriority
from opc_database.repositories import TaskRepository
from tests.utils import create_test_task, create_test_employee


@pytest.mark.asyncio
class TestTaskRepository:
    """TaskRepository 测试类"""
    
    async def test_create_task(self, db_session: AsyncSession):
        """测试创建任务"""
        repo = TaskRepository(db_session)
        
        task = await create_test_task(db_session, title="测试任务")
        
        assert task.id is not None
        assert task.title == "测试任务"
        assert task.status == TaskStatus.PENDING.value
    
    async def test_get_by_id(self, db_session: AsyncSession):
        """测试根据ID获取任务"""
        repo = TaskRepository(db_session)
        
        created = await create_test_task(db_session, title="任务A")
        
        found = await repo.get_by_id(created.id)
        
        assert found is not None
        assert found.id == created.id
        assert found.title == "任务A"
    
    async def test_get_by_employee(self, db_session: AsyncSession):
        """测试获取员工任务"""
        repo = TaskRepository(db_session)
        
        # 创建员工
        emp = await create_test_employee(db_session)
        
        # 创建任务并分配
        task1 = await create_test_task(db_session, assigned_to=emp.id)
        task2 = await create_test_task(db_session, assigned_to=emp.id)
        
        # 查询
        tasks = await repo.get_by_employee(emp.id)
        
        assert len(tasks) == 2
        assert all(t.assigned_to == emp.id for t in tasks)
    
    async def test_get_by_status(self, db_session: AsyncSession):
        """测试根据状态获取任务"""
        repo = TaskRepository(db_session)
        
        # 创建不同状态的任务
        task_pending = await create_test_task(db_session)
        task_pending.status = TaskStatus.PENDING.value
        
        task_completed = await create_test_task(db_session)
        task_completed.status = TaskStatus.COMPLETED.value
        
        await db_session.flush()
        
        # 查询
        pending_tasks = await repo.get_by_status(TaskStatus.PENDING)
        
        assert len(pending_tasks) >= 1
        assert all(t.status == TaskStatus.PENDING.value for t in pending_tasks)
    
    async def test_get_pending_tasks(self, db_session: AsyncSession):
        """测试获取待分配任务"""
        repo = TaskRepository(db_session)
        
        # 创建待分配任务
        task = await create_test_task(db_session)
        task.status = TaskStatus.PENDING.value
        await db_session.flush()
        
        pending = await repo.get_pending_tasks()
        
        assert len(pending) >= 1
        assert all(t.status == TaskStatus.PENDING.value for t in pending)
    
    async def test_assign_task(self, db_session: AsyncSession):
        """测试分配任务"""
        repo = TaskRepository(db_session)
        
        task = await create_test_task(db_session)
        emp = await create_test_employee(db_session)
        
        updated = await repo.assign_task(task.id, emp.id, assigned_by="user_1")
        
        assert updated is not None
        assert updated.assigned_to == emp.id
        assert updated.assigned_by == "user_1"
        assert updated.status == TaskStatus.ASSIGNED.value
        assert updated.assigned_at is not None
    
    async def test_start_task(self, db_session: AsyncSession):
        """测试开始任务"""
        repo = TaskRepository(db_session)
        
        task = await create_test_task(db_session)
        
        updated = await repo.start_task(task.id, session_key="sess_123")
        
        assert updated is not None
        assert updated.status == TaskStatus.IN_PROGRESS.value
        assert updated.started_at is not None
        assert updated.session_key == "sess_123"
    
    async def test_complete_task(self, db_session: AsyncSession):
        """测试完成任务"""
        repo = TaskRepository(db_session)
        
        task = await create_test_task(db_session)
        
        updated = await repo.complete_task(
            task.id,
            result="任务完成结果",
            actual_cost=300.0,
            tokens_input=100,
            tokens_output=50
        )
        
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED.value
        assert updated.result == "任务完成结果"
        assert updated.actual_cost == 300.0
        assert updated.tokens_input == 100
        assert updated.tokens_output == 50
        assert updated.completed_at is not None
    
    async def test_fail_task(self, db_session: AsyncSession):
        """测试标记任务失败"""
        repo = TaskRepository(db_session)
        
        task = await create_test_task(db_session)
        
        updated = await repo.fail_task(task.id, "资源不足")
        
        assert updated is not None
        assert updated.status == TaskStatus.FAILED.value
        assert "资源不足" in updated.result
        assert updated.completed_at is not None
    
    async def test_request_rework(self, db_session: AsyncSession):
        """测试请求返工"""
        repo = TaskRepository(db_session)
        
        # 先创建一个已完成任务
        task = await create_test_task(db_session)
        task.status = TaskStatus.COMPLETED.value
        task.rework_count = 0
        await db_session.flush()
        
        # 请求返工
        updated = await repo.request_rework(task.id, "需要修改")
        
        assert updated is not None
        assert updated.status == TaskStatus.IN_PROGRESS.value
        assert updated.rework_count == 1
        assert updated.feedback == "需要修改"
        assert updated.completed_at is None  # 清除完成时间
    
    async def test_request_rework_exceed_limit(self, db_session: AsyncSession):
        """测试返工次数超过限制"""
        repo = TaskRepository(db_session)
        
        # 创建已达返工上限的任务
        task = await create_test_task(db_session)
        task.status = TaskStatus.COMPLETED.value
        task.rework_count = 3  # 已达上限
        await db_session.flush()
        
        # 请求返工应该失败
        updated = await repo.request_rework(task.id, "再次修改")
        
        assert updated is None
    
    async def test_get_task_stats(self, db_session: AsyncSession):
        """测试获取任务统计"""
        repo = TaskRepository(db_session)
        
        # 创建测试任务
        await create_test_task(db_session, estimated_cost=500.0, actual_cost=400.0)
        await create_test_task(db_session, estimated_cost=300.0, actual_cost=250.0)
        
        stats = await repo.get_task_stats()
        
        assert "total_tasks" in stats
        assert "total_estimated_cost" in stats
        assert "total_actual_cost" in stats
        assert "status_counts" in stats
        assert stats["total_tasks"] >= 2
    
    async def test_update_nonexistent_task(self, db_session: AsyncSession):
        """测试更新不存在的任务"""
        repo = TaskRepository(db_session)
        
        result = await repo.assign_task("non_existent", "emp_id")
        
        assert result is None
