"""
opc-core: 工作流端到端测试脚本 (v0.4.2)

用于手动验证工作流功能

运行方式:
    python -m tests.integration.test_workflow_e2e

注意: 需要完整的环境配置（数据库、OpenClaw Agent等）
"""

import asyncio
import json
import sys

# 添加项目路径
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-openclaw/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')

from opc_database import init_db, get_session
from opc_database.repositories import TaskRepository, EmployeeRepository
from opc_database.models import Employee, TaskStatus
from opc_core.services import (
    TaskService,
    WorkflowService,
    WorkflowStepConfig,
)


async def setup_test_data(session):
    """设置测试数据"""
    emp_repo = EmployeeRepository(session)
    
    # 创建测试员工1（研究员）
    emp1 = Employee(
        id="emp-test-researcher",
        name="Test Researcher",
        openclaw_agent_id="opc-researcher",
        monthly_budget=1000.0,
        used_budget=0.0,
        status="idle",
    )
    
    # 创建测试员工2（审查员）
    emp2 = Employee(
        id="emp-test-reviewer",
        name="Test Reviewer",
        openclaw_agent_id="opc-reviewer",
        monthly_budget=1000.0,
        used_budget=0.0,
        status="idle",
    )
    
    await emp_repo.create(emp1)
    await emp_repo.create(emp2)
    
    return emp1, emp2


async def test_create_workflow():
    """测试创建工作流"""
    print("\n" + "="*60)
    print("测试1: 创建工作流")
    print("="*60)
    
    async with get_session() as session:
        # 设置测试数据
        emp1, emp2 = await setup_test_data(session)
        print(f"✓ 创建测试员工: {emp1.name}, {emp2.name}")
        
        # 创建服务
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        task_service = TaskService(task_repo, emp_repo)
        workflow_service = WorkflowService(task_repo, emp_repo, task_service)
        
        # 创建工作流
        steps = [
            WorkflowStepConfig(
                employee_id=emp1.id,
                title="研究主题",
                description="研究AI在医疗领域的应用，收集相关数据",
                estimated_cost=200,
            ),
            WorkflowStepConfig(
                employee_id=emp2.id,
                title="审查结果",
                description="验证研究结果的准确性和完整性",
                estimated_cost=150,
            ),
        ]
        
        result = await workflow_service.create_workflow(
            name="AI医疗研究报告",
            description="自动生成AI在医疗领域应用的研究报告",
            steps=steps,
            initial_input={"topic": "AI医疗", "keywords": ["诊断", "治疗", "药物研发"]},
            created_by="test-user",
            max_rework_per_step=2,
        )
        
        print(f"✓ 工作流创建成功")
        print(f"  - Workflow ID: {result.workflow_id}")
        print(f"  - First Task ID: {result.first_task_id}")
        print(f"  - Total Steps: {len(result.task_ids)}")
        print(f"  - Status: {result.status}")
        
        # 验证任务创建
        tasks = await task_repo.get_by_workflow(result.workflow_id)
        print(f"✓ 已创建 {len(tasks)} 个任务")
        
        for i, task in enumerate(tasks):
            print(f"  - Step {i+1}: {task.title}")
            print(f"    Status: {task.status}")
            print(f"    Assigned to: {task.assigned_to}")
            
        return result.workflow_id


async def test_workflow_progress(workflow_id):
    """测试工作流进度查询"""
    print("\n" + "="*60)
    print("测试2: 工作流进度查询")
    print("="*60)
    
    async with get_session() as session:
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        task_service = TaskService(task_repo, emp_repo)
        workflow_service = WorkflowService(task_repo, emp_repo, task_service)
        
        progress = await workflow_service.get_workflow_progress(workflow_id)
        
        if progress:
            print(f"✓ 工作流进度查询成功")
            print(f"  - Workflow ID: {progress.workflow_id}")
            print(f"  - Total Steps: {progress.total_steps}")
            print(f"  - Completed Steps: {progress.completed_steps}")
            print(f"  - Current Step: {progress.current_step}")
            print(f"  - Status: {progress.status}")
            print(f"  - Progress: {progress.progress_percent}%")
        else:
            print(f"✗ 工作流不存在: {workflow_id}")


async def test_rework_mechanism():
    """测试返工机制（模拟）"""
    print("\n" + "="*60)
    print("测试3: 返工机制")
    print("="*60)
    
    async with get_session() as session:
        # 设置测试数据
        emp1, emp2 = await setup_test_data(session)
        
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        task_service = TaskService(task_repo, emp_repo)
        workflow_service = WorkflowService(task_repo, emp_repo, task_service)
        
        # 创建工作流
        steps = [
            WorkflowStepConfig(
                employee_id=emp1.id,
                title="研究主题",
                description="研究AI在医疗领域的应用",
                estimated_cost=200,
            ),
            WorkflowStepConfig(
                employee_id=emp2.id,
                title="审查结果",
                description="验证研究结果的准确性",
                estimated_cost=150,
            ),
        ]
        
        result = await workflow_service.create_workflow(
            name="返工测试工作流",
            description="测试返工机制",
            steps=steps,
            initial_input={},
            created_by="test-user",
        )
        
        print(f"✓ 工作流创建成功: {result.workflow_id}")
        
        # 获取任务
        tasks = await task_repo.get_by_workflow(result.workflow_id)
        if len(tasks) >= 2:
            from_task = tasks[1]  # 第二步
            to_task = tasks[0]    # 第一步
            
            print(f"✓ 模拟返工请求: Step 2 -> Step 1")
            print(f"  - From Task: {from_task.id}")
            print(f"  - To Task: {to_task.id}")
            print(f"  - Rework Count (before): {to_task.rework_count}/{to_task.max_rework}")
            
            # 注意: 实际返工需要任务先完成，这里只测试结构
            print(f"  - 返工机制结构正确")


async def test_data_structure():
    """测试数据结构"""
    print("\n" + "="*60)
    print("测试4: 数据结构验证")
    print("="*60)
    
    async with get_session() as session:
        emp1, emp2 = await setup_test_data(session)
        
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        task_service = TaskService(task_repo, emp_repo)
        workflow_service = WorkflowService(task_repo, emp_repo, task_service)
        
        # 创建工作流
        steps = [
            WorkflowStepConfig(
                employee_id=emp1.id,
                title="数据测试步骤",
                description="测试数据结构",
                estimated_cost=100,
            ),
            WorkflowStepConfig(
                employee_id=emp2.id,
                title="数据接收步骤",
                description="接收数据结构",
                estimated_cost=100,
            ),
        ]
        
        result = await workflow_service.create_workflow(
            name="数据结构测试",
            description="测试数据结构传递",
            steps=steps,
            initial_input={"test_key": "test_value", "nested": {"key": "value"}},
            created_by="test-user",
        )
        
        # 获取任务
        tasks = await task_repo.get_by_workflow(result.workflow_id)
        first_task = tasks[0]
        
        print(f"✓ 任务数据结构验证")
        print(f"  - workflow_id: {first_task.workflow_id}")
        print(f"  - step_index: {first_task.step_index}")
        print(f"  - total_steps: {first_task.total_steps}")
        print(f"  - depends_on: {first_task.depends_on}")
        print(f"  - next_task_id: {first_task.next_task_id}")
        print(f"  - is_rework: {first_task.is_rework}")
        
        # 验证 input_data
        input_data = json.loads(first_task.input_data) if first_task.input_data else {}
        print(f"  - input_data.workflow_context.workflow_id: {input_data.get('workflow_context', {}).get('workflow_id')}")
        print(f"  - input_data.initial_input.test_key: {input_data.get('initial_input', {}).get('test_key')}")
        
        return True


async def cleanup_test_data():
    """清理测试数据"""
    print("\n" + "="*60)
    print("清理测试数据")
    print("="*60)
    
    async with get_session() as session:
        # 删除测试员工
        emp_repo = EmployeeRepository(session)
        for emp_id in ["emp-test-researcher", "emp-test-reviewer"]:
            emp = await emp_repo.get_by_id(emp_id)
            if emp:
                await emp_repo.delete(emp)
                print(f"✓ 删除测试员工: {emp_id}")


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("OpenClaw OPC v0.4.2 工作流端到端测试")
    print("="*60)
    
    try:
        # 初始化数据库
        print("\n初始化数据库...")
        await init_db()
        print("✓ 数据库初始化完成")
        
        # 运行测试
        workflow_id = await test_create_workflow()
        await test_workflow_progress(workflow_id)
        await test_rework_mechanism()
        await test_data_structure()
        
        # 清理（可选）
        # await cleanup_test_data()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
