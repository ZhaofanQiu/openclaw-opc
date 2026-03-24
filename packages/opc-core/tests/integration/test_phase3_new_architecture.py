"""
opc-core: Phase 3 集成测试 (v0.4.1)

测试新架构下的完整流程:
- 同步任务分配
- ResponseParser 解析
- 预算结算

作者: OpenClaw OPC Team
版本: 0.4.1
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from opc_database.models import Base, Employee, Task, AgentStatus, TaskStatus
from opc_database.repositories import EmployeeRepository, TaskRepository

from opc_core.services import TaskService, TaskNotFoundError, EmployeeNotFoundError


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
        # remaining_budget 是计算属性，不需要设置
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
        description="测试同步分配流程",
        status=TaskStatus.PENDING,
        priority="normal",
        estimated_cost=500.0,
        assigned_to="emp_int_001",  # 预先分配
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
        from opc_openclaw import ResponseParser, ParsedReport

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

        assert result.is_valid is True  # 格式正确
        assert result.status == "failed"  # 但状态是失败
        assert result.tokens_used == 200
        assert "依赖安装失败" in result.summary

    @pytest.mark.asyncio
    async def test_parse_no_report_format(self):
        """测试无 OPC-REPORT 格式的响应 (解析失败)"""
        from opc_openclaw import ResponseParser

        parser = ResponseParser()

        agent_response = "I have completed the task successfully!"
        result = parser.parse(agent_response)

        assert result.is_valid is False  # 格式不正确
        assert result.status == ""  # 无法解析状态
        assert result.errors  # 应该有错误信息


# ============ TaskService + ResponseParser 集成测试 ============


class TestTaskServiceIntegration:
    """TaskService 集成测试 (含 Mock TaskCaller)"""

    @pytest.mark.asyncio
    async def test_assign_task_success_flow(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试完整成功流程: 分配 → Agent执行 → 解析 → 更新"""

        # Mock TaskCaller 返回 completed 响应
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.session_key = "sess_test_001"
        mock_response.content = """
任务已完成！

---OPC-REPORT---
task_id: task_int_001
status: completed
tokens_used: 450
summary: 成功完成代码审查，发现3个问题
---END-REPORT---
"""

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            # 执行任务分配
            result = await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_int_001",
            )

        # 验证结果
        assert result.status == TaskStatus.COMPLETED.value
        assert result.actual_cost == 0.45  # 450 / 1000
        assert "成功完成代码审查" in result.result

        # 验证员工状态
        emp_repo = EmployeeRepository(db_session)
        employee = await emp_repo.get_by_id("emp_int_001")
        assert employee.status == AgentStatus.IDLE.value  # 任务完成后恢复空闲
        assert employee.used_budget == 0.45
        assert employee.remaining_budget == 999.55

    @pytest.mark.asyncio
    async def test_assign_task_failed_flow(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试失败流程: Agent 返回 failed 状态"""

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.session_key = "sess_test_002"
        mock_response.content = """
---OPC-REPORT---
task_id: task_int_001
status: failed
tokens_used: 200
summary: 依赖安装失败
---END-REPORT---
"""

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            result = await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_int_001",
            )

        assert result.status == TaskStatus.FAILED.value
        assert "依赖安装失败" in result.result

    @pytest.mark.asyncio
    async def test_assign_task_needs_review_flow(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试 needs_review 流程: 解析失败"""

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.session_key = "sess_test_003"
        mock_response.content = "I have done the task but no report format"

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            result = await task_service.assign_task(
                task_id="task_int_001",
                employee_id="emp_int_001",
            )

        assert result.status == TaskStatus.NEEDS_REVIEW.value

    @pytest.mark.asyncio
    async def test_assign_task_send_failure(
        self, db_session, task_service, sample_employee, sample_task
    ):
        """测试发送失败场景"""

        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error = "Agent not available"
        mock_response.error = "Agent not available"

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            from opc_core.services import TaskAssignmentError

            with pytest.raises(TaskAssignmentError) as exc_info:
                await task_service.assign_task(
                    task_id="task_int_001",
                    employee_id="emp_int_001",
                )

            assert "Agent not available" in str(exc_info.value)


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
    async def test_retry_task_success(
        self, db_session, task_service, sample_employee, failed_task
    ):
        """测试重试成功"""

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.session_key = "sess_retry_001"
        mock_response.content = """
---OPC-REPORT---
task_id: task_failed_001
status: completed
tokens_used: 300
summary: 重试成功
---END-REPORT---
"""

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            result = await task_service.retry_task("task_failed_001")

        assert result.status == TaskStatus.COMPLETED.value
        assert result.rework_count == 1

    @pytest.mark.asyncio
    async def test_retry_max_reached(self, db_session, task_service):
        """测试返工次数已达上限"""

        # 创建已达上限的任务
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

        from opc_core.services import TaskAssignmentError

        with pytest.raises(TaskAssignmentError) as exc_info:
            await task_service.retry_task("task_max_rework")

        assert "max rework limit" in str(exc_info.value).lower()


# ============ 端到端工作流测试 ============


class TestEndToEndNewArchitecture:
    """新架构端到端测试"""

    @pytest.mark.asyncio
    async def test_full_workflow_success(self, db_session):
        """
        完整成功工作流:
        1. 创建员工和任务
        2. 分配任务 (同步)
        3. 验证任务完成
        4. 验证预算结算
        """
        emp_repo = EmployeeRepository(db_session)
        task_repo = TaskRepository(db_session)
        task_service = TaskService(task_repo, emp_repo)

        # 1. 创建员工
        employee = Employee(
            id="emp_e2e_new",
            name="新架构测试员工",
            emoji="🚀",
            status=AgentStatus.IDLE,
            monthly_budget=1000.0,
            openclaw_agent_id="opc_worker_e2e",
        )
        await emp_repo.create(employee)

        # 2. 创建任务 (已分配给该员工)
        task = Task(
            id="task_e2e_new",
            title="新架构端到端任务",
            description="测试完整流程",
            status=TaskStatus.PENDING,
            estimated_cost=500.0,
            assigned_to="emp_e2e_new",  # 预先分配
        )
        await task_repo.create(task)

        # 3. 模拟 Agent 成功响应
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.session_key = "sess_e2e_001"
        mock_response.content = """
已根据手册完成任务。

---OPC-REPORT---
task_id: task_e2e_new
status: completed
tokens_used: 420
summary: 代码审查完成，发现2个潜在问题并给出建议
result_files: ["/tmp/review_report.md"]
---END-REPORT---
"""

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_response

            # 执行分配
            result = await task_service.assign_task(
                task_id="task_e2e_new",
                employee_id="emp_e2e_new",
            )

        # 4. 验证结果
        assert result.status == TaskStatus.COMPLETED.value
        assert result.actual_cost == 0.42  # 420 / 1000

        # 5. 验证员工预算
        updated_emp = await emp_repo.get_by_id("emp_e2e_new")
        assert updated_emp.used_budget == 0.42
        assert updated_emp.remaining_budget == 999.58
        assert updated_emp.completed_tasks == 1

    @pytest.mark.asyncio
    async def test_full_workflow_with_rework(self, db_session):
        """
        带返工的完整工作流:
        1. 首次分配失败
        2. 重试成功
        """
        emp_repo = EmployeeRepository(db_session)
        task_repo = TaskRepository(db_session)
        task_service = TaskService(task_repo, emp_repo)

        # 创建员工和任务
        employee = Employee(
            id="emp_rework",
            name="返工测试员工",
            emoji="🔧",
            status=AgentStatus.IDLE,
            monthly_budget=1000.0,
            openclaw_agent_id="opc_worker_rework",
        )
        await emp_repo.create(employee)

        task = Task(
            id="task_rework",
            title="返工测试任务",
            status=TaskStatus.PENDING,
            max_rework=3,
            assigned_to="emp_rework",  # 预先分配
        )
        await task_repo.create(task)

        # 首次分配失败
        mock_fail_response = MagicMock()
        mock_fail_response.success = True
        mock_fail_response.session_key = "sess_rework_fail_001"
        mock_fail_response.content = """
---OPC-REPORT---
task_id: task_rework
status: failed
tokens_used: 150
summary: 环境配置错误
---END-REPORT---
"""

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_fail_response

            result = await task_service.assign_task(
                task_id="task_rework",
                employee_id="emp_rework",
            )

        assert result.status == TaskStatus.FAILED.value
        assert result.rework_count == 0

        # 重试成功
        mock_success_response = MagicMock()
        mock_success_response.success = True
        mock_success_response.session_key = "sess_rework_success_001"
        mock_success_response.content = """
---OPC-REPORT---
task_id: task_rework
status: completed
tokens_used: 300
summary: 重试成功，问题已解决
---END-REPORT---
"""

        with patch.object(
            task_service.task_caller, 'assign_task', new_callable=AsyncMock
        ) as mock_assign:
            mock_assign.return_value = mock_success_response

            result = await task_service.retry_task("task_rework")

        assert result.status == TaskStatus.COMPLETED.value
        assert result.rework_count == 1
        assert result.actual_cost == 0.3  # 300 / 1000


# ============ 性能测试 ============


class TestPerformance:
    """性能测试"""

    @pytest.mark.asyncio
    async def test_assign_task_timeout(self, db_session, task_service, sample_employee, sample_task):
        """测试超时处理"""
        import asyncio

        # Mock 长时间运行的任务
        async def slow_assign(*args, **kwargs):
            await asyncio.sleep(2)  # 模拟2秒延迟
            return MagicMock(
                success=True,
                session_key="sess_timeout_001",
                content="---OPC-REPORT---\nstatus: completed\ntokens_used: 100\n---END-REPORT---"
            )

        with patch.object(
            task_service.task_caller, 'assign_task', side_effect=slow_assign
        ):
            # 使用较短的超时
            with pytest.raises(Exception):  # 应该触发超时
                await asyncio.wait_for(
                    task_service.assign_task("task_int_001", "emp_int_001"),
                    timeout=1.0
                )
