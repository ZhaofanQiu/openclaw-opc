"""
Database migration: Add employee avatars table.

This migration creates the employee_avatars table for avatar storage.
"""

import sqlite3
from pathlib import Path


def migrate_avatars(db_path: str = "data/opc.db"):
    """
    Create employee_avatars table.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employee_avatars'")
        if cursor.fetchone():
            print("Migration already applied (employee_avatars table exists)")
        else:
            print("Creating employee_avatars table...")
            
            cursor.execute("""
                CREATE TABLE employee_avatars (
                    id VARCHAR PRIMARY KEY,
                    agent_id VARCHAR NOT NULL UNIQUE,
                    source VARCHAR DEFAULT 'system',
                    storage_path VARCHAR,
                    external_url VARCHAR,
                    style_params TEXT,
                    generation_prompt TEXT,
                    skill_used VARCHAR,
                    original_filename VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index
            cursor.execute("CREATE INDEX idx_avatars_agent ON employee_avatars(agent_id)")
            
            print("- Created employee_avatars table")
            print("- Created index: agent_id")
        
        # Create avatars directory
        avatars_dir = db_path.parent / "avatars"
        avatars_dir.mkdir(exist_ok=True)
        print(f"- Created avatars directory: {avatars_dir}")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_avatars()
