"""
Database configuration and utilities.

Supports both SQLite (development) and PostgreSQL (production).
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
DB_PATH = os.getenv("OPC_DB_PATH", "./data/opc.db")


def get_database_url() -> str:
    """
    Get database URL based on configuration.
    
    Priority:
    1. DATABASE_URL environment variable (for production)
    2. DB_TYPE=postgresql with PG_HOST, PG_PORT, etc.
    3. DB_TYPE=sqlite (default, development)
    """
    # If DATABASE_URL is explicitly set, use it
    if DATABASE_URL:
        return DATABASE_URL
    
    # PostgreSQL configuration
    if DB_TYPE == "postgresql":
        pg_host = os.getenv("PG_HOST", "localhost")
        pg_port = os.getenv("PG_PORT", "5432")
        pg_user = os.getenv("PG_USER", "opc")
        pg_password = os.getenv("PG_PASSWORD", "opc_password")
        pg_db = os.getenv("PG_DATABASE", "openclaw_opc")
        
        return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
    
    # Default: SQLite
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"


def create_database_engine():
    """Create SQLAlchemy engine based on database type."""
    url = get_database_url()
    
    if url.startswith("sqlite"):
        # SQLite-specific configuration
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        # PostgreSQL configuration
        return create_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
        )


# Create engine
engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from src.models import agent, approval_request, async_message, budget, shared_memory, skill_growth, task, sub_task, task_dependency  # noqa: F401
    Base.metadata.create_all(bind=engine)


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database connection information.
    
    Returns:
        Dict with database type, URL (masked), and connection status
    """
    url = get_database_url()
    db_type = "postgresql" if url.startswith("postgresql") else "sqlite"
    
    # Mask password in URL for display
    masked_url = url
    if "@" in url and ":" in url.split("@")[0]:
        # postgresql://user:password@host -> postgresql://user:***@host
        parts = url.split("@")
        auth_part = parts[0].split(":")
        masked_url = f"{auth_part[0]}:***@{parts[1]}"
    
    return {
        "type": db_type,
        "url": masked_url,
        "connected": check_database_connection(),
    }
