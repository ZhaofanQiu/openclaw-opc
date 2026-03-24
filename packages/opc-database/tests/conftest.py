"""
opc-database: 测试配置

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import os
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 测试数据库配置
os.environ["DB_TYPE"] = "sqlite"
os.environ["OPC_DB_PATH"] = "./data/test_opc.db"

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from opc_database import init_db, get_session


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """创建测试数据库引擎"""
    # 确保测试数据库目录存在
    Path("./data").mkdir(parents=True, exist_ok=True)
    
    # 删除旧的测试数据库
    test_db = Path("./data/test_opc.db")
    if test_db.exists():
        test_db.unlink()
    
    # 初始化数据库
    await init_db()
    
    yield
    
    # 清理
    if test_db.exists():
        test_db.unlink()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """提供数据库会话"""
    async with get_session() as session:
        yield session
