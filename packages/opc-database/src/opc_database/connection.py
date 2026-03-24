"""
opc-database: 数据库连接管理

提供异步数据库连接和会话管理

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from .models import Base


# 数据库配置
DEFAULT_DB_PATH = "./data/opc.db"
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_database_url() -> str:
    """
    获取数据库URL
    
    优先级:
    1. DATABASE_URL 环境变量
    2. PostgreSQL 配置
    3. SQLite (默认)
    
    Returns:
        数据库连接URL
    """
    if DATABASE_URL:
        return DATABASE_URL
    
    if DB_TYPE == "postgresql":
        pg_host = os.getenv("PG_HOST", "localhost")
        pg_port = os.getenv("PG_PORT", "5432")
        pg_user = os.getenv("PG_USER", "opc")
        pg_password = os.getenv("PG_PASSWORD", "opc_password")
        pg_db = os.getenv("PG_DATABASE", "openclaw_opc")
        return f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    
    # SQLite (默认)
    db_path = os.getenv("OPC_DB_PATH", DEFAULT_DB_PATH)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


def create_engine():
    """
    创建异步数据库引擎
    
    Returns:
        异步SQLAlchemy引擎
    """
    url = get_database_url()
    
    if "sqlite" in url:
        # SQLite 配置
        return create_async_engine(
            url,
            echo=False,
            poolclass=NullPool,  # SQLite不需要连接池
        )
    else:
        # PostgreSQL 配置
        return create_async_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )


# 全局引擎实例
_engine = None


def get_engine():
    """获取或创建引擎（单例）"""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂"""
    engine = get_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（异步上下文管理器）
    
    使用示例:
        async with get_session() as session:
            repo = EmployeeRepository(session)
            employee = await repo.get_by_id("emp_xxx")
    
    Yields:
        异步数据库会话
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库表
    
    创建所有定义的表结构
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_connection() -> bool:
    """
    检查数据库连接是否正常
    
    Returns:
        连接成功返回True，否则False
    """
    try:
        engine = get_engine()
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


async def close_db():
    """关闭数据库连接"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
