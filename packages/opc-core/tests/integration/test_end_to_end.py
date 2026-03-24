import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import httpx
from unittest.mock import AsyncMock, MagicMock
import respx

from opc_database.models import Base, Employee, Task, AgentStatus as EmployeeStatus
from opc_database.repositories import EmployeeRepository, TaskRepository
from opc_openclaw.client import AgentClient, SessionClient


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


class TestDatabaseIntegration:
    """数据库集成测试 - Repository 协同工作"""
    
    @pytest.mark.asyncio
    async def test_employee_task_relationship(self, db_session):
        """测试员工和任务的关联关系"""
        emp_repo = EmployeeRepository(db_session)
        task_repo = TaskRepository(db_session)
        
        # 创建员工 - 使用模型实例
        employee = Employee(
            id="emp_001",
            name="测试员工",
            emoji="🤖",
            openclaw_agent_id="agent_001",
            status=EmployeeStatus.IDLE
        )
        await emp_repo.create(employee)
        
        # 创建任务 - 使用模型实例
        task = Task(
            id="task_001",
            title="测试任务",
            description="描述",
            status="pending"
        )
        await task_repo.create(task)
        
        # 分配任务给员工
        await task_repo.assign_task("task_001", "emp_001")
        
        # 更新员工状态
        await emp_repo.update_status("emp_001", EmployeeStatus.WORKING)
        
        # 验证关联
        updated_task = await task_repo.get_by_id("task_001")
        assert updated_task.assigned_to == "emp_001"
        assert updated_task.status == "assigned"
        
        updated_emp = await emp_repo.get_by_id("emp_001")
        assert updated_emp.status == EmployeeStatus.WORKING
    
    @pytest.mark.asyncio
    async def test_task_lifecycle_with_employee(self, db_session):
        """测试任务完整生命周期中员工状态变化"""
        emp_repo = EmployeeRepository(db_session)
        task_repo = TaskRepository(db_session)
        
        # 创建员工和任务
        employee = Employee(
            id="emp_002",
            name="员工2",
            emoji="🤖",
            status=EmployeeStatus.IDLE
        )
        await emp_repo.create(employee)
        
        task = Task(
            id="task_002",
            title="生命周期测试任务",
            status="pending"
        )
        await task_repo.create(task)
        
        # 1. 分配任务
        await task_repo.assign_task("task_002", "emp_002")
        await emp_repo.update_status("emp_002", EmployeeStatus.WORKING, current_task_id="task_002")
        
        # 2. 开始任务
        await task_repo.start_task("task_002")
        
        # 3. 完成任务
        await task_repo.complete_task("task_002", result="完成结果")
        await emp_repo.increment_completed_tasks("emp_002")
        await emp_repo.update_status("emp_002", EmployeeStatus.IDLE, current_task_id=None)
        
        # 验证最终状态
        task = await task_repo.get_by_id("task_002")
        emp = await emp_repo.get_by_id("emp_002")
        
        assert task.status == "completed"
        assert task.result == "完成结果"
        assert emp.status == EmployeeStatus.IDLE
        assert emp.completed_tasks == 1
        assert emp.current_task_id is None


class TestOpenClawIntegration:
    """OpenClaw 客户端集成测试"""
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_agent_session_workflow(self):
        """测试 Agent 获取到会话发送的完整流程"""
        base_url = "http://localhost:8080"
        
        # Mock 获取 Agent
        respx.get(f"{base_url}/api/agents/agent_123").mock(
            return_value=httpx.Response(200, json={
                "id": "agent_123",
                "name": "TestAgent",
                "status": "online"
            })
        )
        
        # Mock 获取 Agent 状态
        respx.get(f"{base_url}/api/agents/agent_123/status").mock(
            return_value=httpx.Response(200, json={
                "agent_id": "agent_123",
                "status": "online",
                "active_sessions": 0
            })
        )
        
        # Mock 创建 Session
        respx.post(f"{base_url}/api/sessions/spawn").mock(
            return_value=httpx.Response(200, json={
                "session_id": "sess_456",
                "status": "active"
            })
        )
        
        # Mock 发送消息
        respx.post(f"{base_url}/api/sessions/sess_456/send").mock(
            return_value=httpx.Response(200, json={
                "message_id": "msg_789",
                "status": "delivered"
            })
        )
        
        # 执行流程
        agent_client = AgentClient(base_url, api_key="test_key")
        session_client = SessionClient(base_url, api_key="test_key")
        
        # 1. 获取 Agent
        agent = await agent_client.get_agent("agent_123")
        assert agent is not None
        assert agent["id"] == "agent_123"
        
        # 2. 检查状态
        status = await agent_client.get_agent_status("agent_123")
        assert status["status"] == "online"
        
        # 3. 创建 Session
        session = await session_client.spawn_session("agent_123", "测试任务")
        assert session["session_id"] == "sess_456"
        
        # 4. 发送消息
        result = await session_client.send_message("sess_456", "Hello")
        assert result["status"] == "delivered"
    
    @respx.mock
    @pytest.mark.asyncio
    async def test_agent_health_check(self):
        """测试 Agent 健康检查"""
        base_url = "http://localhost:8080"
        
        # Mock 在线 Agent
        respx.get(f"{base_url}/api/agents/online_agent/status").mock(
            return_value=httpx.Response(200, json={
                "agent_id": "online_agent",
                "status": "online",
                "active_sessions": 1
            })
        )
        
        # Mock 离线 Agent
        respx.get(f"{base_url}/api/agents/offline_agent/status").mock(
            return_value=httpx.Response(200, json={
                "agent_id": "offline_agent",
                "status": "offline",
                "active_sessions": 0
            })
        )
        
        agent_client = AgentClient(base_url)
        
        # 在线 Agent 应该返回 True
        assert await agent_client.check_agent_health("online_agent") is True
        
        # 离线 Agent 应该返回 False
        assert await agent_client.check_agent_health("offline_agent") is False


class TestEndToEndWorkflow:
    """端到端工作流测试"""
    
    @pytest.mark.asyncio
    async def test_create_assign_execute_task(self, db_session):
        """
        完整流程测试:
        1. 创建员工
        2. 创建任务
        3. 分配任务
        4. 模拟执行
        5. 完成任务
        """
        emp_repo = EmployeeRepository(db_session)
        task_repo = TaskRepository(db_session)
        
        # 步骤 1: 创建员工
        employee = Employee(
            id="emp_e2e",
            name="E2E测试员工",
            emoji="🚀",
            openclaw_agent_id="agent_e2e",
            status=EmployeeStatus.IDLE,
            monthly_budget=1000.0
        )
        await emp_repo.create(employee)
        assert employee.id == "emp_e2e"
        
        # 步骤 2: 创建任务
        task = Task(
            id="task_e2e",
            title="E2E测试任务",
            description="这是一个完整的端到端测试",
            estimated_cost=500.0,
            priority="high",
            status="pending"
        )
        await task_repo.create(task)
        assert task.id == "task_e2e"
        assert task.status == "pending"
        
        # 步骤 3: 分配任务
        await task_repo.assign_task("task_e2e", "emp_e2e")
        await emp_repo.update_status("emp_e2e", EmployeeStatus.WORKING, current_task_id="task_e2e")
        
        task = await task_repo.get_by_id("task_e2e")
        assert task.status == "assigned"
        assert task.assigned_to == "emp_e2e"
        
        # 步骤 4: 开始执行
        await task_repo.start_task("task_e2e")
        task = await task_repo.get_by_id("task_e2e")
        assert task.status == "in_progress"
        
        # 步骤 5: 完成任务
        await task_repo.complete_task(
            "task_e2e",
            result="任务执行成功！",
            actual_cost=450.0
        )
        await emp_repo.increment_completed_tasks("emp_e2e")
        await emp_repo.update_status("emp_e2e", EmployeeStatus.IDLE, current_task_id=None)
        
        # 最终验证
        final_task = await task_repo.get_by_id("task_e2e")
        final_emp = await emp_repo.get_by_id("emp_e2e")
        
        assert final_task.status == "completed"
        assert final_task.result == "任务执行成功！"
        assert final_task.actual_cost == 450.0
        assert final_emp.status == EmployeeStatus.IDLE
        assert final_emp.completed_tasks == 1
        assert final_emp.current_task_id is None
