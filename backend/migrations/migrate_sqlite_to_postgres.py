#!/usr/bin/env python3
"""
Database Migration Script: SQLite → PostgreSQL

Usage:
    python migrations/migrate_sqlite_to_postgres.py --source ./data/opc.db --target postgresql://user:pass@localhost:5432/opc

Requirements:
    pip install psycopg2-binary sqlalchemy
"""

import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def get_sqlite_tables(engine):
    """Get list of tables from SQLite database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        return [row[0] for row in result]


def get_table_columns(engine, table_name):
    """Get column info for a table."""
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        return [
            {
                "name": row[1],
                "type": row[2],
                "nullable": not row[3],
                "default": row[4],
            }
            for row in result
        ]


def migrate_table(source_engine, target_engine, table_name):
    """Migrate data from one table."""
    print(f"Migrating table: {table_name}...")
    
    # Get data from source
    with source_engine.connect() as source_conn:
        result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        columns = result.keys()
    
    if not rows:
        print(f"  - No data in {table_name}")
        return 0
    
    # Insert into target
    with target_engine.connect() as target_conn:
        # Build insert statement
        column_str = ", ".join(columns)
        placeholder_str = ", ".join([f":{col}" for col in columns])
        
        insert_stmt = text(f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholder_str})")
        
        # Convert rows to dicts
        row_dicts = [dict(zip(columns, row)) for row in rows]
        
        # Handle PostgreSQL-specific type conversions
        for row in row_dicts:
            for key, value in row.items():
                # Convert SQLite booleans (0/1) to Python booleans for PostgreSQL
                if isinstance(value, int) and key in ["is_online", "is_bound", "is_active", "is_overdue", "is_exact"]:
                    row[key] = bool(value)
        
        # Execute inserts
        target_conn.execute(insert_stmt, row_dicts)
        target_conn.commit()
    
    print(f"  - Migrated {len(rows)} rows")
    return len(rows)


def check_target_empty(target_engine):
    """Check if target database is empty (no tables)."""
    with target_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public'
        """))
        count = result.scalar()
        return count == 0


def create_tables_in_target(target_engine):
    """Create tables in target database using SQLAlchemy models."""
    print("Creating tables in target database...")
    
    from database import Base
    
    # Import all models to register them with Base
    from models import agent, budget, config, notification, share, skill, task
    
    Base.metadata.create_all(bind=target_engine)
    print("  - Tables created")


def migrate_data(source_url: str, target_url: str, skip_confirm: bool = False):
    """
    Migrate data from SQLite to PostgreSQL.
    
    Args:
        source_url: SQLite database URL
        target_url: PostgreSQL database URL
        skip_confirm: Skip confirmation prompt
    """
    # Create engines
    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)
    
    # Test connections
    print("Testing database connections...")
    try:
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  - Source (SQLite): OK")
    except Exception as e:
        print(f"  - Source (SQLite): FAILED - {e}")
        return False
    
    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  - Target (PostgreSQL): OK")
    except Exception as e:
        print(f"  - Target (PostgreSQL): FAILED - {e}")
        return False
    
    # Check if target has tables
    if not check_target_empty(target_engine):
        if not skip_confirm:
            response = input("Target database has existing tables. Continue? (yes/no): ")
            if response.lower() != "yes":
                print("Migration cancelled")
                return False
    
    # Create tables in target
    create_tables_in_target(target_engine)
    
    # Get list of tables from source
    tables = get_sqlite_tables(source_engine)
    print(f"\nFound {len(tables)} tables: {', '.join(tables)}")
    
    # Migrate each table
    total_rows = 0
    for table in tables:
        try:
            rows = migrate_table(source_engine, target_engine, table)
            total_rows += rows
        except Exception as e:
            print(f"  - ERROR migrating {table}: {e}")
            if not skip_confirm:
                response = input("Continue with remaining tables? (yes/no): ")
                if response.lower() != "yes":
                    return False
    
    print(f"\nMigration complete! Total rows migrated: {total_rows}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate OpenClaw OPC database from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--source",
        default="./data/opc.db",
        help="Source SQLite database path (default: ./data/opc.db)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target PostgreSQL URL (e.g., postgresql://user:pass@localhost:5432/opc)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompts",
    )
    
    args = parser.parse_args()
    
    # Build source URL
    source_url = f"sqlite:///{args.source}"
    
    print("=" * 60)
    print("OpenClaw OPC Database Migration")
    print("SQLite → PostgreSQL")
    print("=" * 60)
    print(f"Source: {source_url}")
    print(f"Target: {args.target}")
    print("=" * 60)
    
    if not args.yes:
        response = input("\nStart migration? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled")
            return
    
    success = migrate_data(source_url, args.target, skip_confirm=args.yes)
    
    if success:
        print("\n✅ Migration successful!")
        print("\nNext steps:")
        print("1. Update your .env file: DB_TYPE=postgresql")
        print("2. Set PostgreSQL connection parameters")
        print("3. Restart the application")
    else:
        print("\n❌ Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
