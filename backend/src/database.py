"""
Database configuration and utilities.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database path
DB_PATH = os.getenv("OPC_DB_PATH", "./data/opc.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# SQLAlchemy setup
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)
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
    from src.models import agent, budget, task  # noqa: F401
    Base.metadata.create_all(bind=engine)
