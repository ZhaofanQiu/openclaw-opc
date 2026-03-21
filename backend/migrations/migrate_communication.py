"""
Database migration: Add agent communication table.

This migration creates the agent_messages table for inter-agent messaging.
"""

import sqlite3
from pathlib import Path


def migrate_communication(db_path: str = "data/opc.db"):
    """
    Create agent_messages table.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_messages'")
        if cursor.fetchone():
            print("Migration already applied (agent_messages table exists)")
        else:
            print("Creating agent_messages table...")
            
            cursor.execute("""
                CREATE TABLE agent_messages (
                    id VARCHAR PRIMARY KEY,
                    sender_id VARCHAR NOT NULL,
                    recipient_id VARCHAR NOT NULL,
                    subject VARCHAR,
                    content TEXT NOT NULL,
                    priority VARCHAR DEFAULT 'normal',
                    status VARCHAR DEFAULT 'pending',
                    related_task_id VARCHAR,
                    related_type VARCHAR,
                    sent_at TIMESTAMP,
                    delivered_at TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_messages_sender ON agent_messages(sender_id)")
            cursor.execute("CREATE INDEX idx_messages_recipient ON agent_messages(recipient_id)")
            cursor.execute("CREATE INDEX idx_messages_status ON agent_messages(status)")
            cursor.execute("CREATE INDEX idx_messages_created ON agent_messages(created_at)")
            
            print("- Created agent_messages table")
            print("- Created indexes: sender_id, recipient_id, status, created_at")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_communication()
