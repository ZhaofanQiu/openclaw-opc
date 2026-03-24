"""
opc-database: 测试配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from opc_database.models import Base


# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """创建测试数据库引擎（内存模式）"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,  # 禁用连接池，适合测试
        echo=False  # 设置为True可查看SQL日志
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 清理
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """提供数据库会话（每个测试独立）"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        # 回滚所有更改
        await session.rollback()


@pytest.fixture
def sample_employee_data():
    """示例员工数据"""
    return {
        "name": "测试员工",
        "emoji": "🤖",
        "position_level": 2,
        "monthly_budget": 1000.0,
        "used_budget": 0.0,
        "status": "idle",
        "openclaw_agent_id": "agent_test123"
    }


@pytest.fixture
def sample_company_data():
    """示例公司数据"""
    return {
        "name": "测试公司",
        "total_budget": 10000.0,
        "used_budget": 0.0
    }


@pytest.fixture
def sample_task_data():
    """示例任务数据"""
    return {
        "title": "测试任务",
        "description": "这是一个测试任务",
        "priority": "normal",
        "estimated_cost": 500.0,
        "actual_cost": 0.0,
        "status": "pending"
    }
