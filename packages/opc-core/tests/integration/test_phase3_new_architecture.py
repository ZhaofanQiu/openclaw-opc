"""
opc-core: Phase 3 集成测试 (v0.4.1) - 异步架构

测试异步架构下的完整流程:
- 任务分配立即返回 (assigned 状态)
- 后台任务被创建
- ResponseParser 解析结果

作者: OpenClaw OPC Team
版本: 0.4.1
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from opc_database.models import Base, Employee, Task, AgentStatus, TaskStatus
from opc_database.repositories import EmployeeRepository, TaskRepository

from opc_core.services import TaskService, TaskNotFoundError, EmployeeNotFoundError, AgentNotBoundError, TaskAssignmentError


# ============ Fixtures ============


@pytest_asyncio.fixture
async def db_session():
    """创建内存数据库会话用于集成测试"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def task_service(db_session):
    """创建 TaskService 实例"""
    task_repo = TaskRepository(db_session)
    emp_repo = EmployeeRepository(db_session)
    return TaskService(task_repo=task_repo, emp_repo=emp_repo)


@pytest_asyncio.fixture
async def sample_employee(db_session):
    """创建测试员工"""
    emp = Employee(
        id="emp_int_001",
        name="集成测试员工",
        emoji="🤖",
        status=AgentStatus.IDLE,
        monthly_budget=1000.0,
        used_budget=0.0,
        openclaw_agent_id="opc_worker_001",
    )
    db_session.add(emp)
    await db_session.commit()
    return emp


@pytest_asyncio.fixture
async def sample_task(db_session):
    """创建测试任务"""
    task = Task(
        id="task_int_001",
        title="集成测试任务",
        description="测试异步分配流程",
        status=TaskStatus.PENDING,
        priority="normal",
        estimated_cost=500.0,
        assigned_to="emp_int_001",
    )
    db_session.add(task)
    await db_session.commit()
    return task


# ============ ResponseParser 集成测试 ============


class TestResponseParserIntegration:
    """ResponseParser 集成测试"""

    @pytest.mark.asyncio
    async def test_parse_completed_response(self):
        """测试解析 completed 状态响应"""
        from opc_openclaw import ResponseParser

        parser = ResponseParser()

        agent_response = """
任务已完成！

---OPC-REPORT---
task_id: task_int_001
status: completed
tokens_used: 450
summary: 成功完成代码审查，发现3个问题
---END-REPORT---
"""
        result = parser.parse(agent_response)

        assert result.is_valid is True
        assert result.status == "completed"
        assert result.tokens_used == 450
        assert result.summary == "成功完成代码审查，发现3个问题"
        assert result.task_id == "task_int_001"

    @pytest.mark.asyncio
    async def test_parse_failed_response(self):
        """测试解析 failed 状态响应"""
        from opc_openclaw import ResponseParser

        parser = ResponseParser()

        agent_response = """
执行任务时遇到错误。

---OPC-REPORT---
task_id: task_int_001
status: failed
tokens_used: 200
summary: 依赖安装失败，无法继续
---END-REPORT---
"""
        result = parser.parse(agent_response)

        assert result.is_valid is True
        assert result.status == "failed"
        assert result.tokens_used == 200
        assert "依赖安装失败" in result.summary

    @pytest.mark.asyncio
    async def test_parse_needs_revision_response(self):
        """测试解析 needs_revision 状态响应"""
        from opc_openclaw import ResponseParser

        parser = ResponseParser()

        agent_response = """
任务需要返工。

---OPC-REPORT---
task_id: task_int_001
status: needs_revision
tokens_used: 300
summary: 代码风格不符合规范，请修改
---END-REPORT---
"""
        result = parser.parse(agent_response)

        assert result.is_valid is True
        assert result.status == "needs_revision"
        assert result.tokens_used == 300

    @pytest.mark.asyncio
    async def test_parse_no_report_format(self):
        """测试无 OPC-REPORT 格式的响应 (解析失败)"""
        from opc_openclaw import ResponseParser

        parser = ResponseParser()

        agent_response = "I have completed the task successfully!"
        result = parser.parse(agent_response)

        assert result.is_valid is False
        assert result.status == ""
        assert result.errors


# ============ 异步任务分配测试 ============


class TestAsyncTaskAssignment:
    """异步任务分配测试 - assign_task 立即返回，后台执行"""

    @pytest.mark.asyncio
    async def test_assign_task_returns_immediately(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试 assign_task 立即返回 assigned 状态"""
        
        # Mock 后台任务，不实际执行
        with patch.object(
            task_service, '_execute_task_in_background', new_callable=AsyncMock
        ):
            result = await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_int_001",
            )

        # 验证：立即返回 assigned 状态
        assert result.status == TaskStatus.ASSIGNED.value
        assert result.assigned_to == "emp_int_001"

    @pytest.mark.asyncio
    async def test_assign_task_updates_employee_status_sync(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试 assign_task 同步更新员工状态为 working"""
        
        with patch.object(
            task_service, '_execute_task_in_background', new_callable=AsyncMock
        ):
            await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_int_001",
            )

        # 验证员工状态立即更新
        emp_repo = EmployeeRepository(db_session)
        employee = await emp_repo.get_by_id("emp_int_001")
        assert employee.status == AgentStatus.WORKING.value
        assert employee.current_task_id == "task_int_001"

    @pytest.mark.asyncio
    async def test_assign_task_creates_background_task(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试 assign_task 创建后台任务"""
        
        with patch.object(
            task_service, '_execute_task_in_background', new_callable=AsyncMock
        ) as mock_background:
            await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_int_001",
            )
            
            # 验证后台任务被创建
            mock_background.assert_called_once_with("task_int_001", "emp_int_001")


# ============ 任务重试集成测试 ============


class TestRetryTaskIntegration:
    """任务重试集成测试"""

    @pytest_asyncio.fixture
    async def failed_task(self, db_session):
        """创建失败任务"""
        task = Task(
            id="task_failed_001",
            title="失败任务",
            status=TaskStatus.FAILED,
            assigned_to="emp_int_001",
            rework_count=0,
            max_rework=3,
        )
        db_session.add(task)
        await db_session.commit()
        return task

    @pytest.mark.asyncio
    async def test_retry_task_returns_immediately(
        self, db_session, task_service, sample_employee, failed_task
    ):
        """测试重试立即返回 assigned 状态"""
        
        with patch.object(
            task_service, '_execute_task_in_background', new_callable=AsyncMock
        ):
            result = await task_service.retry_task("task_failed_001")

            # 立即返回 assigned
            assert result.status == TaskStatus.ASSIGNED.value
            # 验证返工计数已增加
            assert result.rework_count == 1

    @pytest.mark.asyncio
    async def test_retry_max_reached(self, db_session, task_service):
        """测试返工次数已达上限"""
        
        task = Task(
            id="task_max_rework",
            title="已达上限任务",
            status=TaskStatus.FAILED,
            assigned_to="emp_int_001",
            rework_count=3,
            max_rework=3,
        )
        db_session.add(task)
        await db_session.commit()

        with pytest.raises(TaskAssignmentError) as exc_info:
            await task_service.retry_task("task_max_rework")

        assert "max rework limit" in str(exc_info.value).lower()


# ============ 错误处理测试 ============


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_task_not_found(
        self, db_session, task_service, sample_employee
    ):
        """测试任务不存在错误"""

        with pytest.raises(TaskNotFoundError):
            await task_service.assign_task(
                task_id="non_existent_task",
                employee_id="emp_int_001",  # 使用存在的员工
            )

    @pytest.mark.asyncio
    async def test_employee_not_found(
        self, db_session, task_service, sample_task
    ):
        """测试员工不存在错误"""

        with pytest.raises(EmployeeNotFoundError):
            await task_service.assign_task(
                task_id="task_int_001",
                employee_id="non_existent_emp",
            )

    @pytest.mark.asyncio
    async def test_agent_not_bound(
        self, db_session, task_service, sample_task
    ):
        """测试员工未绑定 Agent 错误"""

        # 创建未绑定 Agent 的员工
        emp_repo = EmployeeRepository(db_session)
        employee = Employee(
            id="emp_no_agent",
            name="未绑定员工",
            status=AgentStatus.IDLE,
            monthly_budget=1000.0,
            openclaw_agent_id=None,  # 未绑定
        )
        await emp_repo.create(employee)

        # 更新任务分配
        sample_task.assigned_to = "emp_no_agent"
        await db_session.commit()

        with pytest.raises(AgentNotBoundError):
            await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_no_agent",
            )
