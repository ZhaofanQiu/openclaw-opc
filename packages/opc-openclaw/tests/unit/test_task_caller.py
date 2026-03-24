"""
opc-openclaw: TaskCaller 单元测试 (v0.4.1)
"""

import pytest
from pathlib import Path

from opc_openclaw.interaction import TaskCaller, TaskAssignment, TaskResponse
from opc_openclaw.interaction.messenger import MessageResponse


class TestTaskCaller:
    """TaskCaller 测试"""

    @pytest.fixture
    def sample_task(self):
        """示例任务"""
        return TaskAssignment(
            task_id="task-001",
            title="Code Review",
            description="Review the authentication module",
            agent_id="opc-worker-1",
            agent_name="Worker One",
            employee_id="emp-001",
            company_manual_path="/home/user/opc/manuals/company.md",
            employee_manual_path="/home/user/opc/manuals/employees/emp-001.md",
            task_manual_path="/home/user/opc/manuals/tasks/task-001.md",
            timeout=900,
        )

    @pytest.fixture
    def sample_task_with_budget(self):
        """带预算信息的示例任务"""
        return TaskAssignment(
            task_id="task-001",
            title="Code Review",
            description="Review the authentication module",
            agent_id="opc-worker-1",
            agent_name="Worker One",
            employee_id="emp-001",
            company_manual_path="/home/user/opc/manuals/company.md",
            employee_manual_path="/home/user/opc/manuals/employees/emp-001.md",
            task_manual_path="/home/user/opc/manuals/tasks/task-001.md",
            timeout=900,
            monthly_budget=1000.0,
            used_budget=300.0,
            remaining_budget=700.0,
        )

    def test_build_message_contains_absolute_paths(self, sample_task):
        """测试消息包含绝对路径"""
        caller = TaskCaller()
        message = caller._build_message(sample_task)

        # 检查包含绝对路径
        assert "/home/user/opc/manuals/company.md" in message
        assert "/home/user/opc/manuals/employees/emp-001.md" in message
        assert "/home/user/opc/manuals/tasks/task-001.md" in message

    def test_build_message_contains_report_format(self, sample_task):
        """测试消息包含报告格式说明"""
        caller = TaskCaller()
        message = caller._build_message(sample_task)

        # 检查包含 OPC-REPORT 格式说明
        assert "---OPC-REPORT---" in message
        assert "---END-REPORT---" in message
        assert "task_id: task-001" in message
        assert "completed|failed|needs_revision" in message

    def test_build_message_contains_task_info(self, sample_task):
        """测试消息包含任务信息"""
        caller = TaskCaller()
        message = caller._build_message(sample_task)

        assert "task-001" in message
        assert "Code Review" in message
        assert "Review the authentication module" in message
        assert "Worker One" in message

    def test_build_message_contains_budget_info(self, sample_task_with_budget):
        """测试消息包含预算信息"""
        caller = TaskCaller()
        message = caller._build_message(sample_task_with_budget)

        assert "预算信息" in message
        assert "1000.00 OC币" in message
        assert "300.00 OC币" in message
        assert "700.00 OC币" in message

    def test_build_message_no_budget(self, sample_task):
        """测试无预算信息的消息"""
        caller = TaskCaller()
        message = caller._build_message(sample_task)

        # 当预算为 0 时不显示预算部分
        assert "本月预算" not in message

    def test_to_absolute_path_already_absolute(self):
        """测试已经是绝对路径"""
        caller = TaskCaller()
        path = "/home/user/test.md"
        result = caller._to_absolute_path(path)
        assert result == "/home/user/test.md"

    def test_to_absolute_path_relative(self):
        """测试相对路径转绝对路径"""
        caller = TaskCaller()
        path = "manuals/test.md"
        result = caller._to_absolute_path(path)
        # 应该是当前工作目录 + 相对路径
        assert Path(result).is_absolute()
        assert "manuals/test.md" in result

    @pytest.mark.asyncio
    async def test_assign_task_success(self, sample_task, monkeypatch):
        """测试成功分配任务"""
        # Mock messenger
        mock_response = MessageResponse(
            success=True,
            content="Task accepted",
            session_key="sess-abc123",
            tokens_input=100,
            tokens_output=50,
        )

        async def mock_send(*args, **kwargs):
            return mock_response

        caller = TaskCaller()
        caller.messenger.send = mock_send

        result = await caller.assign_task(sample_task)

        assert result.success is True
        assert result.content == "Task accepted"
        assert result.session_key == "sess-abc123"
        assert result.tokens_input == 100
        assert result.tokens_output == 50

    @pytest.mark.asyncio
    async def test_assign_task_failure(self, sample_task):
        """测试任务分配失败"""
        async def mock_send(*args, **kwargs):
            return MessageResponse(
                success=False,
                error="Agent not found",
            )

        caller = TaskCaller()
        caller.messenger.send = mock_send

        result = await caller.assign_task(sample_task)

        assert result.success is False
        assert result.error == "Agent not found"

    @pytest.mark.asyncio
    async def test_assign_task_uses_correct_timeout(self, sample_task):
        """测试使用正确的超时时间"""
        received_timeout = None

        async def mock_send(agent_id, message, message_type, timeout):
            nonlocal received_timeout
            received_timeout = timeout
            return MessageResponse(success=True, content="OK")

        caller = TaskCaller()
        caller.messenger.send = mock_send

        await caller.assign_task(sample_task)

        assert received_timeout == 900  # 15分钟


class TestTaskAssignment:
    """TaskAssignment 数据类测试"""

    def test_default_timeout(self):
        """测试默认超时时间"""
        task = TaskAssignment(
            task_id="task-001",
            title="Test",
            description="Test task",
            agent_id="opc-worker-1",
            agent_name="Worker",
            employee_id="emp-001",
            company_manual_path="/path/to/company.md",
            employee_manual_path="/path/to/employee.md",
            task_manual_path="/path/to/task.md",
        )
        assert task.timeout == 900  # 默认 15 分钟

    def test_default_budget(self):
        """测试默认预算值"""
        task = TaskAssignment(
            task_id="task-001",
            title="Test",
            description="Test task",
            agent_id="opc-worker-1",
            agent_name="Worker",
            employee_id="emp-001",
            company_manual_path="/path/to/company.md",
            employee_manual_path="/path/to/employee.md",
            task_manual_path="/path/to/task.md",
        )
        assert task.monthly_budget == 0.0
        assert task.used_budget == 0.0
        assert task.remaining_budget == 0.0

    def test_custom_timeout(self):
        """测试自定义超时时间"""
        task = TaskAssignment(
            task_id="task-001",
            title="Test",
            description="Test task",
            agent_id="opc-worker-1",
            agent_name="Worker",
            employee_id="emp-001",
            company_manual_path="/path/to/company.md",
            employee_manual_path="/path/to/employee.md",
            task_manual_path="/path/to/task.md",
            timeout=1800,  # 30 分钟
        )
        assert task.timeout == 1800


class TestTaskResponse:
    """TaskResponse 数据类测试"""

    def test_total_tokens(self):
        """测试总 token 计算"""
        response = TaskResponse(
            success=True,
            content="Done",
            tokens_input=100,
            tokens_output=50,
        )
        assert response.total_tokens == 150

    def test_default_values(self):
        """测试默认值"""
        response = TaskResponse(success=True)
        assert response.content == ""
        assert response.session_key is None
        assert response.tokens_input == 0
        assert response.tokens_output == 0
        assert response.error is None
