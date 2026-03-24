"""
opc-database: 测试工具函数

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import asyncio
from typing import AsyncGenerator, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from opc_database.models import Employee, Company, Task


async def create_test_employee(
    session: AsyncSession,
    name: str = "测试员工",
    emoji: str = "🤖",
    position_level: int = 2,
    monthly_budget: float = 1000.0,
    openclaw_agent_id: str = "agent_test"
) -> Employee:
    """创建测试员工"""
    employee = Employee(
        name=name,
        emoji=emoji,
        position_level=position_level,
        monthly_budget=monthly_budget,
        used_budget=0.0,
        remaining_budget=monthly_budget,
        status="idle",
        openclaw_agent_id=openclaw_agent_id
    )
    session.add(employee)
    await session.commit()
    await session.refresh(employee)
    return employee


async def create_test_company(
    session: AsyncSession,
    name: str = "测试公司",
    total_budget: float = 10000.0
) -> Company:
    """创建测试公司"""
    company = Company(
        name=name,
        total_budget=total_budget,
        used_budget=0.0,
        remaining_budget=total_budget
    )
    session.add(company)
    await session.commit()
    await session.refresh(company)
    return company


async def create_test_task(
    session: AsyncSession,
    title: str = "测试任务",
    description: str = "测试描述",
    priority: str = "normal",
    estimated_cost: float = 500.0,
    employee_id: str = None
) -> Task:
    """创建测试任务"""
    task = Task(
        title=title,
        description=description,
        priority=priority,
        estimated_cost=estimated_cost,
        actual_cost=0.0,
        status="pending",
        assigned_to=employee_id
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


def async_test(coro: Callable) -> Callable:
    """辅助装饰器，用于运行异步测试函数"""
    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))
    return wrapper
