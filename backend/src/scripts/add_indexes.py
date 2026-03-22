"""
Database Index Migration Script
添加数据库索引以优化查询性能

运行方式:
    cd backend && python -m src.scripts.add_indexes

或直接使用 SQL:
    sqlite3 data/opc.db < src/scripts/indexes.sql
"""

import sqlite3
import os
from pathlib import Path

# 索引定义
INDEXES = [
    # workflow_steps 索引
    ("idx_workflow_steps_workflow_id", "workflow_steps", "workflow_id"),
    ("idx_workflow_steps_assignee_id", "workflow_steps", "assignee_id"),
    ("idx_workflow_steps_status", "workflow_steps", "status"),
    ("idx_workflow_steps_workflow_status", "workflow_steps", "workflow_id, status"),
    
    # workflow_history 索引
    ("idx_workflow_history_workflow_id", "workflow_history", "workflow_id"),
    ("idx_workflow_history_created_at", "workflow_history", "created_at"),
    
    # workflow_rework_records 索引
    ("idx_workflow_rework_workflow_id", "workflow_rework_records", "workflow_id"),
    
    # agents 索引
    ("idx_agents_position_level", "agents", "position_level"),
    ("idx_agents_is_bound", "agents", "is_bound"),
    
    # tasks 索引
    ("idx_tasks_agent_id", "tasks", "agent_id"),
    ("idx_tasks_status", "tasks", "status"),
    ("idx_tasks_agent_status", "tasks", "agent_id, status"),
    
    # async_messages 索引
    ("idx_async_messages_recipient", "async_messages", "recipient_id"),
    ("idx_async_messages_status", "async_messages", "status"),
    ("idx_async_messages_recipient_status", "async_messages", "recipient_id, status"),
    
    # budget_transactions 索引
    ("idx_budget_agent_id", "budget_transactions", "agent_id"),
    ("idx_budget_created_at", "budget_transactions", "created_at"),
]


def add_indexes(db_path: str = None):
    """添加所有索引"""
    
    if db_path is None:
        # 默认数据库路径
        base_dir = Path(__file__).parent.parent.parent
        db_path = base_dir / "data" / "opc.db"
    
    print(f"📁 数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取现有索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    existing_indexes = {row[0] for row in cursor.fetchall()}
    
    added_count = 0
    skipped_count = 0
    
    print(f"\n🚀 开始添加索引...")
    print("-" * 60)
    
    for index_name, table, columns in INDEXES:
        if index_name in existing_indexes:
            print(f"⏭️  跳过已存在: {index_name}")
            skipped_count += 1
            continue
        
        try:
            sql = f"CREATE INDEX {index_name} ON {table}({columns})"
            cursor.execute(sql)
            print(f"✅ 已创建: {index_name} ON {table}({columns})")
            added_count += 1
        except sqlite3.Error as e:
            print(f"❌ 失败: {index_name} - {e}")
    
    conn.commit()
    conn.close()
    
    print("-" * 60)
    print(f"\n📊 结果统计:")
    print(f"   新增索引: {added_count}")
    print(f"   跳过已有: {skipped_count}")
    print(f"   总计: {added_count + skipped_count}/{len(INDEXES)}")
    
    return True


def verify_indexes(db_path: str = None):
    """验证索引是否创建成功"""
    
    if db_path is None:
        base_dir = Path(__file__).parent.parent.parent
        db_path = base_dir / "data" / "opc.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n🔍 验证索引...")
    print("-" * 60)
    
    for index_name, table, columns in INDEXES:
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
            (index_name,)
        )
        exists = cursor.fetchone() is not None
        status = "✅" if exists else "❌"
        print(f"{status} {index_name}")
    
    conn.close()
    print("-" * 60)


def analyze_query_performance(db_path: str = None):
    """分析查询性能（使用EXPLAIN QUERY PLAN）"""
    
    if db_path is None:
        base_dir = Path(__file__).parent.parent.parent
        db_path = base_dir / "data" / "opc.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    test_queries = [
        ("工作流步骤查询", 
         "SELECT * FROM workflow_steps WHERE workflow_id = 'test'"),
        ("员工任务查询", 
         "SELECT * FROM tasks WHERE agent_id = 'test' AND status = 'pending'"),
        ("消息收件箱", 
         "SELECT * FROM async_messages WHERE recipient_id = 'test' AND status = 'pending'"),
        ("Partner查询", 
         "SELECT * FROM agents WHERE position_level = 5"),
    ]
    
    print("\n📈 查询计划分析")
    print("-" * 60)
    
    for name, query in test_queries:
        print(f"\n{name}:")
        print(f"  SQL: {query}")
        
        cursor.execute(f"EXPLAIN QUERY PLAN {query}")
        plans = cursor.fetchall()
        
        for plan in plans:
            detail = plan[3] if len(plan) > 3 else str(plan)
            print(f"  📋 {detail}")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    # 支持自定义数据库路径
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("=" * 60)
    print("   OpenClaw OPC - 数据库索引优化工具")
    print("=" * 60)
    
    # 添加索引
    success = add_indexes(db_path)
    
    if success:
        # 验证索引
        verify_indexes(db_path)
        
        # 分析查询
        analyze_query_performance(db_path)
        
        print("\n✨ 优化完成！")
    else:
        print("\n❌ 优化失败")
        sys.exit(1)
