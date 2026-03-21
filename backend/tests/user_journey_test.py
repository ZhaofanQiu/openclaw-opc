#!/usr/bin/env python3
"""
User Journey End-to-End Tests for OpenClaw OPC v0.3.0-beta
Simulates real user workflows from onboarding to daily operations
"""

import sys
import os
import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/backend')

# Test configuration
TEST_DB_PATH = '/tmp/opc_user_journey.db'
TEST_AVATAR_DIR = '/tmp/opc_journey_avatars'
BASE_URL = "http://localhost:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def log(msg, level='INFO'):
    colors = {
        'INFO': Colors.BLUE,
        'PASS': Colors.GREEN,
        'FAIL': Colors.RED,
        'WARN': Colors.YELLOW,
        'STEP': Colors.CYAN
    }
    color = colors.get(level, Colors.RESET)
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def setup_test_environment():
    """Setup clean test environment."""
    log("=" * 70)
    log("SETTING UP USER JOURNEY TEST ENVIRONMENT")
    log("=" * 70)
    
    # Clean up
    for path in [TEST_DB_PATH, TEST_AVATAR_DIR]:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    os.makedirs(TEST_AVATAR_DIR, exist_ok=True)
    
    # Create database
    from sqlalchemy import create_engine
    from src.database import Base
    
    engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
    Base.metadata.create_all(bind=engine)
    
    log(f"✓ Database: {TEST_DB_PATH}")
    log(f"✓ Avatar Dir: {TEST_AVATAR_DIR}")
    return engine

# =============================================================================
# SCENARIO 1: Documentation & Onboarding
# =============================================================================

def test_documentation_completeness():
    """Test 1.1: Verify documentation exists and is readable."""
    log("\n" + "=" * 70)
    log("SCENARIO 1: Documentation & Onboarding")
    log("=" * 70)
    
    docs_path = Path('/root/.openclaw/workspace/openclaw-opc')
    required_docs = [
        'README.md',
        'docs/API_REFERENCE.md',
        'docs/TEST_PLAN_v0.3.0.md',
    ]
    
    all_exist = True
    for doc in required_docs:
        full_path = docs_path / doc
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        log(f"{status} {doc} {'Found' if exists else 'MISSING'}", 'PASS' if exists else 'FAIL')
        all_exist = all_exist and exists
    
    # Check README content
    readme = docs_path / 'README.md'
    if readme.exists():
        content = readme.read_text()
        has_quickstart = 'quick start' in content.lower() or 'getting started' in content.lower()
        has_api_examples = '```' in content
        log(f"{'✓' if has_quickstart else '✗'} README has quick start guide", 'PASS' if has_quickstart else 'WARN')
        log(f"{'✓' if has_api_examples else '✗'} README has code examples", 'PASS' if has_api_examples else 'WARN')
    
    return all_exist

# =============================================================================
# SCENARIO 2: Company Setup (Partner Creation)
# =============================================================================

def test_company_setup():
    """Test 2.1-2.4: Company initialization with Partner."""
    log("\n" + "=" * 70)
    log("SCENARIO 2: Company Setup (Partner)")
    log("=" * 70)
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.agent_service import AgentService
        from src.services.avatar_service import AvatarService
        
        engine = setup_test_environment()
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Step 2.1: Create Partner
        log("\n[Step 2.1] Creating Partner Agent...")
        agent_service = AgentService(db)
        partner = agent_service.create_agent(
            name="公司合伙人 (Partner)",
            monthly_budget=10000.0
        )
        # Set as Partner level
        from sqlalchemy import text
        db.execute(text("UPDATE agents SET position_level = 5 WHERE id = :id"), {'id': partner.id})
        db.commit()
        log(f"✓ Partner created: ID={partner.id}, Budget={partner.monthly_budget} OC币")
        
        # Step 2.2: Verify Partner configuration
        log("\n[Step 2.2] Verifying Partner configuration...")
        db.refresh(partner)
        assert partner.monthly_budget == 10000.0, "Budget mismatch"
        log(f"✓ Partner budget confirmed: {partner.monthly_budget} OC币")
        
        # Step 2.3: Update Partner budget
        log("\n[Step 2.3] Updating Partner budget...")
        partner.monthly_budget = 15000.0
        db.commit()
        log(f"✓ Partner budget updated to: {partner.monthly_budget} OC币")
        
        # Step 2.4: Generate Partner Avatar
        log("\n[Step 2.4] Generating Partner Avatar...")
        avatar_service = AvatarService(db, upload_dir=Path(TEST_AVATAR_DIR))
        avatar = avatar_service.generate_system_avatar(partner.id, style='humanoid')
        avatar_url = avatar_service.get_avatar_url(avatar)
        log(f"✓ Partner avatar: {avatar_url}")
        
        # Save ID before closing session
        partner_id = partner.id
        
        db.close()
        log("\n✅ SCENARIO 2 PASSED - Company setup successful", 'PASS')
        return True, partner_id
        
    except Exception as e:
        log(f"\n❌ SCENARIO 2 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False, None

# =============================================================================
# SCENARIO 3: Employee Management (HR Workflow)
# =============================================================================

def test_employee_management(partner_id):
    """Test 3.1-3.7: Full employee lifecycle."""
    log("\n" + "=" * 70)
    log("SCENARIO 3: Employee Management")
    log("=" * 70)
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.agent_service import AgentService
        from src.services.avatar_service import AvatarService, AvatarSource
        from src.models import Agent
        from sqlalchemy import text
        
        engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        agent_service = AgentService(db)
        avatar_service = AvatarService(db, upload_dir=Path(TEST_AVATAR_DIR))
        
        # Step 3.1: Create regular employee
        log("\n[Step 3.1] Creating regular employee...")
        emp1 = agent_service.create_agent(
            name="张三 (Developer)",
            monthly_budget=3000.0
        )
        log(f"✓ Employee created: {emp1.name}, Budget={emp1.monthly_budget} OC币")
        
        # Step 3.2: Create senior employee
        log("\n[Step 3.2] Creating senior employee...")
        emp2 = agent_service.create_agent(
            name="李四 (Senior Developer)",
            monthly_budget=5000.0
        )
        db.execute(text("UPDATE agents SET position_level = 3 WHERE id = :id"), {'id': emp2.id})
        db.commit()
        log(f"✓ Senior employee created: {emp2.name}, Budget={emp2.monthly_budget} OC币")
        
        # Step 3.3: Generate system avatars
        log("\n[Step 3.3] Generating system avatars...")
        avatar1 = avatar_service.generate_system_avatar(emp1.id, style='robot')
        avatar2 = avatar_service.generate_system_avatar(emp2.id, style='alien')
        log(f"✓ {emp1.name} avatar: {avatar_service.get_avatar_url(avatar1)}")
        log(f"✓ {emp2.name} avatar: {avatar_service.get_avatar_url(avatar2)}")
        
        # Step 3.4: Upload custom avatar
        log("\n[Step 3.4] Uploading custom avatar...")
        # Create a simple test PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        avatar_up = avatar_service.save_uploaded_avatar(
            agent_id=emp1.id,
            file_data=png_data,
            filename="custom_avatar.png",
            content_type="image/png"
        )
        assert avatar_up.source == AvatarSource.UPLOADED.value
        log(f"✓ Custom avatar uploaded for {emp1.name}")
        
        # Step 3.5: Update employee budget
        log("\n[Step 3.5] Updating employee budget...")
        emp1.monthly_budget = 3500.0
        db.commit()
        log(f"✓ {emp1.name} budget updated to {emp1.monthly_budget} OC币")
        
        # Step 3.6: List employees
        log("\n[Step 3.6] Listing all employees...")
        employees = db.query(Agent).all()
        log(f"✓ Total employees: {len(employees)}")
        for emp in employees:
            log(f"   - {emp.name}: {emp.monthly_budget} OC币")
        
        # Step 3.7: Delete employee
        log("\n[Step 3.7] Deleting employee...")
        emp_id_to_delete = emp2.id
        emp2_name = emp2.name  # Save name before delete
        # Delete avatar first
        avatar_service.delete_avatar(emp_id_to_delete)
        # Delete agent
        db.execute(text("DELETE FROM agents WHERE id = :id"), {'id': emp_id_to_delete})
        db.commit()
        log(f"✓ Employee {emp2_name} deleted")
        
        # Save ID before closing
        emp1_id = emp1.id
        
        db.close()
        log("\n✅ SCENARIO 3 PASSED - Employee management successful", 'PASS')
        return True, emp1_id
        
    except Exception as e:
        log(f"\n❌ SCENARIO 3 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False, None

# =============================================================================
# SCENARIO 4: Task Management (Project Workflow)
# =============================================================================

def test_task_management(employee_id):
    """Test 4.1-4.7: Full task lifecycle."""
    log("\n" + "=" * 70)
    log("SCENARIO 4: Task Management")
    log("=" * 70)
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.budget_service import BudgetService
        from src.models import Task, TaskStatus
        from sqlalchemy import text
        
        engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        budget_service = BudgetService(db)
        
        # Step 4.1: Create simple task
        log("\n[Step 4.1] Creating simple task...")
        task1 = Task(
            id="task_001",
            title="实现用户登录功能",
            description="开发前端登录页面和后端API",
            estimated_cost=50.0,
            agent_id=employee_id,
            priority="high",
            status="assigned"
        )
        db.add(task1)
        db.commit()
        log(f"✓ Task created: {task1.title}, Budget={task1.estimated_cost} OC币")
        
        # Step 4.2: Create another task
        log("\n[Step 4.2] Creating low priority task...")
        task2 = Task(
            id="task_002",
            title="优化文档",
            description="更新API文档",
            estimated_cost=20.0,
            agent_id=employee_id,
            priority="low",
            status="pending"
        )
        db.add(task2)
        db.commit()
        log(f"✓ Task created: {task2.title}, Priority={task2.priority}")
        
        # Step 4.3: Start task
        log("\n[Step 4.3] Starting task...")
        task1.status = "in_progress"
        task1.started_at = datetime.utcnow()
        db.commit()
        log(f"✓ Task '{task1.title}' started")
        
        # Step 4.4: Record estimated consumption
        log("\n[Step 4.4] Recording estimated consumption...")
        # Update employee used_budget
        agent = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': employee_id}).fetchone()
        used = agent.used_budget + 30.0  # Simulated consumption
        db.execute(text("UPDATE agents SET used_budget = :used WHERE id = :id"), 
                   {'used': used, 'id': employee_id})
        db.commit()
        log(f"✓ Estimated consumption: 30 OC币")
        
        # Step 4.5: Record exact token consumption
        log("\n[Step 4.5] Recording exact token consumption...")
        transaction = budget_service.record_exact_consumption(
            agent_id=employee_id,
            task_id=task1.id,
            tokens_input=2000,
            tokens_output=1500,
            session_key="dev-session-001",
            description="实现登录功能的实际消耗"
        )
        # Update actual cost
        task1.actual_cost = abs(transaction.amount)
        task1.actual_tokens_input = transaction.actual_tokens_input
        task1.actual_tokens_output = transaction.actual_tokens_output
        task1.is_exact = "true"
        db.commit()
        log(f"✓ Exact consumption: {abs(transaction.amount)} OC币")
        log(f"✓ Tokens: {transaction.actual_tokens_input} in, {transaction.actual_tokens_output} out")
        
        # Step 4.6: Complete task
        log("\n[Step 4.6] Completing task...")
        task1.status = "completed"
        task1.completed_at = datetime.utcnow()
        task1.result_summary = "登录功能已实现，包含JWT认证"
        db.commit()
        log(f"✓ Task completed: {task1.result_summary}")
        
        # Step 4.7: List tasks
        log("\n[Step 4.7] Listing all tasks...")
        tasks = db.query(Task).all()
        log(f"✓ Total tasks: {len(tasks)}")
        for t in tasks:
            status_icon = "✓" if t.status == "completed" else "○"
            log(f"   {status_icon} [{t.status}] {t.title}")
        
        # Save ID before closing
        task1_id = task1.id
        
        db.close()
        log("\n✅ SCENARIO 4 PASSED - Task management successful", 'PASS')
        return True, task1_id
        
    except Exception as e:
        log(f"\n❌ SCENARIO 4 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False, None

# =============================================================================
# SCENARIO 5: Budget & Fuse Management
# =============================================================================

def test_budget_and_fuse(employee_id, task_id):
    """Test 5.1-5.5: Budget control and fuse handling."""
    log("\n" + "=" * 70)
    log("SCENARIO 5: Budget & Fuse Management")
    log("=" * 70)
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.fuse_service import FuseService
        from src.services.budget_service import BudgetService
        from src.models import BudgetTransaction, Task
        from sqlalchemy import text
        
        engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        fuse_service = FuseService(db)
        budget_service = BudgetService(db)
        
        # Step 5.1: Check budget report
        log("\n[Step 5.1] Checking budget report...")
        agent = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': employee_id}).fetchone()
        remaining = agent.monthly_budget - agent.used_budget
        usage_pct = (agent.used_budget / agent.monthly_budget) * 100
        log(f"✓ Budget Report for {agent.name}:")
        log(f"   - Monthly: {agent.monthly_budget} OC币")
        log(f"   - Used: {agent.used_budget:.2f} OC币 ({usage_pct:.1f}%)")
        log(f"   - Remaining: {remaining:.2f} OC币")
        
        # Step 5.2: Create a task that will trigger fuse
        log("\n[Step 5.2] Creating task that exceeds budget...")
        # Exhaust budget first
        db.execute(text("UPDATE agents SET used_budget = monthly_budget WHERE id = :id"), 
                   {'id': employee_id})
        db.commit()
        
        big_task = Task(
            id="big_task_001",
            title="大型重构项目",
            description="需要大量预算的任务",
            estimated_cost=100.0,
            agent_id=employee_id,
            priority="urgent",
            status="pending"
        )
        db.add(big_task)
        db.commit()
        log(f"✓ Created big task requiring {big_task.estimated_cost} OC币")
        
        # Step 5.3: Trigger fuse
        log("\n[Step 5.3] Triggering budget fuse...")
        agent = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': employee_id}).fetchone()
        fuse_event = fuse_service.record_fuse_event(
            agent_id=employee_id,
            task_id=big_task.id,
            fuse_type="fuse",
            threshold_percentage=100.0,
            budget_used=agent.used_budget,
            budget_total=agent.monthly_budget
        )
        log(f"✓ Fuse triggered: {fuse_event.id}")
        log(f"✓ Status: {fuse_event.status}")
        
        # Step 5.4: Resolve fuse by adding budget
        log("\n[Step 5.4] Resolving fuse (adding budget)...")
        # Resolve fuse
        fuse_service.resolve_event(
            event_id=fuse_event.id,
            action="add_budget",
            resolved_by="partner",
            resolution_note="项目重要，紧急增加预算"
        )
        # Add budget
        db.execute(text("UPDATE agents SET monthly_budget = monthly_budget + 500 WHERE id = :id"),
                   {'id': employee_id})
        db.commit()
        
        agent = db.execute(text("SELECT * FROM agents WHERE id = :id"), {'id': employee_id}).fetchone()
        new_remaining = agent.monthly_budget - agent.used_budget
        log(f"✓ Budget increased by 500 OC币")
        log(f"✓ New monthly budget: {agent.monthly_budget} OC币")
        log(f"✓ Available: {new_remaining} OC币")
        
        # Step 5.5: View transaction history
        log("\n[Step 5.5] Viewing transaction history...")
        transactions = db.query(BudgetTransaction).filter(
            BudgetTransaction.agent_id == employee_id
        ).all()
        log(f"✓ Total transactions: {len(transactions)}")
        for t in transactions:
            log(f"   - {t.transaction_type}: {t.amount} OC币 - {t.description[:30]}...")
        
        db.close()
        log("\n✅ SCENARIO 5 PASSED - Budget & fuse management successful", 'PASS')
        return True
        
    except Exception as e:
        log(f"\n❌ SCENARIO 5 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

# =============================================================================
# SCENARIO 6: Communication & Collaboration
# =============================================================================

def test_communication(partner_id, employee_id):
    """Test 6.1-6.5: Agent communication features."""
    log("\n" + "=" * 70)
    log("SCENARIO 6: Communication & Collaboration")
    log("=" * 70)
    
    try:
        from sqlalchemy.orm import sessionmaker
        from src.services.communication_service import CommunicationService
        
        engine = create_engine(f'sqlite:///{TEST_DB_PATH}')
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        comm_service = CommunicationService(db)
        
        # Step 6.1: Partner sends message to employee
        log("\n[Step 6.1] Partner sending direct message...")
        msg1 = comm_service.send_message(
            sender_id=partner_id,
            recipient_id=employee_id,
            content="本周五下午3点进行代码评审，请准备好你的进度报告。",
            subject="代码评审通知",
            priority="high"
        )
        log(f"✓ Message sent: {msg1.id}")
        
        # Step 6.2: Employee checks inbox
        log("\n[Step 6.2] Employee checking inbox...")
        inbox = comm_service.get_messages(recipient_id=employee_id)
        log(f"✓ Employee has {len(inbox)} message(s)")
        for m in inbox:
            log(f"   - [{m.priority}] {m.subject}: {m.content[:30]}...")
        
        # Step 6.3: Send broadcast
        log("\n[Step 6.3] Sending broadcast to all employees...")
        # Create another employee for broadcast test
        from src.services.agent_service import AgentService
        agent_service = AgentService(db)
        emp2 = agent_service.create_agent(name="王五 (Tester)", monthly_budget=2000.0)
        
        broadcast_msgs = comm_service.broadcast_message(
            sender_id=partner_id,
            recipient_ids=[employee_id, emp2.id],
            content="全公司通知：下周一开始使用新的开发流程，请大家提前阅读文档。",
            subject="流程变更通知"
        )
        log(f"✓ Broadcast sent to {len(broadcast_msgs)} employees")
        
        # Step 6.4: Task notification
        log("\n[Step 6.4] Sending task assignment notification...")
        msg3 = comm_service.send_message(
            sender_id=partner_id,
            recipient_id=employee_id,
            content="您被分配了新任务：紧急修复生产环境Bug",
            subject="新任务分配",
            priority="urgent"
        )
        log(f"✓ Task notification sent: {msg3.id}")
        
        # Step 6.5: Check message stats
        log("\n[Step 6.5] Checking communication stats...")
        stats = comm_service.get_stats()
        log(f"✓ Communication stats:")
        for key, value in stats.items():
            log(f"   - {key}: {value}")
        
        db.close()
        log("\n✅ SCENARIO 6 PASSED - Communication successful", 'PASS')
        return True
        
    except Exception as e:
        log(f"\n❌ SCENARIO 6 FAILED: {e}", 'FAIL')
        import traceback
        traceback.print_exc()
        return False

# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_user_journey_tests():
    """Run all user journey tests in sequence."""
    log("\n" + "🚀" * 35)
    log("OPENCLAW OPC v0.3.0-beta USER JOURNEY TESTS")
    log("🚀" * 35)
    log("\nThis test suite simulates real user workflows")
    log("from company setup to daily operations.")
    log("=" * 70)
    
    results = []
    partner_id = None
    employee_id = None
    task_id = None
    
    # Scenario 1: Documentation
    results.append(("1. Documentation", test_documentation_completeness()))
    
    # Scenario 2: Company Setup
    success, partner_id = test_company_setup()
    results.append(("2. Company Setup", success))
    
    if not partner_id:
        log("\n❌ Critical failure: Partner creation failed. Stopping tests.", 'FAIL')
        return results
    
    # Scenario 3: Employee Management
    success, employee_id = test_employee_management(partner_id)
    results.append(("3. Employee Management", success))
    
    if not employee_id:
        log("\n❌ Critical failure: Employee creation failed. Stopping tests.", 'FAIL')
        return results
    
    # Scenario 4: Task Management
    success, task_id = test_task_management(employee_id)
    results.append(("4. Task Management", success))
    
    # Scenario 5: Budget & Fuse
    success = test_budget_and_fuse(employee_id, task_id or "task_001")
    results.append(("5. Budget & Fuse", success))
    
    # Scenario 6: Communication
    success = test_communication(partner_id, employee_id)
    results.append(("6. Communication", success))
    
    # Summary
    log("\n" + "=" * 70)
    log("USER JOURNEY TEST SUMMARY")
    log("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = 'PASS' if result else 'FAIL'
        log(f"{name}: {status}", status)
    
    log(f"\nTotal: {passed}/{total} scenarios passed", 'PASS' if passed == total else 'FAIL')
    
    if passed == total:
        log("\n🎉 ALL USER JOURNEYS PASSED!", 'PASS')
        log("✅ v0.3.0-beta is ready for production use!", 'PASS')
    elif passed >= total * 0.8:
        log("\n⚠️ Most journeys passed. Minor issues to address.", 'WARN')
    else:
        log("\n❌ Multiple failures. Not ready for release.", 'FAIL')
    
    # Cleanup
    log("\nCleaning up test files...")
    for path in [TEST_DB_PATH, TEST_AVATAR_DIR]:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    log("✓ Cleanup complete")
    
    return results

if __name__ == "__main__":
    from sqlalchemy import create_engine
    results = run_user_journey_tests()
    sys.exit(0 if all(r for _, r in results) else 1)
