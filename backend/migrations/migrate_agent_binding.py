"""
Database migration: Add agent binding support.

This migration makes agent_id optional and adds is_bound field.
Run this after updating the Agent model.
"""

import sqlite3
from pathlib import Path


def migrate_agent_binding(db_path: str = "data/opc.db"):
    """
    Migration steps:
    1. Create new agents table with nullable agent_id
    2. Copy data from old table
    3. Set is_bound = "true" for existing agents
    4. Drop old table, rename new table
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if migration already applied
        cursor.execute("PRAGMA table_info(agents)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if "is_bound" in columns:
            print("Migration already applied (is_bound column exists)")
            conn.close()
            return
        
        print("Starting migration...")
        
        # 1. Create new table with updated schema
        cursor.execute("""
            CREATE TABLE agents_new (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                emoji VARCHAR DEFAULT '🧑‍💻',
                position_level INTEGER DEFAULT 1,
                position_title VARCHAR DEFAULT '实习生',
                agent_id VARCHAR UNIQUE,
                is_bound VARCHAR DEFAULT 'false',
                monthly_budget FLOAT DEFAULT 2000.0,
                used_budget FLOAT DEFAULT 0.0,
                status VARCHAR DEFAULT 'idle',
                current_task_id VARCHAR,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                completed_tasks INTEGER DEFAULT 0,
                soul_md TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_heartbeat TIMESTAMP,
                is_online VARCHAR DEFAULT 'unknown'
            )
        """)
        
        # 2. Copy data from old table
        cursor.execute("""
            INSERT INTO agents_new (
                id, name, emoji, position_level, position_title,
                agent_id, monthly_budget, used_budget, status,
                current_task_id, level, xp, completed_tasks, soul_md,
                created_at, updated_at, last_heartbeat, is_online
            )
            SELECT 
                id, name, emoji, position_level, position_title,
                agent_id, monthly_budget, used_budget, status,
                current_task_id, level, xp, completed_tasks, soul_md,
                created_at, updated_at, last_heartbeat, is_online
            FROM agents
        """)
        
        # 3. Set is_bound = "true" for existing agents (they already have agent_id)
        cursor.execute("UPDATE agents_new SET is_bound = 'true' WHERE agent_id IS NOT NULL")
        
        # 4. Drop old table and rename
        cursor.execute("DROP TABLE agents")
        cursor.execute("ALTER TABLE agents_new RENAME TO agents")
        
        conn.commit()
        print("Migration completed successfully!")
        print("- agent_id is now nullable")
        print("- is_bound column added")
        print("- Existing agents marked as bound")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_agent_binding()
