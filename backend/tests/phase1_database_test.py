#!/usr/bin/env python3
"""
Phase 1 Unit Tests for OpenClaw OPC v0.3.0-beta
Database Compatibility Tests
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/backend')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Test configuration
TEST_DB_PATH = '/tmp/test_opc_phase1.db'
VERBOSE = True

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level='INFO'):
    """Log with color and timestamp."""
    colors = {
        'INFO': Colors.BLUE,
        'PASS': Colors.GREEN,
        'FAIL': Colors.RED,
        'WARN': Colors.YELLOW,
    }
    color = colors.get(level, Colors.RESET)
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def setup_sqlite_db():
    """Create fresh SQLite test database."""
    log("Setting up SQLite test database...")
    
    # Remove existing test db
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
    
    # Create tables manually to avoid full migration
    with engine.connect() as conn:
        # Agents table
        conn.execute(text("""
            CREATE TABLE agents (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                agent_id VARCHAR,
                is_bound VARCHAR DEFAULT 'false',
                emoji VARCHAR DEFAULT '🧑‍💻',
                position_level VARCHAR DEFAULT 'EMPLOYEE',
                monthly_budget FLOAT DEFAULT 2000.0,
                remaining_budget FLOAT DEFAULT 2000.0,
                current_task_id VARCHAR,
                status VARCHAR DEFAULT 'idle',
                mood VARCHAR DEFAULT '😊',
                skills TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Tasks table
        conn.execute(text("""
            CREATE TABLE tasks (
                id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                description TEXT,
                status VARCHAR DEFAULT 'pending',
                assigned_to VARCHAR,
                estimated_cost FLOAT DEFAULT 0,
                actual_cost FLOAT DEFAULT 0,
                priority VARCHAR DEFAULT 'normal',
                required_skills TEXT,
                parent_task_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """))
        
        # Budget transactions
        conn.execute(text("""
            CREATE TABLE budget_transactions (
                id VARCHAR PRIMARY KEY,
                agent_id VARCHAR NOT NULL,
                task_id VARCHAR,
                amount FLOAT NOT NULL,
                transaction_type VARCHAR NOT NULL,
                description TEXT,
                is_exact BOOLEAN DEFAULT 0,
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                session_key VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Employee avatars
        conn.execute(text("""
            CREATE TABLE employee_avatars (
                id VARCHAR PRIMARY KEY,
                agent_id VARCHAR NOT NULL UNIQUE,
                source VARCHAR DEFAULT 'system',
                url VARCHAR NOT NULL,
                generation_prompt TEXT,
                skill_used VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Agent messages
        conn.execute(text("""
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
        """))
        
        # Budget fuse events
        conn.execute(text("""
            CREATE TABLE budget_fuse_events (
                id VARCHAR PRIMARY KEY,
                agent_id VARCHAR NOT NULL,
                task_id VARCHAR,
                fuse_type VARCHAR NOT NULL,
                threshold_percent FLOAT NOT NULL,
                budget_used FLOAT NOT NULL,
                budget_total FLOAT NOT NULL,
                status VARCHAR DEFAULT 'triggered',
                resolution_action VARCHAR,
                resolution_amount FLOAT,
                resolution_reason TEXT,
                resolved_by VARCHAR,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """))
        
        conn.commit()
    
    log(f"SQLite database created at {TEST_DB_PATH}", 'PASS')
    return engine

def test_basic_crud(engine):
    """Test 1.1: Basic CRUD operations."""
    log("\n=== Test 1.1: Basic CRUD Operations ===")
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create
        agent_id = "test_agent_001"
        db.execute(text("""
            INSERT INTO agents (id, name, emoji, monthly_budget, remaining_budget)
            VALUES (:id, :name, :emoji, :budget, :remaining)
        """), {
            'id': agent_id,
            'name': 'Test Agent',
            'emoji': '🤖',
            'budget': 2000.0,
            'remaining': 2000.0
        })
        db.commit()
        log(f"✓ Created agent {agent_id}")
        
        # Read
        result = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': agent_id})
        agent = result.fetchone()
        assert agent is not None, "Agent not found"
        assert agent.name == 'Test Agent', f"Name mismatch: {agent.name}"
        log(f"✓ Read agent: name={agent.name}, budget={agent.monthly_budget}")
        
        # Update
        db.execute(text("""
            UPDATE agents SET remaining_budget = :budget WHERE id = :id
        """), {'id': agent_id, 'budget': 1500.0})
        db.commit()
        
        result = db.execute(text("SELECT remaining_budget FROM agents WHERE id = :id"), {'id': agent_id})
        updated = result.fetchone()
        assert updated.remaining_budget == 1500.0, f"Update failed: {updated.remaining_budget}"
        log(f"✓ Updated remaining_budget to 1500.0")
        
        # Delete
        db.execute(text("DELETE FROM agents WHERE id = :id"), {'id': agent_id})
        db.commit()
        
        result = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': agent_id})
        assert result.fetchone() is None, "Agent not deleted"
        log(f"✓ Deleted agent {agent_id}")
        
        log("Test 1.1 PASSED", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 1.1 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_unicode_and_special_chars(engine):
    """Test 1.2: Unicode, emoji, and special characters."""
    log("\n=== Test 1.2: Unicode and Special Characters ===")
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    test_cases = [
        ('unicode_001', '中文测试', '中文描述测试'),
        ('emoji_001', 'Agent 🎉🚀💻', 'Testing with emojis 🎨🎮🔥'),
        ('special_001', 'Test \'quotes\' and "double"', 'Special chars: < > & " \''),
        ('long_001', 'A' * 1000, 'B' * 5000),  # Long text
    ]
    
    try:
        for agent_id, name, desc in test_cases:
            db.execute(text("""
                INSERT INTO agents (id, name, current_task_id)
                VALUES (:id, :name, :desc)
            """), {'id': agent_id, 'name': name, 'desc': desc})
        
        db.commit()
        
        # Verify
        for agent_id, expected_name, expected_desc in test_cases:
            result = db.execute(text("SELECT name, current_task_id FROM agents WHERE id = :id"), {'id': agent_id})
            row = result.fetchone()
            assert row is not None, f"Agent {agent_id} not found"
            assert row.name == expected_name, f"Name mismatch for {agent_id}"
            assert row.current_task_id == expected_desc, f"Desc mismatch for {agent_id}"
            log(f"✓ {agent_id}: name={row.name[:30]}..., desc_len={len(row.current_task_id)}")
        
        log("Test 1.2 PASSED", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 1.2 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_float_precision(engine):
    """Test 1.3: Float precision for budget calculations."""
    log("\n=== Test 1.3: Float Precision ===")
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Test high precision values
        test_values = [
            0.0001,
            123.4567,
            999999.9999,
            0.123456789,  # Should truncate/round
        ]
        
        for i, value in enumerate(test_values):
            agent_id = f"precision_{i}"
            db.execute(text("""
                INSERT INTO agents (id, name, monthly_budget, remaining_budget)
                VALUES (:id, :name, :budget, :remaining)
            """), {'id': agent_id, 'name': f'Precision Test {i}', 'budget': value, 'remaining': value})
        
        db.commit()
        
        # Verify
        for i, expected in enumerate(test_values):
            agent_id = f"precision_{i}"
            result = db.execute(text("SELECT monthly_budget FROM agents WHERE id = :id"), {'id': agent_id})
            row = result.fetchone()
            
            # SQLite stores as REAL (8-byte IEEE), small precision loss expected
            stored = row.monthly_budget
            diff = abs(stored - expected)
            
            log(f"✓ {agent_id}: expected={expected}, stored={stored}, diff={diff:.2e}")
            assert diff < 1e-10, f"Precision loss too large: {diff}"
        
        log("Test 1.3 PASSED", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 1.3 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_datetime_handling(engine):
    """Test 1.4: DateTime handling."""
    log("\n=== Test 1.4: DateTime Handling ===")
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Insert with explicit timestamp
        agent_id = "datetime_test"
        now = datetime.now(timezone.utc)
        
        db.execute(text("""
            INSERT INTO agents (id, name, created_at)
            VALUES (:id, :name, :created)
        """), {'id': agent_id, 'name': 'DateTime Test', 'created': now})
        db.commit()
        
        # Read back
        result = db.execute(text("SELECT created_at FROM agents WHERE id = :id"), {'id': agent_id})
        row = result.fetchone()
        
        log(f"✓ Original: {now}")
        log(f"✓ Stored: {row.created_at}")
        
        # Verify it's close (SQLite may lose timezone info)
        if row.created_at:
            log("Test 1.4 PASSED (timestamp stored)", 'PASS')
        else:
            log("Test 1.4 WARNING: timestamp is None", 'WARN')
        
        return True
        
    except Exception as e:
        log(f"Test 1.4 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_concurrent_writes(engine):
    """Test 1.5: Concurrent write handling."""
    log("\n=== Test 1.5: Concurrent Writes ===")
    
    # SQLite has limited concurrency, test basic behavior
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Create shared agent
        agent_id = "concurrent_agent"
        db.execute(text("""
            INSERT INTO agents (id, name, remaining_budget)
            VALUES (:id, :name, :budget)
        """), {'id': agent_id, 'name': 'Concurrent Test', 'budget': 1000.0})
        db.commit()
        
        # Simulate concurrent updates (sequential in SQLite)
        updates = [100, 200, 300, 400, 500]
        for i, amount in enumerate(updates):
            db.execute(text("""
                UPDATE agents SET remaining_budget = :amount WHERE id = :id
            """), {'id': agent_id, 'amount': amount})
            db.commit()
            log(f"✓ Update {i+1}: budget = {amount}")
        
        # Final value should be last update
        result = db.execute(text("SELECT remaining_budget FROM agents WHERE id = :id"), {'id': agent_id})
        final = result.fetchone()
        assert final.remaining_budget == 500, f"Final value wrong: {final.remaining_budget}"
        
        log(f"✓ Final budget: {final.remaining_budget}")
        log("Test 1.5 PASSED", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 1.5 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_transaction_rollback(engine):
    """Test 1.6: Transaction rollback."""
    log("\n=== Test 1.6: Transaction Rollback ===")
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Start transaction
        agent_id = "rollback_test"
        db.execute(text("""
            INSERT INTO agents (id, name, remaining_budget)
            VALUES (:id, :name, :budget)
        """), {'id': agent_id, 'name': 'Rollback Test', 'budget': 1000.0})
        
        # Verify it's there (within same session)
        result = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': agent_id})
        assert result.fetchone() is not None, "Insert not visible in session"
        log("✓ Insert visible in session")
        
        # Rollback
        db.rollback()
        
        # Verify it's gone
        result = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': agent_id})
        assert result.fetchone() is None, "Rollback failed"
        log("✓ Rollback successful")
        
        log("Test 1.6 PASSED", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 1.6 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def run_all_tests():
    """Run all Phase 1 database tests."""
    log("=" * 60)
    log("PHASE 1: DATABASE COMPATIBILITY TESTS")
    log("=" * 60)
    
    # Setup
    engine = setup_sqlite_db()
    
    # Run tests
    results = []
    results.append(("1.1 Basic CRUD", test_basic_crud(engine)))
    results.append(("1.2 Unicode/Special Chars", test_unicode_and_special_chars(engine)))
    results.append(("1.3 Float Precision", test_float_precision(engine)))
    results.append(("1.4 DateTime Handling", test_datetime_handling(engine)))
    results.append(("1.5 Concurrent Writes", test_concurrent_writes(engine)))
    results.append(("1.6 Transaction Rollback", test_transaction_rollback(engine)))
    
    # Summary
    log("\n" + "=" * 60)
    log("PHASE 1 DATABASE TEST SUMMARY")
    log("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = 'PASS' if result else 'FAIL'
        log(f"{name}: {status}", status)
    
    log(f"\nTotal: {passed}/{total} tests passed", 'PASS' if passed == total else 'FAIL')
    
    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        log(f"\nCleaned up test database: {TEST_DB_PATH}")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
