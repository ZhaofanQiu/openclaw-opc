"""
Database Migration Script for v0.4.2

Adds workflow support fields to Task model

Revision ID: v0_4_2_add_workflow_fields
Create Date: 2026-03-25
"""

# 这个脚本用于手动执行数据库迁移
# 由于我们使用 SQLite，可以直接删除数据库重新创建
# 或者使用 ALTER TABLE 添加新列

MIGRATION_SQL = """
-- 添加工作流相关字段到 tasks 表

-- 1. 工作流关联字段
ALTER TABLE tasks ADD COLUMN workflow_id VARCHAR(255);
ALTER TABLE tasks ADD COLUMN step_index INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN total_steps INTEGER DEFAULT 1;

-- 2. 步骤链表字段
ALTER TABLE tasks ADD COLUMN depends_on VARCHAR(255);
ALTER TABLE tasks ADD COLUMN next_task_id VARCHAR(255);

-- 3. 结构化数据字段
ALTER TABLE tasks ADD COLUMN input_data TEXT DEFAULT '{}';
ALTER TABLE tasks ADD COLUMN output_data TEXT DEFAULT '{}';

-- 4. 返工机制字段
ALTER TABLE tasks ADD COLUMN is_rework BOOLEAN DEFAULT 0;
ALTER TABLE tasks ADD COLUMN rework_target VARCHAR(255);
ALTER TABLE tasks ADD COLUMN rework_triggered_by VARCHAR(255);
ALTER TABLE tasks ADD COLUMN rework_reason TEXT;
ALTER TABLE tasks ADD COLUMN rework_instructions TEXT;

-- 5. 执行历史日志
ALTER TABLE tasks ADD COLUMN execution_log TEXT DEFAULT '[]';

-- 6. 添加索引
CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id ON tasks(workflow_id);
"""

def get_migration_sql():
    """获取迁移 SQL"""
    return MIGRATION_SQL

def migrate_sqlite(db_path: str):
    """
    执行 SQLite 迁移
    
    由于 SQLite 的 ALTER TABLE 限制，我们采用以下策略：
    1. 检查列是否存在
    2. 如果不存在，使用 ALTER TABLE 添加
    3. SQLite 支持有限的 ALTER TABLE，但添加列是支持的
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取现有列
    cursor.execute("PRAGMA table_info(tasks)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    # 需要添加的列
    columns_to_add = [
        ("workflow_id", "VARCHAR(255)"),
        ("step_index", "INTEGER DEFAULT 0"),
        ("total_steps", "INTEGER DEFAULT 1"),
        ("depends_on", "VARCHAR(255)"),
        ("next_task_id", "VARCHAR(255)"),
        ("input_data", "TEXT DEFAULT '{}'"),
        ("output_data", "TEXT DEFAULT '{}'"),
        ("is_rework", "BOOLEAN DEFAULT 0"),
        ("rework_target", "VARCHAR(255)"),
        ("rework_triggered_by", "VARCHAR(255)"),
        ("rework_reason", "TEXT"),
        ("rework_instructions", "TEXT"),
        ("execution_log", "TEXT DEFAULT '[]'"),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
                print(f"✅ Added column: {col_name}")
            except Exception as e:
                print(f"⚠️ Failed to add {col_name}: {e}")
        else:
            print(f"⏭️ Column already exists: {col_name}")
    
    # 添加索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_workflow_id ON tasks(workflow_id)")
        print("✅ Created index: idx_tasks_workflow_id")
    except Exception as e:
        print(f"⚠️ Failed to create index: {e}")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration completed!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        migrate_sqlite(db_path)
    else:
        print("Usage: python migration_v0_4_2.py <db_path>")
        print(f"\nMigration SQL:\n{MIGRATION_SQL}")
