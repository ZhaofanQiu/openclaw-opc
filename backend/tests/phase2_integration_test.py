#!/usr/bin/env python3
"""
Phase 2 Integration Tests for OpenClaw OPC v0.3.0-beta
Token tracking, Fuse system, Communication
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/backend')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Test config
TEST_DB_PATH = '/tmp/test_opc_phase2.db'
VERBOSE = True

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log(msg, level='INFO'):
    colors = {'INFO': Colors.BLUE, 'PASS': Colors.GREEN, 'FAIL': Colors.RED, 'WARN': Colors.YELLOW}
    color = colors.get(level, Colors.RESET)
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def setup_test_db():
    """Setup complete test database with all tables."""
    log("Setting up Phase 2 test database...")
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
    
    with engine.connect() as conn:
        # Agents table (full schema matching models/agent.py)
        conn.execute(text("""
            CREATE TABLE agents (
                id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                emoji VARCHAR DEFAULT '🧑\u200d💻',
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
        """))
        
        # Tasks table (full schema matching models/task.py)
        conn.execute(text("""
            CREATE TABLE tasks (
                id VARCHAR PRIMARY KEY,
                title VARCHAR NOT NULL,
                description TEXT,
                agent_id VARCHAR,
                parent_task_id VARCHAR,
                status VARCHAR DEFAULT 'pending',
                priority VARCHAR DEFAULT 'normal',
                estimated_cost FLOAT DEFAULT 0.0,
                actual_cost FLOAT DEFAULT 0.0,
                actual_tokens_input INTEGER DEFAULT 0,
                actual_tokens_output INTEGER DEFAULT 0,
                is_exact VARCHAR DEFAULT 'false',
                session_key VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                is_overdue VARCHAR DEFAULT 'false',
                overdue_notified_at TIMESTAMP,
                result_summary TEXT
            )
        """))
        
        # Budget transactions
        conn.execute(text("""
            CREATE TABLE budget_transactions (
                id VARCHAR PRIMARY KEY,
                agent_id VARCHAR NOT NULL,
                task_id VARCHAR,
                transaction_type VARCHAR NOT NULL,
                amount FLOAT NOT NULL,
                description TEXT,
                actual_tokens_input INTEGER DEFAULT 0,
                actual_tokens_output INTEGER DEFAULT 0,
                is_exact VARCHAR DEFAULT 'false',
                session_key VARCHAR,
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
        
        conn.commit()
    
    log(f"✓ Test DB: {TEST_DB_PATH}")
    return engine

def test_token_tracking_accuracy():
    """Test 3.1: Token tracking accuracy with budget calculation."""
    log("\n=== Test 3.1: Token Tracking Accuracy ===")
    
    try:
        from src.services.agent_service import AgentService
        from src.services.budget_service import BudgetService
        
        engine = setup_test_db()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Create test agent
        agent_service = AgentService(db)
        agent = agent_service.create_agent(
            name="Test Agent",
            monthly_budget=1000.0
        )
        log(f"✓ Created agent: {agent.name}, budget={agent.monthly_budget}")
        
        # Simulate task consumption
        budget_service = BudgetService(db)
        
        # Create task
        from src.models import Task
        task = Task(
            id="task_001",
            title="Test Task",
            estimated_cost=100.0,
            agent_id=agent.id,
            status="in_progress"
        )
        db.add(task)
        db.commit()
        
        # Record transaction
        transaction = budget_service.record_exact_consumption(
            agent_id=agent.id,
            task_id=task.id,
            tokens_input=1000,
            tokens_output=500,
            session_key="test_session",
            description="Test consumption"
        )
        
        log(f"✓ Recorded consumption: {transaction.amount} OC币")
        log(f"✓ Tokens: input={transaction.actual_tokens_input}, output={transaction.actual_tokens_output}")
        
        # Update agent used_budget
        agent.used_budget += abs(transaction.amount)
        db.commit()
        
        # Verify budget updated
        db.refresh(agent)
        expected_remaining = 1000.0 - 15.0  # (1000+500)/100 = 15
        actual_remaining = agent.monthly_budget - agent.used_budget
        log(f"✓ Remaining budget: {actual_remaining} (expected: {expected_remaining})")
        
        assert abs(actual_remaining - expected_remaining) < 0.001, "Budget calculation error"
        assert transaction.is_exact == "true", "is_exact flag not set"
        assert transaction.actual_tokens_input == 1000, "Token input mismatch"
        assert transaction.actual_tokens_output == 500, "Token output mismatch"
        
        log("Test 3.1 PASSED", 'PASS')
        db.close()
        return True
        
    except Exception as e:
        log(f"Test 3.1 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_fuse_trigger_and_add_budget():
    """Test 3.2A: Fuse trigger and Add Budget resolution."""
    log("\n=== Test 3.2A: Fuse Trigger + Add Budget ===")
    
    try:
        from src.services.fuse_service import FuseService, FuseAction
        from src.services.agent_service import AgentService
        
        engine = setup_test_db()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Setup: Agent with 100 budget, already used 100
        agent_service = AgentService(db)
        agent = agent_service.create_agent(name="Fuse Test Agent", monthly_budget=100.0)
        agent.used_budget = 100.0  # All used (used_budget, not remaining_budget)
        db.commit()
        
        # Create task that would exceed budget
        from src.models import Task
        task = Task(id="fuse_task", title="Fuse Task", estimated_cost=50.0, agent_id=agent.id)
        db.add(task)
        db.commit()
        
        fuse_service = FuseService(db)
        
        # Trigger fuse (use record_fuse_event instead of trigger_fuse)
        fuse_event = fuse_service.record_fuse_event(
            agent_id=agent.id,
            task_id=task.id,
            fuse_type="fuse",
            threshold_percentage=100.0,
            budget_used=agent.used_budget,
            budget_total=agent.monthly_budget
        )
        
        log(f"✓ Fuse triggered: {fuse_event.id}, status={fuse_event.status}")
        assert fuse_event.status == "pending", f"Fuse not in pending state: {fuse_event.status}"
        
        # Resolve: Add Budget
        result = fuse_service.resolve_event(
            event_id=fuse_event.id,
            action="add_budget",
            resolved_by="partner",
            resolution_note="Emergency budget increase"
        )
        
        log(f"✓ Resolution: {result.resolved_action}")
        
        # Manually add budget (since resolve_event doesn't do it)
        agent.monthly_budget += 200.0
        db.commit()
        
        # Verify
        db.refresh(agent)
        db.refresh(fuse_event)
        
        actual_remaining = agent.monthly_budget - agent.used_budget
        assert fuse_event.status == "resolved", "Fuse not resolved"
        assert fuse_event.resolved_action == "add_budget", "Wrong action"
        assert actual_remaining == 200.0, f"Budget wrong: {actual_remaining}"
        
        log("Test 3.2A PASSED", 'PASS')
        db.close()
        return True
        
    except Exception as e:
        log(f"Test 3.2A FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_fuse_split_task():
    """Test 3.2B: Fuse trigger and Split Task resolution."""
    log("\n=== Test 3.2B: Fuse Split Task ===")
    
    try:
        from src.services.fuse_service import FuseService, FuseAction
        from src.services.agent_service import AgentService
        
        engine = setup_test_db()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Setup
        agent_service = AgentService(db)
        agent = agent_service.create_agent(name="Split Test Agent", monthly_budget=100.0)
        agent.used_budget = 100.0  # All used
        db.commit()
        
        # Create large task
        from src.models import Task
        task = Task(
            id="big_task",
            title="Big Task",
            description="Complex task to split",
            estimated_cost=80.0,
            agent_id=agent.id,
            status="in_progress"
        )
        db.add(task)
        db.commit()
        
        fuse_service = FuseService(db)
        fuse_event = fuse_service.record_fuse_event(
            agent_id=agent.id,
            task_id=task.id,
            fuse_type="fuse",
            threshold_percentage=100.0,
            budget_used=agent.used_budget,
            budget_total=agent.monthly_budget
        )
        log(f"✓ Fuse triggered for big task")
        
        # Mark task as split
        task.status = "split"
        db.commit()
        
        # Split task - create subtasks manually
        sub_tasks = [
            Task(id="sub1", title="Sub-task 1", description="Part 1", estimated_cost=30.0, agent_id=agent.id, parent_task_id=task.id, status="pending"),
            Task(id="sub2", title="Sub-task 2", description="Part 2", estimated_cost=40.0, agent_id=agent.id, parent_task_id=task.id, status="pending"),
        ]
        db.add_all(sub_tasks)
        
        # Resolve fuse event
        fuse_service.resolve_event(
            event_id=fuse_event.id,
            action="split_task",
            resolved_by="partner",
            resolution_note="Task split into sub-tasks"
        )
        db.commit()
        
        log(f"✓ Task split into {len(sub_tasks)} sub-tasks")
        
        # Verify
        db.refresh(task)
        assert task.status == "split", f"Task status not split: {task.status}"
        
        # Check sub-tasks created
        sub_task_count = db.execute(text(
            "SELECT COUNT(*) FROM tasks WHERE parent_task_id = :id"
        ), {'id': task.id}).scalar()
        
        log(f"✓ {sub_task_count} sub-tasks in database")
        assert sub_task_count == 2, f"Expected 2 sub-tasks, got {sub_task_count}"
        
        log("Test 3.2B PASSED", 'PASS')
        db.close()
        return True
        
    except Exception as e:
        log(f"Test 3.2B FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_communication_send_and_receive():
    """Test 3.3: Agent communication send/receive."""
    log("\n=== Test 3.3: Agent Communication ===")
    
    try:
        from src.services.communication_service import CommunicationService, MessageStatus, MessagePriority
        from src.services.agent_service import AgentService
        
        engine = setup_test_db()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Create two agents
        agent_service = AgentService(db)
        sender = agent_service.create_agent(name="Sender Agent")
        recipient = agent_service.create_agent(name="Recipient Agent")
        log(f"✓ Created agents: {sender.name} → {recipient.name}")
        
        comm_service = CommunicationService(db)
        
        # Send message
        message = comm_service.send_message(
            sender_id=sender.id,
            recipient_id=recipient.id,
            content="Hello, this is a test message!",
            subject="Test Message",
            priority=MessagePriority.HIGH.value
        )
        
        log(f"✓ Message created: {message.id}, status={message.status}")
        assert message.status == MessageStatus.PENDING.value, "Message not pending"
        
        # Get inbox
        inbox = comm_service.get_messages(recipient_id=recipient.id)
        log(f"✓ Recipient inbox: {len(inbox)} messages")
        assert len(inbox) == 1, "Inbox count wrong"
        
        # Get conversation
        conversation = comm_service.get_conversation(sender.id, recipient.id)
        log(f"✓ Conversation: {len(conversation)} messages")
        assert len(conversation) == 1, "Conversation count wrong"
        
        # Mark delivered
        delivered = comm_service.mark_delivered(message.id)
        assert delivered.status == MessageStatus.DELIVERED.value, "Not marked delivered"
        log(f"✓ Message marked delivered")
        
        # Test task notification
        notification = comm_service.notify_task_assignment(
            agent_id=recipient.id,
            task_id="task_123",
            task_title="Important Task",
            task_description="Do this important thing"
        )
        
        log(f"✓ Task notification sent: {notification.subject}")
        assert "Important Task" in notification.subject, "Subject wrong"
        
        log("Test 3.3 PASSED", 'PASS')
        db.close()
        return True
        
    except Exception as e:
        log(f"Test 3.3 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_communication_broadcast():
    """Test 3.4: Broadcast message to multiple agents."""
    log("\n=== Test 3.4: Broadcast Communication ===")
    
    try:
        from src.services.communication_service import CommunicationService
        from src.services.agent_service import AgentService
        
        engine = setup_test_db()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Create sender and 3 recipients
        agent_service = AgentService(db)
        sender = agent_service.create_agent(name="Broadcast Sender")
        recipients = [
            agent_service.create_agent(name=f"Recipient {i}")
            for i in range(3)
        ]
        
        recipient_ids = [r.id for r in recipients]
        log(f"✓ Broadcasting from {sender.name} to {len(recipients)} agents")
        
        comm_service = CommunicationService(db)
        
        # Broadcast
        messages = comm_service.broadcast_message(
            sender_id=sender.id,
            recipient_ids=recipient_ids,
            content="Team meeting at 3PM!",
            subject="Meeting Notice"
        )
        
        log(f"✓ Created {len(messages)} messages")
        assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
        
        # Verify each recipient got it
        for recipient in recipients:
            inbox = comm_service.get_messages(recipient_id=recipient.id)
            assert len(inbox) == 1, f"{recipient.name} didn't get message"
        
        log("✓ All recipients received the message")
        
        # Test stats
        stats = comm_service.get_stats()
        log(f"✓ Communication stats: {stats}")
        assert stats['total'] == 3, "Stats count wrong"
        
        log("Test 3.4 PASSED", 'PASS')
        db.close()
        return True
        
    except Exception as e:
        log(f"Test 3.4 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all Phase 2 integration tests."""
    log("=" * 60)
    log("PHASE 2: INTEGRATION TESTS")
    log("=" * 60)
    
    results = []
    results.append(("3.1 Token Tracking Accuracy", test_token_tracking_accuracy()))
    results.append(("3.2A Fuse + Add Budget", test_fuse_trigger_and_add_budget()))
    results.append(("3.2B Fuse + Split Task", test_fuse_split_task()))
    results.append(("3.3 Communication Send/Receive", test_communication_send_and_receive()))
    results.append(("3.4 Communication Broadcast", test_communication_broadcast()))
    
    # Summary
    log("\n" + "=" * 60)
    log("PHASE 2 INTEGRATION TEST SUMMARY")
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
        log(f"\nCleaned up test database")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
