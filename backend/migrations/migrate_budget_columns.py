#!/usr/bin/env python3
"""
Database migration: Add missing BudgetTransaction columns for v0.3.0-beta.

Adds columns for exact token tracking.
"""

import sqlite3
from pathlib import Path


def migrate_budget_transaction_columns(db_path: str = "data/opc.db"):
    """
    Add missing columns to budget_transactions table.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(budget_transactions)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"Existing columns: {existing_columns}")
        
        # Columns to add
        columns_to_add = {
            "actual_tokens_input": "INTEGER DEFAULT 0",
            "actual_tokens_output": "INTEGER DEFAULT 0",
            "is_exact": "VARCHAR DEFAULT 'false'",
            "session_key": "VARCHAR",
        }
        
        added = []
        for column, col_type in columns_to_add.items():
            if column not in existing_columns:
                print(f"Adding column: {column} ({col_type})")
                cursor.execute(f"ALTER TABLE budget_transactions ADD COLUMN {column} {col_type}")
                added.append(column)
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(budget_transactions)")
        final_columns = {row[1] for row in cursor.fetchall()}
        print(f"\nFinal columns: {final_columns}")
        
        print(f"\nMigration completed! Added {len(added)} columns")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate_budget_transaction_columns()
    exit(0 if success else 1)
