#!/usr/bin/env python3
"""
Database migration: Add missing Task columns for v0.3.0-beta.

This migration adds columns required for:
- Task splitting (parent_task_id)
- Exact token tracking (actual_tokens_input/output, is_exact, session_key)
"""

import sqlite3
from pathlib import Path


def migrate_task_columns(db_path: str = "data/opc.db"):
    """
    Add missing columns to tasks table.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(tasks)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"Existing columns: {existing_columns}")
        
        # Columns to add
        columns_to_add = {
            "parent_task_id": "VARCHAR",
            "actual_tokens_input": "INTEGER DEFAULT 0",
            "actual_tokens_output": "INTEGER DEFAULT 0",
            "is_exact": "VARCHAR DEFAULT 'false'",
            "session_key": "VARCHAR",
        }
        
        added = []
        skipped = []
        
        for column, col_type in columns_to_add.items():
            if column not in existing_columns:
                print(f"Adding column: {column} ({col_type})")
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column} {col_type}")
                added.append(column)
            else:
                skipped.append(column)
        
        if skipped:
            print(f"Skipped (already exists): {skipped}")
        
        # Add foreign key constraint for parent_task_id (SQLite doesn't support adding FK via ALTER)
        # We need to recreate the table to add FK constraint, but for now the column is enough
        if "parent_task_id" in added:
            print("Note: parent_task_id column added. Foreign key constraint requires table rebuild.")
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(tasks)")
        final_columns = {row[1] for row in cursor.fetchall()}
        print(f"\nFinal columns: {final_columns}")
        
        print(f"\nMigration completed!")
        print(f"  Added: {len(added)} columns")
        print(f"  Skipped: {len(skipped)} columns")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def migrate_postgres(db_url: str = None):
    """
    Add missing columns to PostgreSQL tasks table.
    """
    import os
    
    if not db_url:
        db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("DATABASE_URL not set")
        return False
    
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks'
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        print(f"Existing columns: {existing_columns}")
        
        # Columns to add
        columns_to_add = [
            ("parent_task_id", "VARCHAR"),
            ("actual_tokens_input", "INTEGER DEFAULT 0"),
            ("actual_tokens_output", "INTEGER DEFAULT 0"),
            ("is_exact", "VARCHAR DEFAULT 'false'"),
            ("session_key", "VARCHAR"),
        ]
        
        added = []
        for column, col_type in columns_to_add:
            if column not in existing_columns:
                print(f"Adding column: {column}")
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {column} {col_type}")
                added.append(column)
        
        conn.commit()
        
        # Add foreign key if parent_task_id was added
        if "parent_task_id" in added:
            try:
                cursor.execute("""
                    ALTER TABLE tasks 
                    ADD CONSTRAINT fk_parent_task 
                    FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
                """)
                print("Added foreign key constraint for parent_task_id")
                conn.commit()
            except Exception as e:
                print(f"Note: Could not add FK constraint: {e}")
        
        print(f"\nPostgreSQL migration completed! Added {len(added)} columns")
        return True
        
    except ImportError:
        print("psycopg2 not installed, skipping PostgreSQL migration")
        return False
    except Exception as e:
        print(f"PostgreSQL migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    import sys
    
    # SQLite migration
    sqlite_ok = migrate_task_columns()
    
    # PostgreSQL migration (if available)
    postgres_ok = migrate_postgres()
    
    if sqlite_ok:
        print("\n✅ SQLite migration successful")
        sys.exit(0)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
