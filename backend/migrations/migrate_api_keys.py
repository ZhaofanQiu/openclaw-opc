"""
Migration script to add API Key table for external access.
Run this to create the api_keys table.
"""

import os
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, MetaData, Table
from sqlalchemy import inspect as sa_inspect

# Database path
DB_PATH = os.getenv("OPC_DB_PATH", "./data/opc.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"


def migrate():
    """Create API key table."""
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    metadata = MetaData()
    
    # Check if table exists
    insp = sa_inspect(engine)
    
    if 'api_keys' in insp.get_table_names():
        print("api_keys table already exists")
        return
    
    # Create api_keys table
    api_keys = Table(
        'api_keys',
        metadata,
        Column('id', String, primary_key=True, index=True),
        Column('name', String, nullable=False),
        Column('key_hash', String, nullable=False, index=True),
        Column('key_prefix', String(8), nullable=False, index=True),
        Column('permissions', String, default="read"),
        Column('allowed_ips', String, nullable=True),
        Column('allowed_origins', String, nullable=True),
        Column('rate_limit_per_minute', Integer, nullable=True),
        Column('is_active', Boolean, default=True),
        Column('last_used_at', DateTime, nullable=True),
        Column('use_count', Integer, default=0),
        Column('expires_at', DateTime, nullable=True),
        Column('created_at', DateTime, nullable=True),
        Column('created_by', String, nullable=True),
    )
    
    metadata.create_all(engine)
    print("Migration completed successfully!")
    print("- api_keys table created")


if __name__ == "__main__":
    migrate()
