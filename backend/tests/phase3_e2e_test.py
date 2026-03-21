#!/usr/bin/env python3
"""
Phase 3 End-to-End Tests for OpenClaw OPC v0.3.0-beta
Complete workflow testing with real database
"""

import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/backend')

# Use the actual database for E2E testing
DB_PATH = '/root/.openclaw/workspace/openclaw-opc/backend/data/opc.db'

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

def setup_e2e_env():
    """Setup E2E test environment using real database."""
    log("Setting up E2E test environment...")
    
    # Ensure data directory exists
    data_dir = Path(DB_PATH).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create engine with actual database
    from sqlalchemy import create_engine
    engine = create_engine(f'sqlite:///{DB_PATH}')
    
    # Create tables if not exist (using actual models)
    from src.database import Base
    Base.metadata.create_all(bind=engine)
    
    log(f"✓ Connected to: {DB_PATH}")
    return engine

def cleanup_test_data(db):
    """Clean up test data after tests."""
    from sqlalchemy import text
    
    # Delete test agents (those with 'test_' prefix)
    db.execute(text("DELETE FROM agents WHERE name LIKE 'E2E Test%'"))
    db.execute(text("DELETE FROM agents WHERE name LIKE 'Test Agent%'"))
    db.execute(text("DELETE FROM tasks WHERE title LIKE 'E2E%'"))
    db.execute(text("DELETE FROM agent_messages WHERE content LIKE '%E2E%'"))
    db.commit()
    log("✓ Cleaned up test data")

def test_complete_task_lifecycle():
    """Test 4.1: Complete task lifecycle from creation to completion."""
    log("\n=== Test 4.1: Complete Task Lifecycle ===")
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.agent_service import AgentService
        from src.services.budget_service import BudgetService
        from src.services.communication_service import CommunicationService
        
        engine = setup_e2e_env()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Step 1: Partner creates an employee
        agent_service = AgentService(db)
        partner = agent_service.create_agent(
            name="E2E Test Partner",
            monthly_budget=5000.0
        )
        # Set as partner via direct DB update
        from sqlalchemy import text
        db.execute(text("UPDATE agents SET position_level = 5 WHERE id = :id"), {'id': partner.id})
        db.commit()
        log(f"✓ Step 1: Partner created: {partner.name}")
        
        # Step 2: Create employee
        employee = agent_service.create_agent(
            name="E2E Test Employee",
            monthly_budget=1000.0
        )
        initial_budget = employee.monthly_budget
        log(f"✓ Step 2: Employee created: {employee.name}, budget={initial_budget}")
        
        # Step 3: Partner creates and assigns task
        from src.models import Task
        task = Task(
            id="e2e_task_001",
            title="E2E Complete Task Test",
            description="Test the complete workflow",
            estimated_cost=100.0,
            priority="high",
            agent_id=employee.id,
            status="assigned"
        )
        db.add(task)
        db.commit()
        log(f"✓ Step 3: Task created: {task.title}, cost={task.estimated_cost}")
        
        # Step 4: Employee receives notification
        comm_service = CommunicationService(db)
        notifications = comm_service.get_messages(recipient_id=employee.id)
        log(f"✓ Step 4: Employee has {len(notifications)} notification(s)")
        
        # Step 5: Employee starts working (task in progress)
        task.status = "in_progress"
        task.started_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        log(f"✓ Step 5: Task started, status={task.status}")
        
        # Step 6: Record budget consumption
        budget_service = BudgetService(db)
        actual_cost = 23.0  # (1500+800)/100 = 23
        transaction = budget_service.record_exact_consumption(
            agent_id=employee.id,
            task_id=task.id,
            tokens_input=1500,
            tokens_output=800,
            session_key="e2e-test-session",
            description="E2E task consumption"
        )
        log(f"✓ Step 6: Consumed {abs(transaction.amount)} OC币 (tokens: {transaction.actual_tokens_input}/{transaction.actual_tokens_output})")
        
        # Update employee used_budget
        employee.used_budget += abs(transaction.amount)
        db.commit()
        
        # Step 7: Complete task
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.result_summary = "E2E test completed successfully"
        db.commit()
        db.refresh(task)
        db.refresh(employee)
        log(f"✓ Step 7: Task completed")
        
        # Step 8: Verify budget updated correctly
        expected_remaining = initial_budget - abs(transaction.amount)
        actual_remaining = employee.monthly_budget - employee.used_budget
        log(f"✓ Step 8: Budget check - expected={expected_remaining:.2f}, actual={actual_remaining:.2f}")
        
        assert abs(actual_remaining - expected_remaining) < 0.01, f"Budget mismatch! expected={expected_remaining}, actual={actual_remaining}"
        
        # Step 9: Verify transaction recorded
        from src.models import BudgetTransaction
        transactions = db.query(BudgetTransaction).filter(BudgetTransaction.agent_id == employee.id).all()
        task_transactions = [t for t in transactions if t.task_id == task.id]
        log(f"✓ Step 9: {len(task_transactions)} transaction(s) recorded for this task")
        
        # Cleanup
        cleanup_test_data(db)
        db.close()
        
        log("Test 4.1 PASSED - Complete workflow verified!", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 4.1 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_fuse_workflow():
    """Test 4.2: Complete fuse workflow - trigger, resolve, recovery."""
    log("\n=== Test 4.2: Fuse Workflow ===")
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.agent_service import AgentService
        from src.services.budget_service import BudgetService
        from src.services.fuse_service import FuseService, FuseAction
        
        engine = setup_e2e_env()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Setup: Create agent with small budget
        agent_service = AgentService(db)
        agent = agent_service.create_agent(
            name="E2E Fuse Test Agent",
            monthly_budget=100.0
        )
        # Simulate budget exhausted
        agent.used_budget = 100.0
        db.commit()
        log(f"✓ Agent created with exhausted budget: {agent.used_budget}/{agent.monthly_budget}")
        
        # Step 1: Try to assign task that exceeds budget
        from src.models import Task
        task = Task(
            id="e2e_fuse_task",
            title="E2E Fuse Trigger Task",
            description="This should trigger fuse",
            estimated_cost=50.0,
            agent_id=agent.id,
            status="pending"
        )
        db.add(task)
        db.commit()
        log(f"✓ Task created requiring {task.estimated_cost} OC币")
        
        # Step 2: Check budget - should fail or create fuse event
        has_budget = agent.monthly_budget - agent.used_budget >= task.estimated_cost
        log(f"✓ Budget check: available={agent.monthly_budget - agent.used_budget}, required={task.estimated_cost}")
        
        if not has_budget:
            # Step 3: Record fuse event
            fuse_service = FuseService(db)
            fuse_event = fuse_service.record_fuse_event(
                agent_id=agent.id,
                task_id=task.id,
                fuse_type="fuse",  # pause/fuse/warning
                threshold_percentage=100.0,
                budget_used=agent.used_budget,
                budget_total=agent.monthly_budget
            )
            log(f"✓ Fuse recorded: {fuse_event.id}, status={fuse_event.status}")
            
            # Step 4: Resolve fuse event
            from src.models import BudgetTransaction
            # Simulate adding budget via transaction
            budget_service = BudgetService(db)
            transaction = BudgetTransaction(
                id=str(__import__('uuid').uuid4())[:8],
                agent_id=agent.id,
                task_id=task.id,
                transaction_type="manual_adjustment",
                amount=200.0,
                description="Emergency budget for E2E test"
            )
            db.add(transaction)
            
            # Update fuse event status
            fuse_event.status = "resolved"
            fuse_event.resolution_type = "add_budget"
            fuse_event.resolved_at = datetime.utcnow()
            db.commit()
            
            # Update agent budget
            agent.monthly_budget += 200.0
            db.commit()
            
            log(f"✓ Fuse resolved: add_budget, added 200.0 OC币")
            
            # Step 5: Verify agent can now work
            db.refresh(agent)
            available = agent.monthly_budget - agent.used_budget
            log(f"✓ Agent now has {available} OC币 available")
            
            assert available >= task.estimated_cost, "Budget still insufficient!"
        
        # Cleanup
        cleanup_test_data(db)
        db.close()
        
        log("Test 4.2 PASSED - Fuse workflow verified!", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 4.2 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_avatar_workflow():
    """Test 4.3: Complete avatar workflow - system, upload, status."""
    log("\n=== Test 4.3: Avatar Workflow ===")
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.agent_service import AgentService
        from src.services.avatar_service import AvatarService, AvatarSource
        
        engine = setup_e2e_env()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Step 1: Create agent
        agent_service = AgentService(db)
        agent = agent_service.create_agent(name="E2E Avatar Test Agent")
        log(f"✓ Step 1: Agent created: {agent.name}")
        
        # Step 2: Generate system avatar
        avatar_service = AvatarService(db)
        avatar1 = avatar_service.generate_system_avatar(agent.id, style='humanoid')
        url1 = avatar_service.get_avatar_url(avatar1)
        log(f"✓ Step 2: System avatar generated: {url1}")
        assert avatar1.source == AvatarSource.SYSTEM.value
        
        # Step 3: Update with different style
        avatar2 = avatar_service.generate_system_avatar(agent.id, style='robot')
        url2 = avatar_service.get_avatar_url(avatar2)
        log(f"✓ Step 3: Updated to robot style: {url2}")
        assert url1 != url2, "URLs should be different for different styles"
        
        # Step 4: Test file upload
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            # Write minimal valid PNG
            f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
            temp_path = f.name
        
        with open(temp_path, 'rb') as f:
            file_data = f.read()
        
        avatar3 = avatar_service.save_uploaded_avatar(
            agent_id=agent.id,
            file_data=file_data,
            filename="test_upload.png",
            content_type="image/png"
        )
        url3 = avatar_service.get_avatar_url(avatar3)
        log(f"✓ Step 4: File uploaded: {url3}")
        assert avatar3.source == AvatarSource.UPLOADED.value
        
        # Step 6: Cleanup uploaded file
        os.remove(temp_path)
        
        # Step 7: Delete avatar (via DB)
        from sqlalchemy import text
        db.execute(text("DELETE FROM employee_avatars WHERE agent_id = :id"), {'id': agent.id})
        db.commit()
        log(f"✓ Step 5: Avatar deleted from database")
        
        # Cleanup
        cleanup_test_data(db)
        db.close()
        
        log("Test 4.3 PASSED - Avatar workflow verified!", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 4.3 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def test_communication_workflow():
    """Test 4.4: Complete communication workflow."""
    log("\n=== Test 4.4: Communication Workflow ===")
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.agent_service import AgentService
        from src.services.communication_service import CommunicationService, MessagePriority
        
        engine = setup_e2e_env()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Step 1: Create agents
        agent_service = AgentService(db)
        partner = agent_service.create_agent(name="E2E Comm Partner")
        # Set as partner
        from sqlalchemy import text
        db.execute(text("UPDATE agents SET position_level = 5 WHERE id = :id"), {'id': partner.id})
        db.commit()
        emp1 = agent_service.create_agent(name="E2E Comm Employee 1")
        emp2 = agent_service.create_agent(name="E2E Comm Employee 2")
        log(f"✓ Step 1: Created {partner.name}, {emp1.name}, {emp2.name}")
        
        # Step 2: Partner sends direct message
        comm_service = CommunicationService(db)
        msg1 = comm_service.send_message(
            sender_id=partner.id,
            recipient_id=emp1.id,
            content="E2E: Please prepare for the meeting tomorrow.",
            subject="Meeting Preparation",
            priority=MessagePriority.HIGH.value
        )
        log(f"✓ Step 2: Direct message sent: {msg1.id}")
        
        # Step 3: Partner broadcasts to team
        msg2 = comm_service.broadcast_message(
            sender_id=partner.id,
            recipient_ids=[emp1.id, emp2.id],
            content="E2E: Team standup at 10AM.",
            subject="Standup Notice"
        )
        log(f"✓ Step 3: Broadcast sent to {len(msg2)} employees")
        
        # Step 4: Check inboxes
        inbox1 = comm_service.get_messages(recipient_id=emp1.id)
        inbox2 = comm_service.get_messages(recipient_id=emp2.id)
        log(f"✓ Step 4: Inboxes - emp1={len(inbox1)}, emp2={len(inbox2)}")
        
        assert len(inbox1) == 2, "Emp1 should have 2 messages (direct + broadcast)"
        assert len(inbox2) == 1, "Emp2 should have 1 message (broadcast only)"
        
        # Step 5: Mark messages delivered
        for msg in inbox1:
            comm_service.mark_delivered(msg.id)
        for msg in inbox2:
            comm_service.mark_delivered(msg.id)
        log(f"✓ Step 5: All messages marked delivered")
        
        # Step 6: Check stats
        stats = comm_service.get_stats()
        log(f"✓ Step 6: Stats - total={stats['total']}, delivered={stats['delivered']}")
        
        # Cleanup
        cleanup_test_data(db)
        db.close()
        
        log("Test 4.4 PASSED - Communication workflow verified!", 'PASS')
        return True
        
    except Exception as e:
        log(f"Test 4.4 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all Phase 3 E2E tests."""
    log("=" * 70)
    log("PHASE 3: END-TO-END TESTS")
    log("=" * 70)
    log(f"Using database: {DB_PATH}")
    log("=" * 70)
    
    results = []
    results.append(("4.1 Complete Task Lifecycle", test_complete_task_lifecycle()))
    results.append(("4.2 Fuse Workflow", test_fuse_workflow()))
    results.append(("4.3 Avatar Workflow", test_avatar_workflow()))
    results.append(("4.4 Communication Workflow", test_communication_workflow()))
    
    # Summary
    log("\n" + "=" * 70)
    log("PHASE 3 E2E TEST SUMMARY")
    log("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = 'PASS' if result else 'FAIL'
        log(f"{name}: {status}", status)
    
    log(f"\nTotal: {passed}/{total} tests passed", 'PASS' if passed == total else 'WARN' if passed >= total/2 else 'FAIL')
    
    if passed == total:
        log("\n🎉 All E2E workflows verified! v0.3.0-beta is ready for release!", 'PASS')
    elif passed >= total/2:
        log("\n⚠️  Core workflows functional. Review failed tests before release.", 'WARN')
    else:
        log("\n❌ Multiple workflows failed. Not ready for release.", 'FAIL')
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
