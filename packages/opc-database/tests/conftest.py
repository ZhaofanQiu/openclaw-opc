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
# 添加tests目录到路径（用于导入utils）
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from opc_database.models import Base


# 使用文件数据库进行测试（避免内存数据库连接问题）
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """
    提供数据库会话（每个测试独立，使用新数据库）
    """
    # 创建引擎
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    session = async_session()
    yield session
    
    # 清理
    await session.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


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
