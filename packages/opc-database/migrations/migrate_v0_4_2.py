"""
OpenClaw OPC v0.4.2 Database Migration
添加工作流支持字段到 Task 表

运行方式:
    python migrate_v0_4_2.py

作者: OPC Team
日期: 2026-03-25
"""

import asyncio
import json
import sqlite3
from datetime import datetime


def migrate_sqlite(db_path: str = "data/opc.db"):
    """迁移 SQLite 数据库"""
    print(f"Migrating SQLite database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    if not cursor.fetchone():
        print("Tasks table does not exist, skipping migration")
        conn.close()
        return
    
    # 获取现有列
    cursor.execute("PRAGMA table_info(tasks)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # 定义新列
    new_columns = {
        "workflow_id": "TEXT",
        "step_index": "INTEGER DEFAULT 0",
        "total_steps": "INTEGER DEFAULT 1",
        "depends_on": "TEXT",
        "next_task_id": "TEXT",
        "input_data": "TEXT DEFAULT '{}'",
        "output_data": "TEXT DEFAULT '{}'",
        "is_rework": "BOOLEAN DEFAULT 0",
        "rework_target": "TEXT",
        "rework_triggered_by": "TEXT",
        "rework_reason": "TEXT",
        "rework_instructions": "TEXT",
        "execution_log": "TEXT DEFAULT '[]'",
    }
    
    # 添加新列
    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} {column_type}")
                print(f"  Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"  Error adding {column_name}: {e}")
        else:
            print(f"  Column already exists: {column_name}")
    
    # 为 workflow_id 创建索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id ON tasks(workflow_id)")
        print("  Created index: idx_tasks_workflow_id")
    except sqlite3.OperationalError as e:
        print(f"  Error creating index: {e}")
    
    # 为 depends_on 和 next_task_id 创建外键约束（SQLite 支持有限，这里仅创建索引）
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_depends_on ON tasks(depends_on)")
        print("  Created index: idx_tasks_depends_on")
    except sqlite3.OperationalError as e:
        print(f"  Error creating index: {e}")
    
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_next_task_id ON tasks(next_task_id)")
        print("  Created index: idx_tasks_next_task_id")
    except sqlite3.OperationalError as e:
        print(f"  Error creating index: {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")


async def migrate_asyncpg():
    """迁移 PostgreSQL 数据库（使用 asyncpg）"""
    import asyncpg
    
    print("Migrating PostgreSQL database...")
    
    # 这里需要配置数据库连接
    # conn = await asyncpg.connect(DATABASE_URL)
    
    # 添加列的 SQL 语句
    alter_statements = [
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(255);",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS step_index INTEGER DEFAULT 0;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS total_steps INTEGER DEFAULT 1;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS depends_on VARCHAR(255) REFERENCES tasks(id);",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS next_task_id VARCHAR(255) REFERENCES tasks(id);",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS input_data TEXT DEFAULT '{}';",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS output_data TEXT DEFAULT '{}';",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_rework BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rework_target VARCHAR(255);",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rework_triggered_by VARCHAR(255);",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rework_reason TEXT;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS rework_instructions TEXT;",
        "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS execution_log TEXT DEFAULT '[]';",
        "CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id ON tasks(workflow_id);",
        "CREATE INDEX IF NOT EXISTS idx_tasks_depends_on ON tasks(depends_on);",
        "CREATE INDEX IF NOT EXISTS idx_tasks_next_task_id ON tasks(next_task_id);",
    ]
    
    print("PostgreSQL migration SQL statements prepared.")
    print("Please run these statements manually or configure DATABASE_URL:")
    for stmt in alter_statements:
        print(f"  {stmt}")


def main():
    """主函数"""
    import sys
    
    print("=" * 60)
    print("OpenClaw OPC v0.4.2 Database Migration")
    print("=" * 60)
    print()
    
    # 默认使用 SQLite
    db_type = sys.argv[1] if len(sys.argv) > 1 else "sqlite"
    
    if db_type == "sqlite":
        db_path = sys.argv[2] if len(sys.argv) > 2 else "data/opc.db"
        migrate_sqlite(db_path)
    elif db_type == "postgres":
        asyncio.run(migrate_asyncpg())
    else:
        print(f"Unknown database type: {db_type}")
        print("Usage: python migrate_v0_4_2.py [sqlite|postgres] [db_path]")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("Migration completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
