"""
Database migration: Add exact token tracking support.

This migration adds fields for actual token consumption tracking:
- actual_tokens_input: Actual input tokens consumed
- actual_tokens_output: Actual output tokens consumed
- is_exact: Whether values are exact (True) or estimated (False)
- session_key: Associated OpenClaw session identifier

Run this after updating the BudgetTransaction model.
"""

import sqlite3
from pathlib import Path


def migrate_exact_token_tracking(db_path: str = "data/opc.db"):
    """
    Migration steps:
    1. Add new columns to budget_transactions table
    2. Set is_exact=false for existing records (they're estimates)
    3. Update task model to track session_key
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if migration already applied
        cursor.execute("PRAGMA table_info(budget_transactions)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "actual_tokens_input" in columns:
            print("Migration already applied (actual_tokens_input column exists)")
            conn.close()
            return
        
        print("Starting exact token tracking migration...")
        
        # 1. Add new columns to budget_transactions
        cursor.execute("""
            ALTER TABLE budget_transactions 
            ADD COLUMN actual_tokens_input INTEGER DEFAULT 0
        """)
        
        cursor.execute("""
            ALTER TABLE budget_transactions 
            ADD COLUMN actual_tokens_output INTEGER DEFAULT 0
        """)
        
        cursor.execute("""
            ALTER TABLE budget_transactions 
            ADD COLUMN is_exact VARCHAR DEFAULT 'false'
        """)
        
        cursor.execute("""
            ALTER TABLE budget_transactions 
            ADD COLUMN session_key VARCHAR DEFAULT NULL
        """)
        
        # 2. Mark existing records as estimated (not exact)
        cursor.execute("""
            UPDATE budget_transactions 
            SET is_exact = 'false' 
            WHERE is_exact = 'false' OR is_exact IS NULL
        """)
        
        # 3. Add session_key to tasks table for tracking
        cursor.execute("PRAGMA table_info(tasks)")
        task_columns = {row[1] for row in cursor.fetchall()}
        
        if "session_key" not in task_columns:
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN session_key VARCHAR DEFAULT NULL
            """)
            print("- Added session_key column to tasks table")
        
        # 4. Add token tracking fields to tasks table
        if "actual_tokens_input" not in task_columns:
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN actual_tokens_input INTEGER DEFAULT 0
            """)
            print("- Added actual_tokens_input column to tasks table")
        
        if "actual_tokens_output" not in task_columns:
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN actual_tokens_output INTEGER DEFAULT 0
            """)
            print("- Added actual_tokens_output column to tasks table")
        
        if "is_exact" not in task_columns:
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN is_exact VARCHAR DEFAULT 'false'
            """)
            print("- Added is_exact column to tasks table")
        
        conn.commit()
        print("Migration completed successfully!")
        print("- Added actual_tokens_input to budget_transactions")
        print("- Added actual_tokens_output to budget_transactions")
        print("- Added is_exact flag to budget_transactions")
        print("- Added session_key to budget_transactions")
        print("- Added token tracking fields to tasks table")
        print("- Existing records marked as estimated (is_exact='false')")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


def rollback_migration(db_path: str = "data/opc.db"):
    """
    Rollback the exact token tracking migration.
    Note: SQLite doesn't support DROP COLUMN, so we need to recreate tables.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("Starting rollback...")
        
        # For SQLite, we need to recreate tables without the new columns
        # This is a simplified rollback - in production, you'd want to be more careful
        
        # Check if we have the new columns
        cursor.execute("PRAGMA table_info(budget_transactions)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "actual_tokens_input" not in columns:
            print("Migration was not applied (no new columns found)")
            conn.close()
            return
        
        # Note: SQLite doesn't support DROP COLUMN directly
        # In a real scenario, we'd recreate the table
        print("WARNING: SQLite doesn't support DROP COLUMN")
        print("To rollback, you would need to:")
        print("1. Create new table without the new columns")
        print("2. Copy data from old table")
        print("3. Drop old table")
        print("4. Rename new table")
        print("\nRollback not implemented for safety - please do this manually if needed.")
        
    except Exception as e:
        print(f"Rollback failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration()
    else:
        migrate_exact_token_tracking()
