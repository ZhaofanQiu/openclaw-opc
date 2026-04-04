"""
opc-core: 测试工具函数

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from typing import Dict, Any, Optional
from unittest.mock import AsyncMock



def create_mock_db_session():
    """创建 Mock 数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    return session


def create_mock_employee(
    id: str = "emp_test123",
    name: str = "测试员工",
    emoji: str = "🤖",
    position_level: int = 2,
    monthly_budget: float = 1000.0,
    used_budget: float = 0.0,
    status: str = "idle",
    openclaw_agent_id: str = "agent_test"
) -> Dict[str, Any]:
    """创建 Mock 员工数据"""
    return {
        "id": id,
        "name": name,
        "emoji": emoji,
        "position_level": position_level,
        "monthly_budget": monthly_budget,
        "used_budget": used_budget,
        "remaining_budget": monthly_budget - used_budget,
        "status": status,
        "openclaw_agent_id": openclaw_agent_id,
        "created_at": "2024-03-24T10:00:00",
        "updated_at": "2024-03-24T10:00:00"
    }


def create_mock_task(
    id: str = "task_test456",
    title: str = "测试任务",
    description: str = "测试描述",
    priority: str = "normal",
    status: str = "pending",
    estimated_cost: float = 500.0,
    actual_cost: float = 0.0,
    assigned_to: Optional[str] = None
) -> Dict[str, Any]:
    """创建 Mock 任务数据"""
    return {
        "id": id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "estimated_cost": estimated_cost,
        "actual_cost": actual_cost,
        "assigned_to": assigned_to,
        "created_at": "2024-03-24T10:00:00",
        "updated_at": "2024-03-24T10:00:00"
    }


def create_mock_budget(
    total_budget: float = 10000.0,
    used_budget: float = 2000.0
) -> Dict[str, Any]:
    """创建 Mock 预算数据"""
    return {
        "total_budget": total_budget,
        "used_budget": used_budget,
        "remaining_budget": total_budget - used_budget,
        "usage_percentage": (used_budget / total_budget) * 100 if total_budget > 0 else 0
    }


class MockRepository:
    """Mock Repository 基类"""
    
    def __init__(self, data=None):
        self.data = data or []
        self._id_counter = 1
    
    async def get_by_id(self, id: str):
        for item in self.data:
            if getattr(item, 'id', None) == id:
                return item
        return None
    
    async def get_all(self, skip: int = 0, limit: int = 100):
        return self.data[skip:skip + limit]
    
    async def create(self, obj):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = f"mock_{self._id_counter}"
            self._id_counter += 1
        self.data.append(obj)
        return obj
    
    async def update(self, id: str, **kwargs):
        obj = await self.get_by_id(id)
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
        return obj
    
    async def delete(self, id: str):
        obj = await self.get_by_id(id)
        if obj:
            self.data.remove(obj)
        return obj
