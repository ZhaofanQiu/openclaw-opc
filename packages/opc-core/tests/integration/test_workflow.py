"""
opc-core: 工作流集成测试 (v0.4.2)

测试工作流核心功能：
1. 创建工作流
2. 步骤执行流程
3. 数据传递
4. 返工机制

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opc_database.models import Task, TaskStatus
from opc_core.services import (
    WorkflowService,
    WorkflowStepConfig,
    WorkflowError,
    InvalidStepConfigError,
    ReworkLimitExceeded,
    InvalidReworkTarget,
)


@pytest.fixture
def mock_task_repo():
    """Mock TaskRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.get_by_workflow = AsyncMock(return_value=[])
    repo.get_workflow_head = AsyncMock()
    return repo


@pytest.fixture
def mock_emp_repo():
    """Mock EmployeeRepository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_task_service():
    """Mock TaskService"""
    service = MagicMock()
    service.assign_task = AsyncMock()
    return service


@pytest.fixture
def workflow_service(mock_task_repo, mock_emp_repo, mock_task_service):
    """创建 WorkflowService 实例"""
    return WorkflowService(
        task_repo=mock_task_repo,
        emp_repo=mock_emp_repo,
        task_service=mock_task_service,
    )


@pytest.fixture
def mock_employee():
    """Mock 员工"""
    emp = MagicMock()
    emp.id = "emp-001"
    emp.name = "Test Employee"
    emp.openclaw_agent_id = "opc-worker-1"
    emp.monthly_budget = 1000.0
    emp.used_budget = 0.0
    return emp


@pytest.fixture
def mock_employee2():
    """Mock 员工2"""
    emp = MagicMock()
    emp.id = "emp-002"
    emp.name = "Test Employee 2"
    emp.openclaw_agent_id = "opc-worker-2"
    emp.monthly_budget = 1000.0
    emp.used_budget = 0.0
    return emp


class TestCreateWorkflow:
    """测试创建工作流"""

    async def test_create_simple_workflow(self, workflow_service, mock_emp_repo, mock_task_repo, mock_employee, mock_employee2):
        """测试创建简单工作流（2步骤）"""
        # 设置 mock
        mock_emp_repo.get_by_id.side_effect = [mock_employee, mock_employee2]
        
        created_tasks = []
        async def mock_create(task):
            created_tasks.append(task)
            return task
        mock_task_repo.create.side_effect = mock_create

        # 创建工作流
        steps = [
            WorkflowStepConfig(
                employee_id="emp-001",
                title="Step 1",
                description="First step",
                estimated_cost=100,
            ),
            WorkflowStepConfig(
                employee_id="emp-002",
                title="Step 2",
                description="Second step",
                estimated_cost=150,
            ),
        ]

        result = await workflow_service.create_workflow(
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            initial_input={"key": "value"},
            created_by="user-001",
        )

        # 验证结果
        assert result.workflow_id is not None
        assert result.first_task_id is not None
        assert len(result.task_ids) == 2
        assert result.status == "running"

        # 验证任务创建
        assert len(created_tasks) == 2
        assert created_tasks[0].step_index == 0
        assert created_tasks[0].total_steps == 2
        assert created_tasks[1].step_index == 1
        assert created_tasks[1].total_steps == 2

        # 验证链表关系
        assert created_tasks[0].depends_on is None
        assert created_tasks[0].next_task_id == created_tasks[1].id
        assert created_tasks[1].depends_on == created_tasks[0].id
        assert created_tasks[1].next_task_id is None

        # 验证第一个任务被触发
        mock_task_service.assign_task.assert_called_once_with(
            created_tasks[0].id, created_tasks[0].assigned_to
        )

    async def test_create_workflow_with_invalid_employee(self, workflow_service, mock_emp_repo):
        """测试使用不存在的员工创建工作流"""
        mock_emp_repo.get_by_id.return_value = None

        steps = [
            WorkflowStepConfig(
                employee_id="emp-999",
                title="Step 1",
                description="First step",
            ),
        ]

        with pytest.raises(InvalidStepConfigError) as exc_info:
            await workflow_service.create_workflow(
                name="Test Workflow",
                description="A test workflow",
                steps=steps,
                initial_input={},
                created_by="user-001",
            )

        assert "Employee emp-999 not found" in str(exc_info.value)

    async def test_create_workflow_with_unbound_agent(self, workflow_service, mock_emp_repo):
        """测试使用未绑定Agent的员工创建工作流"""
        emp = MagicMock()
        emp.id = "emp-001"
        emp.openclaw_agent_id = None
        mock_emp_repo.get_by_id.return_value = emp

        steps = [
            WorkflowStepConfig(
                employee_id="emp-001",
                title="Step 1",
                description="First step",
            ),
        ]

        with pytest.raises(InvalidStepConfigError) as exc_info:
            await workflow_service.create_workflow(
                name="Test Workflow",
                description="A test workflow",
                steps=steps,
                initial_input={},
                created_by="user-001",
            )

        assert "has no agent bound" in str(exc_info.value)

    async def test_create_workflow_with_less_than_2_steps(self, workflow_service):
        """测试创建少于2步骤的工作流"""
        steps = [
            WorkflowStepConfig(
                employee_id="emp-001",
                title="Step 1",
                description="First step",
            ),
        ]

        with pytest.raises(InvalidStepConfigError) as exc_info:
            await workflow_service.create_workflow(
                name="Test Workflow",
                description="A test workflow",
                steps=steps,
                initial_input={},
                created_by="user-001",
            )

        assert "at least 2 steps" in str(exc_info.value)


class TestWorkflowExecution:
    """测试工作流执行"""

    async def test_trigger_next_step(self, workflow_service, mock_task_repo, mock_emp_repo, mock_task_service):
        """测试触发下一步"""
        # 创建模拟任务
        task1 = MagicMock()
        task1.id = "task-001"
        task1.step_index = 0
        task1.total_steps = 2
        task1.workflow_id = "wf-001"
        task1.assigned_to = "emp-001"
        task1.output_data = '{"summary": "Step 1 done", "structured_output": {"key": "value"}}'
        task1.next_task_id = "task-002"

        task2 = MagicMock()
        task2.id = "task-002"
        task2.step_index = 1
        task2.total_steps = 2
        task2.workflow_id = "wf-001"
        task2.assigned_to = "emp-002"
        task2.input_data = "{}"

        emp = MagicMock()
        emp.name = "Employee 1"

        mock_task_repo.get_by_id.side_effect = [task1, task2]
        mock_emp_repo.get_by_id.return_value = emp

        # 触发下一步
        result = await workflow_service._trigger_next_step(task1)

        # 验证下一步被触发
        assert result is not None
        assert result.id == "task-002"

        # 验证输入数据被更新
        mock_task_repo.update.assert_called()
        updated_task = mock_task_repo.update.call_args[0][0]
        assert updated_task.input_data is not None

        # 验证分配任务被调用
        mock_task_service.assign_task.assert_called_once_with("task-002", "emp-002")

    async def test_on_task_completed_not_last_step(self, workflow_service, mock_task_repo, mock_emp_repo):
        """测试非最后一步完成时的回调"""
        task = MagicMock()
        task.id = "task-001"
        task.workflow_id = "wf-001"
        task.step_index = 0
        task.total_steps = 3
        task.is_last_step.return_value = False
        task.next_task_id = "task-002"

        next_task = MagicMock()
        next_task.id = "task-002"

        emp = MagicMock()
        emp.name = "Employee"

        mock_task_repo.get_by_id.side_effect = [task, next_task, next_task]
        mock_emp_repo.get_by_id.return_value = emp

        with patch.object(workflow_service, '_trigger_next_step', new_callable=AsyncMock) as mock_trigger:
            await workflow_service.on_task_completed("task-001")
            mock_trigger.assert_called_once()

    async def test_on_task_completed_last_step(self, workflow_service, mock_task_repo):
        """测试最后一步完成时的回调"""
        task = MagicMock()
        task.id = "task-003"
        task.workflow_id = "wf-001"
        task.step_index = 2
        task.total_steps = 3
        task.is_last_step.return_value = True

        mock_task_repo.get_by_id.return_value = task

        with patch.object(workflow_service, '_finalize_workflow', new_callable=AsyncMock) as mock_finalize:
            result = await workflow_service.on_task_completed("task-003")
            assert result is None
            mock_finalize.assert_called_once_with("wf-001")


class TestRework:
    """测试返工机制"""

    async def test_request_rework_success(self, workflow_service, mock_task_repo, mock_emp_repo, mock_task_service):
        """测试成功请求返工"""
        # 创建模拟任务
        from_task = MagicMock()
        from_task.id = "task-002"
        from_task.workflow_id = "wf-001"
        from_task.step_index = 1
        from_task.assigned_to = "emp-002"

        to_task = MagicMock()
        to_task.id = "task-001"
        to_task.workflow_id = "wf-001"
        to_task.step_index = 0
        to_task.assigned_to = "emp-001"
        to_task.rework_count = 0
        to_task.max_rework = 2
        to_task.can_rework.return_value = True
        to_task.input_data = "{}"

        mock_task_repo.get_by_id.side_effect = [from_task, to_task]
        mock_task_repo.create = AsyncMock(return_value=MagicMock(id="task-001-rework"))

        emp = MagicMock()
        emp.name = "Employee 1"
        mock_emp_repo.get_by_id.return_value = emp

        # 请求返工
        result = await workflow_service.request_rework(
            from_task_id="task-002",
            to_task_id="task-001",
            reason="Need more data",
            instructions="Add more details",
        )

        # 验证返工任务创建
        assert result is not None
        mock_task_repo.create.assert_called_once()

        # 验证返工任务被触发
        mock_task_service.assign_task.assert_called_once()

    async def test_request_rework_to_downstream(self, workflow_service, mock_task_repo):
        """测试返工到下游步骤（应该失败）"""
        from_task = MagicMock()
        from_task.id = "task-001"
        from_task.workflow_id = "wf-001"
        from_task.step_index = 0

        to_task = MagicMock()
        to_task.id = "task-002"
        to_task.workflow_id = "wf-001"
        to_task.step_index = 1

        mock_task_repo.get_by_id.side_effect = [from_task, to_task]

        with pytest.raises(InvalidReworkTarget) as exc_info:
            await workflow_service.request_rework(
                from_task_id="task-001",
                to_task_id="task-002",
                reason="Need more data",
                instructions="Add more details",
            )

        assert "Can only rework upstream tasks" in str(exc_info.value)

    async def test_request_rework_exceed_limit(self, workflow_service, mock_task_repo):
        """测试超过返工次数限制"""
        from_task = MagicMock()
        from_task.id = "task-002"
        from_task.workflow_id = "wf-001"
        from_task.step_index = 1

        to_task = MagicMock()
        to_task.id = "task-001"
        to_task.workflow_id = "wf-001"
        to_task.step_index = 0
        to_task.rework_count = 2
        to_task.max_rework = 2
        to_task.can_rework.return_value = False

        mock_task_repo.get_by_id.side_effect = [from_task, to_task]

        with pytest.raises(ReworkLimitExceeded) as exc_info:
            await workflow_service.request_rework(
                from_task_id="task-002",
                to_task_id="task-001",
                reason="Need more data",
                instructions="Add more details",
            )

        assert "reached max rework limit" in str(exc_info.value)


class TestWorkflowProgress:
    """测试工作流进度"""

    async def test_get_workflow_progress(self, workflow_service, mock_task_repo):
        """测试获取工作流进度"""
        tasks = [
            MagicMock(status=TaskStatus.COMPLETED.value, step_index=0, total_steps=3),
            MagicMock(status=TaskStatus.COMPLETED.value, step_index=1, total_steps=3),
            MagicMock(status=TaskStatus.IN_PROGRESS.value, step_index=2, total_steps=3),
        ]

        mock_task_repo.get_by_workflow.return_value = tasks

        progress = await workflow_service.get_workflow_progress("wf-001")

        assert progress is not None
        assert progress.workflow_id == "wf-001"
        assert progress.total_steps == 3
        assert progress.completed_steps == 2
        assert progress.progress_percent == 66.7

    async def test_get_workflow_progress_not_found(self, workflow_service, mock_task_repo):
        """测试获取不存在的工作流进度"""
        mock_task_repo.get_by_workflow.return_value = []

        progress = await workflow_service.get_workflow_progress("wf-999")

        assert progress is None


class TestDataPassing:
    """测试数据传递"""

    async def test_input_data_structure(self, workflow_service, mock_task_repo, mock_emp_repo):
        """测试输入数据结构"""
        task = MagicMock()
        task.id = "task-001"
        task.step_index = 0
        task.total_steps = 2
        task.workflow_id = "wf-001"
        task.input_data = None

        mock_task_repo.create = AsyncMock(return_value=task)
        mock_emp_repo.get_by_id.return_value = MagicMock(
            id="emp-001",
            name="Test Employee",
            openclaw_agent_id="opc-worker-1",
        )

        steps = [
            WorkflowStepConfig(
                employee_id="emp-001",
                title="Step 1",
                description="First step",
            ),
            WorkflowStepConfig(
                employee_id="emp-002",
                title="Step 2",
                description="Second step",
            ),
        ]

        await workflow_service.create_workflow(
            name="Test Workflow",
            description="A test workflow",
            steps=steps,
            initial_input={"topic": "AI"},
            created_by="user-001",
        )

        # 验证第一个任务的输入数据
        created_task = mock_task_repo.create.call_args[0][0]
        import json
        input_data = json.loads(created_task.input_data)
        
        assert "workflow_context" in input_data
        assert input_data["workflow_context"]["workflow_id"] == "wf-001"
        assert input_data["workflow_context"]["total_steps"] == 2
        assert input_data["initial_input"]["topic"] == "AI"
        assert "previous_outputs" in input_data
