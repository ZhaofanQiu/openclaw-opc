"""
opc-database: 测试工具函数

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import asyncio
import uuid
from typing import AsyncGenerator, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from opc_database.models import Employee, CompanyBudget, Task


async def create_test_employee(
    session: AsyncSession,
    name: str = "测试员工",
    emoji: str = "🤖",
    position_level: int = 2,
    monthly_budget: float = 1000.0,
    openclaw_agent_id: str = None
) -> Employee:
    """创建测试员工"""
    # 如果没有提供 agent_id，生成唯一的
    if openclaw_agent_id is None:
        openclaw_agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    employee = Employee(
        id=str(uuid.uuid4()),  # 手动生成 ID
        name=name,
        emoji=emoji,
        position_level=position_level,
        monthly_budget=monthly_budget,
        used_budget=0.0,
        # 注意：remaining_budget 是 @property，不需要设置
        status="idle",
        openclaw_agent_id=openclaw_agent_id
    )
    session.add(employee)
    await session.flush()
    await session.refresh(employee)
    return employee


async def create_test_company(
    session: AsyncSession,
    total_budget: float = 10000.0
) -> CompanyBudget:
    """创建测试公司"""
    company = CompanyBudget(
        id=str(uuid.uuid4()),  # 手动生成 ID
        total_budget=total_budget,
        used_budget=0.0
    )
    session.add(company)
    await session.flush()
    await session.refresh(company)
    return company


async def create_test_task(
    session: AsyncSession,
    title: str = "测试任务",
    description: str = "测试描述",
    priority: str = "normal",
    estimated_cost: float = 500.0,
    actual_cost: float = 0.0,
    assigned_to: str = None
) -> Task:
    """创建测试任务"""
    task = Task(
        id=str(uuid.uuid4()),  # 手动生成 ID
        title=title,
        description=description,
        priority=priority,
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
        status="pending",
        assigned_to=assigned_to
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)
    return task


def async_test(coro: Callable) -> Callable:
    """辅助装饰器，用于运行异步测试函数"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper
