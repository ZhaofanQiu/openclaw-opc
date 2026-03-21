"""
Migration: Add avatar fields to agents table

Run this script to add avatar_url and avatar_source columns.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text
from src.database import engine, get_database_url


def migrate():
    """Add avatar columns to agents table."""
    print(f"Database: {get_database_url()}")
    
    with engine.connect() as conn:
        # Check if columns exist
        if engine.url.drivername.startswith('sqlite'):
            # SQLite: check columns in table info
            result = conn.execute(text("PRAGMA table_info(agents)"))
            columns = [row[1] for row in result]
            
            if 'avatar_url' not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN avatar_url VARCHAR"))
                print("✅ Added avatar_url column")
            else:
                print("⏭️  avatar_url column already exists")
            
            if 'avatar_source' not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN avatar_source VARCHAR DEFAULT 'system'"))
                print("✅ Added avatar_source column")
            else:
                print("⏭️  avatar_source column already exists")
                
        else:
            # PostgreSQL
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'agents'
            """))
            columns = [row[0] for row in result]
            
            if 'avatar_url' not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN avatar_url VARCHAR"))
                print("✅ Added avatar_url column")
            else:
                print("⏭️  avatar_url column already exists")
            
            if 'avatar_source' not in columns:
                conn.execute(text("ALTER TABLE agents ADD COLUMN avatar_source VARCHAR DEFAULT 'system'"))
                print("✅ Added avatar_source column")
            else:
                print("⏭️  avatar_source column already exists")
        
        conn.commit()
    
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    migrate()
