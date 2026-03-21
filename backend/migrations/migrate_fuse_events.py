"""
Database migration: Add budget fuse events and parent_task support.

This migration creates the budget_fuse_events table and adds parent_task_id to tasks.
"""

import sqlite3
from pathlib import Path


def migrate_fuse_events(db_path: str = "data/opc.db"):
    """
    Create budget_fuse_events table and add parent_task_id to tasks.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='budget_fuse_events'")
        if cursor.fetchone():
            print("Migration already applied (budget_fuse_events table exists)")
        else:
            print("Creating budget_fuse_events table...")
            
            cursor.execute("""
                CREATE TABLE budget_fuse_events (
                    id VARCHAR PRIMARY KEY,
                    agent_id VARCHAR NOT NULL,
                    task_id VARCHAR,
                    fuse_type VARCHAR NOT NULL,
                    threshold_percentage FLOAT NOT NULL,
                    budget_used FLOAT NOT NULL,
                    budget_total FLOAT NOT NULL,
                    status VARCHAR DEFAULT 'pending',
                    resolved_action VARCHAR,
                    resolved_by VARCHAR,
                    resolved_at TIMESTAMP,
                    resolution_note TEXT,
                    additional_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_fuse_events_agent ON budget_fuse_events(agent_id)")
            cursor.execute("CREATE INDEX idx_fuse_events_task ON budget_fuse_events(task_id)")
            cursor.execute("CREATE INDEX idx_fuse_events_status ON budget_fuse_events(status)")
            
            print("- Created budget_fuse_events table")
            print("- Created indexes: agent_id, task_id, status")
        
        # Check if parent_task_id column exists in tasks
        cursor.execute("PRAGMA table_info(tasks)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "parent_task_id" not in columns:
            print("Adding parent_task_id column to tasks table...")
            cursor.execute("""
                ALTER TABLE tasks 
                ADD COLUMN parent_task_id VARCHAR DEFAULT NULL
            """)
            print("- Added parent_task_id column")
        else:
            print("parent_task_id column already exists")
        
        # Check if 'split' is in status enum - SQLite doesn't have enums, but we need to handle this in code
        # Just verify the column exists
        if "status" in columns:
            print("Note: Task status 'split' should be handled in application code")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_fuse_events()
