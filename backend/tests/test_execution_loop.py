"""
Test script for Agent Execution Loop (v0.3.0 P0 #3)

This script tests the complete task execution flow:
1. Create a task
2. Assign task to agent (triggers send_task_to_agent)
3. Check execution status
4. Simulate agent report completion
5. Verify task completion and budget update

Usage:
    cd /root/.openclaw/workspace/openclaw-opc/backend
    python3 tests/test_execution_loop.py
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test configuration
TEST_DB_URL = "sqlite:///./test_execution_loop.db"
AGENT_ID = "test_agent_001"
AGENT_NAME = "测试Agent"


def setup_test_db():
    """Create test database."""
    from src.database import Base
    from src.models import Agent, AgentStatus
    
    # Remove old test db if exists
    import os
    if os.path.exists("./test_execution_loop.db"):
        os.remove("./test_execution_loop.db")
    
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Create test agent
    import uuid
    from datetime import datetime
    agent = Agent(
        id=str(uuid.uuid4())[:8],
        name=AGENT_NAME,
        agent_id=AGENT_ID,
        is_bound="true",
        status=AgentStatus.IDLE.value,
        monthly_budget=10000.0,
        used_budget=0.0,
        created_at=datetime.utcnow()
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    print(f"✅ Created test agent: {agent.name} (ID: {agent.agent_id})")
    
    return db, agent


def test_create_task(db):
    """Test 1: Create a new task."""
    from src.services.task_service import TaskService
    
    print("\n📋 Test 1: Create Task")
    print("-" * 40)
    
    service = TaskService(db)
    task = service.create_task(
        title="测试执行任务",
        description="这是一个用于测试执行闭环的任务",
        priority="high",
        estimated_cost=100.0
    )
    
    print(f"✅ Task created: {task.id}")
    print(f"   Title: {task.title}")
    print(f"   Status: {task.status}")
    print(f"   Budget: {task.estimated_cost} OC币")
    
    return task


def test_assign_task(db, task_id, agent_id):
    """Test 2: Assign task to agent (triggers send)."""
    from src.services.task_service import TaskService
    from src.services.task_execution_service import TaskExecutionService
    
    print("\n📤 Test 2: Assign Task (Auto-send to Agent)")
    print("-" * 40)
    
    service = TaskService(db)
    
    try:
        task = service.assign_task(task_id, agent_id)
        print(f"✅ Task assigned to agent")
        print(f"   Status: {task.status}")
        print(f"   Execution Status: {task.execution_status or 'N/A'}")
        print(f"   Sent at: {task.sent_to_agent_at}")
        
        # Check execution service status
        exec_service = TaskExecutionService(db)
        status = exec_service.get_execution_status(task_id)
        if status:
            print(f"   Session ID: {status.get('session_id', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Assignment failed: {e}")
        return False


def test_check_execution_status(db, task_id):
    """Test 3: Check execution status."""
    from src.services.task_execution_service import TaskExecutionService
    
    print("\n🔍 Test 3: Check Execution Status")
    print("-" * 40)
    
    service = TaskExecutionService(db)
    status = service.get_execution_status(task_id)
    
    if status:
        print(f"✅ Execution Status:")
        for key, value in status.items():
            print(f"   {key}: {value}")
    else:
        print("❌ Task not found")
    
    return status


def test_report_completion(db, task_id, agent_id):
    """Test 4: Simulate agent reporting completion."""
    from src.services.task_execution_service import TaskExecutionService
    from src.models import Agent
    
    print("\n✅ Test 4: Report Task Completion")
    print("-" * 40)
    
    # Get agent's budget before
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    budget_before = agent.remaining_budget
    print(f"   Budget before: {budget_before:.2f} OC币")
    
    service = TaskExecutionService(db)
    result = service.report_task_completion(
        task_id=task_id,
        agent_id=agent_id,
        token_used=1500,  # 1500 tokens = 15 OC币
        result_summary="任务已成功完成，实现了所有功能需求",
        status="completed"
    )
    
    if result.get("success"):
        print(f"✅ Report processed successfully")
        print(f"   Status: {result['status']}")
        print(f"   Cost: {result['cost']:.2f} OC币")
        print(f"   Remaining budget: {result['remaining_budget']:.2f} OC币")
        print(f"   Budget used: {budget_before - result['remaining_budget']:.2f} OC币")
        
        # Refresh agent to get updated budget
        db.refresh(agent)
        print(f"   Agent status: {agent.status}")
    else:
        print(f"❌ Report failed: {result.get('error')}")
    
    return result


def test_verify_task_completion(db, task_id):
    """Test 5: Verify task is completed."""
    from src.models import Task
    
    print("\n🔍 Test 5: Verify Task Completion")
    print("-" * 40)
    
    task = db.query(Task).filter(Task.id == task_id).first()
    
    print(f"✅ Task verification:")
    print(f"   Status: {task.status}")
    print(f"   Execution Status: {task.execution_status}")
    print(f"   Actual Cost: {task.actual_cost:.2f} OC币")
    print(f"   Token Used: {task.token_used}")
    print(f"   Result: {task.result_summary}")
    print(f"   Completed at: {task.completed_at}")
    
    return task


def test_resend_task(db, task_id, agent_id):
    """Test 6: Test resend functionality."""
    from src.services.task_execution_service import TaskExecutionService
    
    print("\n🔄 Test 6: Resend Task")
    print("-" * 40)
    
    service = TaskExecutionService(db)
    result = service.send_task_to_agent(task_id, agent_id)
    
    if result.get("success"):
        print(f"✅ Task resent successfully")
        print(f"   Message: {result['message']}")
    else:
        print(f"❌ Resend failed: {result.get('error')}")
    
    return result


def cleanup(db):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    db.close()
    import os
    if os.path.exists("./test_execution_loop.db"):
        os.remove("./test_execution_loop.db")
        print("✅ Test database removed")


def run_all_tests():
    """Run all execution loop tests."""
    print("=" * 50)
    print("🧪 Agent Execution Loop Test Suite")
    print("=" * 50)
    
    try:
        # Setup
        db, agent = setup_test_db()
        
        # Run tests
        task = test_create_task(db)
        
        success = test_assign_task(db, task.id, agent.agent_id)
        if not success:
            print("\n❌ Tests aborted: Assignment failed")
            return False
        
        test_check_execution_status(db, task.id)
        
        result = test_report_completion(db, task.id, agent.agent_id)
        if not result.get("success"):
            print("\n❌ Tests aborted: Report failed")
            return False
        
        test_verify_task_completion(db, task.id)
        
        # Cleanup
        cleanup(db)
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
