"""
Database migration: Add share_links table for external access.

This migration creates the share_links table for JWT-signed share links.
"""

import sqlite3
from pathlib import Path


def migrate_share_links(db_path: str = "data/opc.db"):
    """
    Create share_links table.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='share_links'")
        if cursor.fetchone():
            print("Migration already applied (share_links table exists)")
            conn.close()
            return
        
        print("Creating share_links table...")
        
        cursor.execute("""
            CREATE TABLE share_links (
                id VARCHAR PRIMARY KEY,
                token VARCHAR UNIQUE NOT NULL,
                resource_type VARCHAR NOT NULL,
                resource_id VARCHAR,
                permissions VARCHAR DEFAULT 'read',
                max_uses INTEGER,
                use_count INTEGER DEFAULT 0,
                password_hash VARCHAR,
                is_active BOOLEAN DEFAULT 1,
                revoked_at TIMESTAMP,
                revoked_by VARCHAR,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                description TEXT,
                last_used_at TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_share_links_token ON share_links(token)")
        cursor.execute("CREATE INDEX idx_share_links_active ON share_links(is_active)")
        cursor.execute("CREATE INDEX idx_share_links_created_by ON share_links(created_by)")
        
        conn.commit()
        print("Migration completed successfully!")
        print("- Created share_links table")
        print("- Created indexes: token, is_active, created_by")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_share_links()
