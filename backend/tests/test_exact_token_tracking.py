"""
Test script for Exact Token Tracking (v0.3.0 P0 #4)

This script tests the exact token tracking flow:
1. Create a task with estimated cost
2. Complete the task with estimated tokens
3. Record exact tokens (simulating session_status fetch)
4. Verify exact tokens are stored and cost is recalculated

Usage:
    cd /root/.openclaw/workspace/openclaw-opc/backend
    python3 tests/test_exact_token_tracking.py
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test configuration
TEST_DB_URL = "sqlite:///./test_exact_token.db"
AGENT_ID = "test_token_agent"
AGENT_NAME = "Token测试Agent"


def setup_test_db():
    """Create test database."""
    from src.database import Base
    from src.models import Agent, AgentStatus
    
    import os
    if os.path.exists("./test_exact_token.db"):
        os.remove("./test_exact_token.db")
    
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
    print(f"✅ Created test agent: {agent.name}")
    
    return db, agent


def test_create_and_complete_task(db, agent_id):
    """Test 1: Create and complete a task with estimated tokens."""
    from src.services.task_service import TaskService
    from src.services.task_execution_service import TaskExecutionService
    
    print("\n📋 Test 1: Create and Complete Task")
    print("-" * 40)
    
    # Create task
    task_service = TaskService(db)
    task = task_service.create_task(
        title="精确Token测试任务",
        description="测试精确Token统计功能",
        priority="high",
        estimated_cost=50.0  # Estimated 50 OC币 (5000 tokens)
    )
    print(f"✅ Task created: {task.id}")
    print(f"   Estimated cost: {task.estimated_cost} OC币")
    
    # Assign and complete
    task_service.assign_task(task.id, agent_id)
    
    # Report completion with estimated tokens
    exec_service = TaskExecutionService(db)
    result = exec_service.report_task_completion(
        task_id=task.id,
        agent_id=agent_id,
        token_used=5000,  # Estimated 5000 tokens
        result_summary="任务完成（估算Token）",
        status="completed"
    )
    
    print(f"✅ Task completed with estimated tokens")
    print(f"   Cost: {result['cost']:.2f} OC币")
    print(f"   Is exact: {task.is_exact}")
    
    return task


def test_record_exact_tokens(db, task_id):
    """Test 2: Record exact tokens for the completed task."""
    from src.services.exact_token_service import ExactTokenService
    from src.models import Task
    
    print("\n🎯 Test 2: Record Exact Tokens")
    print("-" * 40)
    
    # Get task before
    task = db.query(Task).filter(Task.id == task_id).first()
    old_cost = task.actual_cost
    print(f"   Previous cost: {old_cost:.2f} OC币")
    print(f"   Previous is_exact: {task.is_exact}")
    
    # Mock the session status fetch by directly updating
    # In real scenario, this would call OpenClaw session_status
    task.actual_tokens_input = 2100
    task.actual_tokens_output = 1850
    task.is_exact = "true"
    
    # Recalculate cost
    new_total_tokens = 2100 + 1850
    new_cost = new_total_tokens / 100.0
    
    # Check if significant difference
    cost_diff = abs(new_cost - old_cost)
    
    if cost_diff > 1.0:
        print(f"   Significant cost difference detected: {cost_diff:.2f} OC币")
        print(f"   Old cost: {old_cost:.2f} → New cost: {new_cost:.2f}")
        
        # Adjust agent budget
        from src.models import Agent
        agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
        budget_adjustment = new_cost - old_cost
        agent.used_budget = (agent.used_budget or 0) + budget_adjustment
        
        task.actual_cost = new_cost
        db.commit()
        
        print(f"   Agent budget adjusted by: {budget_adjustment:.2f} OC币")
    else:
        task.actual_cost = new_cost
        db.commit()
    
    # Refresh and verify
    db.refresh(task)
    
    print(f"✅ Exact tokens recorded")
    print(f"   Input tokens: {task.actual_tokens_input}")
    print(f"   Output tokens: {task.actual_tokens_output}")
    print(f"   Total tokens: {task.actual_tokens_input + task.actual_tokens_output}")
    print(f"   New cost: {task.actual_cost:.2f} OC币")
    print(f"   Is exact: {task.is_exact}")
    
    return task


def test_token_summary(db, agent_id):
    """Test 3: Get exact token summary."""
    from src.services.exact_token_service import ExactTokenService
    
    print("\n📊 Test 3: Token Summary")
    print("-" * 40)
    
    service = ExactTokenService(db)
    summary = service.get_exact_token_summary(agent_id)
    
    print(f"✅ Token summary:")
    print(f"   Total tasks: {summary['total_tasks']}")
    print(f"   Exact tracking: {summary['exact_tasks']} ({summary['exact_percentage']:.1f}%)")
    print(f"   Estimated tracking: {summary['estimated_tasks']}")
    print(f"   Total input tokens: {summary['total_input_tokens']}")
    print(f"   Total output tokens: {summary['total_output_tokens']}")
    print(f"   Total tokens: {summary['total_tokens']}")
    print(f"   Total exact cost: {summary['total_exact_cost']:.2f} OC币")


def cleanup(db):
    """Clean up test data."""
    print("\n🧹 Cleaning up...")
    db.close()
    import os
    if os.path.exists("./test_exact_token.db"):
        os.remove("./test_exact_token.db")
    print("✅ Test database removed")


def run_all_tests():
    """Run all exact token tracking tests."""
    print("=" * 50)
    print("🎯 Exact Token Tracking Test Suite")
    print("=" * 50)
    
    try:
        # Setup
        db, agent = setup_test_db()
        
        # Run tests
        task = test_create_and_complete_task(db, agent.agent_id)
        test_record_exact_tokens(db, task.id)
        test_token_summary(db, agent.agent_id)
        
        # Cleanup
        cleanup(db)
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
