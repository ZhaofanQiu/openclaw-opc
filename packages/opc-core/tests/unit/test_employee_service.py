"""
Employee Service 测试

使用 Mock Repository 测试业务逻辑

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from opc_core.services.employee_service import EmployeeService
from opc_database.models import AgentStatus


@pytest.fixture
def mock_repo():
    """Mock Repository"""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.get_available_for_task = AsyncMock(return_value=[])
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo):
    """Employee Service 实例"""
    return EmployeeService(mock_repo)


class TestEmployeeService:
    """Employee Service 测试类"""
    
    @pytest.mark.asyncio
    async def test_can_accept_task_budget_ok(self, service, mock_repo):
        """测试可以接受任务（预算充足）"""
        mock_emp = MagicMock()
        mock_emp.can_accept_task.return_value = True
        mock_repo.get_by_id.return_value = mock_emp
        
        result = await service.can_accept_task("emp_123", 500.0)
        
        assert result is True
        mock_emp.can_accept_task.assert_called_once_with(500.0)
    
    @pytest.mark.asyncio
    async def test_can_accept_task_budget_insufficient(self, service, mock_repo):
        """测试不能接受任务（预算不足）"""
        mock_emp = MagicMock()
        mock_emp.can_accept_task.return_value = False
        mock_repo.get_by_id.return_value = mock_emp
        
        result = await service.can_accept_task("emp_123", 2000.0)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_can_accept_task_employee_not_found(self, service, mock_repo):
        """测试不能接受任务（员工不存在）"""
        mock_repo.get_by_id.return_value = None
        
        result = await service.can_accept_task("nonexistent", 500.0)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_available_employees(self, service, mock_repo):
        """测试获取可用员工列表"""
        mock_emp1 = MagicMock()
        mock_emp2 = MagicMock()
        mock_repo.get_available_for_task.return_value = [mock_emp1, mock_emp2]
        
        result = await service.get_available_employees(estimated_cost=500.0)
        
        assert len(result) == 2
        mock_repo.get_available_for_task.assert_called_once_with(500.0)
    
    @pytest.mark.asyncio
    async def test_get_available_employees_empty(self, service, mock_repo):
        """测试获取可用员工列表（空）"""
        mock_repo.get_available_for_task.return_value = []
        
        result = await service.get_available_employees(estimated_cost=10000.0)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_release_from_task(self, service, mock_repo):
        """测试释放员工从任务"""
        await service.release_from_task("emp_123")
        
        mock_repo.update_status.assert_called_once()
        # 验证调用了正确的状态
        call_args = mock_repo.update_status.call_args
        assert call_args[0][0] == "emp_123"
        assert call_args[0][1] == AgentStatus.IDLE
