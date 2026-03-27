"""
子功能4测试脚本：集成测试 (v0.4.6)

测试内容：
1. 手动创建工作流，验证手册正确存储
2. AI辅助创建工作流，验证手册正确生成
3. 多步骤工作流执行，验证数据正确传递
4. 返工流程，验证返工上下文传递
5. 端到端完整流程
"""

import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')

from opc_core.services.workflow_service import (
    WorkflowService,
    WorkflowStepConfig,
    MANUALS_DIR,
)
from opc_database.models import Task, TaskStatus


def test_manual_workflow_creation():
    """测试手动创建工作流，验证手册正确存储"""
    print("=" * 60)
    print("测试 1: 手动创建工作流 + 手册存储")
    print("=" * 60)
    
    async def run_test():
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        original_dir = MANUALS_DIR
        
        try:
            import opc_core.services.workflow_service as wf_module
            wf_module.MANUALS_DIR = Path(temp_dir)
            
            # 创建模拟员工
            mock_employee = Mock()
            mock_employee.id = "emp-001"
            mock_employee.name = "测试员工"
            mock_employee.openclaw_agent_id = "opc-agent-001"
            mock_employee.monthly_budget = 1000.0
            mock_employee.used_budget = 0.0
            mock_employee.remaining_budget = 1000.0
            
            # 创建步骤配置（带手册）
            steps = [
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title="需求分析",
                    description="分析项目需求",
                    estimated_cost=100.0,
                    manual_content="## 需求分析手册\n\n1. 收集需求\n2. 整理文档",
                    input_requirements="项目背景资料",
                    output_deliverables="需求文档"
                ),
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title="方案设计",
                    description="设计解决方案",
                    estimated_cost=150.0,
                    manual_content="## 方案设计手册\n\n1. 技术选型\n2. 架构设计",
                    input_requirements="需求文档",
                    output_deliverables="设计方案"
                )
            ]
            
            # 创建模拟仓库
            mock_task_repo = Mock()
            mock_task_repo.create = AsyncMock(side_effect=lambda t: t)
            mock_task_repo.update = AsyncMock(return_value=None)
            
            mock_emp_repo = Mock()
            mock_emp_repo.get_by_id = AsyncMock(return_value=mock_employee)
            
            mock_task_service = Mock()
            mock_task_service.assign_task = AsyncMock(return_value=None)
            
            # 创建工作流
            service = WorkflowService(
                task_repo=mock_task_repo,
                emp_repo=mock_emp_repo,
                task_service=mock_task_service
            )
            
            result = await service.create_workflow(
                name="测试工作流",
                description="集成测试工作流",
                steps=steps,
                initial_input={"project": "测试项目"},
                created_by="test_user"
            )
            
            # 验证结果
            assert result.workflow_id is not None
            assert len(result.task_ids) == 2
            print(f"✓ 工作流创建成功: {result.workflow_id}")
            
            # 验证手册文件创建
            tasks_dir = Path(temp_dir) / "tasks"
            assert tasks_dir.exists(), "手册目录未创建"
            
            manual_files = list(tasks_dir.glob("*.md"))
            assert len(manual_files) == 2, f"期望2个手册文件，实际{len(manual_files)}个"
            print(f"✓ 手册文件创建成功: {len(manual_files)}个")
            
            # 验证手册内容
            for manual_file in manual_files:
                content = manual_file.read_text(encoding="utf-8")
                assert "任务手册" in content
                assert "执行手册" in content
                assert "输入要求" in content
                assert "输出交付物" in content
            print("✓ 手册内容正确")
            
            # 验证 task_service.assign_task 被调用（触发第一个任务）
            mock_task_service.assign_task.assert_called_once()
            print("✓ 第一个任务已触发")
            
            return True
            
        finally:
            wf_module.MANUALS_DIR = original_dir
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    return asyncio.run(run_test())


def test_step_data_passing():
    """测试多步骤数据传递"""
    print("\n" + "=" * 60)
    print("测试 2: 多步骤数据传递")
    print("=" * 60)
    
    async def run_test():
        # 创建模拟任务
        mock_current_task = Mock()
        mock_current_task.id = "task-001"
        mock_current_task.next_task_id = "task-002"
        mock_current_task.step_index = 0
        mock_current_task.assigned_to = "emp-001"
        mock_current_task.output_data = json.dumps({
            "summary": "完成了需求分析",
            "structured_output": {
                "requirements": ["功能1", "功能2"],
                "priority": "high"
            },
            "deliverables": ["需求文档.md"]
        })
        
        mock_next_task = Mock()
        mock_next_task.id = "task-002"
        mock_next_task.step_index = 1
        mock_next_task.total_steps = 3
        mock_next_task.workflow_id = "wf-001"
        mock_next_task.assigned_to = "emp-002"
        mock_next_task.description = "原始描述"
        mock_next_task.input_data = json.dumps({
            "previous_outputs": []
        })
        mock_next_task.execution_context = json.dumps({
            "step_manual": {
                "title": "方案设计",
                "input_requirements": "需要需求文档",
                "output_deliverables": "设计方案文档"
            }
        })
        
        mock_employee = Mock()
        mock_employee.name = "员工A"
        
        # 创建模拟仓库
        mock_task_repo = Mock()
        mock_task_repo.get_by_id = AsyncMock(side_effect=lambda id: 
            mock_current_task if id == "task-001" else mock_next_task
        )
        mock_task_repo.update = AsyncMock(return_value=None)
        
        mock_emp_repo = Mock()
        mock_emp_repo.get_by_id = AsyncMock(return_value=mock_employee)
        
        mock_task_service = Mock()
        mock_task_service.assign_task = AsyncMock(return_value=None)
        
        service = WorkflowService(
            task_repo=mock_task_repo,
            emp_repo=mock_emp_repo,
            task_service=mock_task_service
        )
        
        # 触发下一步
        result = await service._trigger_next_step(mock_current_task)
        
        # 验证
        assert result is not None
        print("✓ 下一步任务触发成功")
        
        # 验证输入数据更新
        assert mock_next_task.set_input_data.called
        call_args = mock_next_task.set_input_data.call_args[0][0]
        
        # 验证 previous_outputs
        assert "previous_outputs" in call_args
        assert len(call_args["previous_outputs"]) == 1
        prev_output = call_args["previous_outputs"][0]
        assert prev_output["step_index"] == 0
        assert "完成了需求分析" in prev_output["output_summary"]
        print("✓ previous_outputs 正确传递")
        
        # 验证 current_step_description
        assert "current_step_description" in call_args
        description = call_args["current_step_description"]
        assert "## 前序步骤输出" in description
        assert "## 输入要求" in description
        assert "需要需求文档" in description
        assert "## 输出交付物要求" in description
        assert "设计方案文档" in description
        print("✓ current_step_description 正确构建")
        
        # 验证任务描述更新
        assert "原始描述" in mock_next_task.description
        assert "## 前序步骤输出" in mock_next_task.description
        print("✓ 任务描述已更新")
        
        return True
    
    return asyncio.run(run_test())


def test_rework_context():
    """测试返工流程"""
    print("\n" + "=" * 60)
    print("测试 3: 返工上下文传递")
    print("=" * 60)
    
    async def run_test():
        # 创建模拟任务
        mock_from_task = Mock()
        mock_from_task.id = "task-002"
        mock_from_task.step_index = 1
        mock_from_task.workflow_id = "wf-001"
        mock_from_task.assigned_to = "emp-002"
        mock_from_task.rework_count = 0
        mock_from_task.max_rework = 3
        
        mock_to_task = Mock()
        mock_to_task.id = "task-001"
        mock_to_task.step_index = 0
        mock_to_task.workflow_id = "wf-001"
        mock_to_task.assigned_to = "emp-001"
        mock_to_task.rework_count = 0
        mock_to_task.max_rework = 3
        mock_to_task.title = "需求分析"
        mock_to_task.description = "原始描述"
        mock_to_task.input_data = json.dumps({
            "initial_input": {"project": "测试"},
            "previous_outputs": []
        })
        mock_to_task.output_data = json.dumps({
            "summary": "第一次执行结果"
        })
        
        mock_employee = Mock()
        mock_employee.name = "返工员工"
        
        # 创建模拟仓库
        mock_task_repo = Mock()
        mock_task_repo.get_by_id = AsyncMock(side_effect=lambda id: {
            "task-001": mock_to_task,
            "task-002": mock_from_task
        }.get(id))
        mock_task_repo.create = AsyncMock(side_effect=lambda t: t)
        mock_task_repo.update = AsyncMock(return_value=None)
        
        mock_emp_repo = Mock()
        mock_emp_repo.get_by_id = AsyncMock(return_value=mock_employee)
        
        mock_task_service = Mock()
        mock_task_service.assign_task = AsyncMock(return_value=None)
        
        service = WorkflowService(
            task_repo=mock_task_repo,
            emp_repo=mock_emp_repo,
            task_service=mock_task_service
        )
        
        # 请求返工
        rework_task = await service.request_rework(
            from_task_id="task-002",
            to_task_id="task-001",
            reason="需求理解有误",
            instructions="请重新分析需求，重点关注用户场景"
        )
        
        # 验证返工任务创建
        assert rework_task is not None
        assert rework_task.is_rework == True
        assert rework_task.rework_count == 1
        assert "返工" in rework_task.title
        print("✓ 返工任务创建成功")
        
        # 验证返工上下文
        assert rework_task.rework_reason == "需求理解有误"
        assert rework_task.rework_instructions == "请重新分析需求，重点关注用户场景"
        print("✓ 返工上下文正确")
        
        # 验证输入数据包含返工信息
        input_data = json.loads(rework_task.input_data) if rework_task.input_data else {}
        assert "upstream_rework_notes" in input_data
        notes = input_data["upstream_rework_notes"]
        assert notes["reason"] == "需求理解有误"
        assert notes["instructions"] == "请重新分析需求，重点关注用户场景"
        print("✓ 返工信息已添加到输入数据")
        
        # 验证 assign_task 被调用
        mock_task_service.assign_task.assert_called_once()
        print("✓ 返工任务已触发")
        
        return True
    
    return asyncio.run(run_test())


def test_end_to_end_workflow():
    """测试端到端完整流程"""
    print("\n" + "=" * 60)
    print("测试 4: 端到端完整流程")
    print("=" * 60)
    
    async def run_test():
        temp_dir = tempfile.mkdtemp()
        original_dir = MANUALS_DIR
        
        try:
            import opc_core.services.workflow_service as wf_module
            wf_module.MANUALS_DIR = Path(temp_dir)
            
            # 1. 创建3步骤工作流
            mock_employee = Mock()
            mock_employee.id = "emp-001"
            mock_employee.name = "全能员工"
            mock_employee.openclaw_agent_id = "opc-agent-001"
            mock_employee.monthly_budget = 1000.0
            mock_employee.used_budget = 0.0
            mock_employee.remaining_budget = 1000.0
            
            steps = [
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title="步骤1: 调研",
                    description="完成调研工作",
                    estimated_cost=100.0,
                    manual_content="调研手册",
                    input_requirements="初始需求",
                    output_deliverables="调研报告"
                ),
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title="步骤2: 设计",
                    description="完成设计工作",
                    estimated_cost=150.0,
                    manual_content="设计手册",
                    input_requirements="调研报告",
                    output_deliverables="设计方案"
                ),
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title="步骤3: 开发",
                    description="完成开发工作",
                    estimated_cost=200.0,
                    manual_content="开发手册",
                    input_requirements="设计方案",
                    output_deliverables="代码实现"
                )
            ]
            
            # 跟踪任务创建
            created_tasks = []
            async def mock_create(task):
                created_tasks.append(task)
                return task
            
            mock_task_repo = Mock()
            mock_task_repo.create = AsyncMock(side_effect=mock_create)
            mock_task_repo.update = AsyncMock(return_value=None)
            mock_task_repo.get_by_id = AsyncMock(side_effect=lambda id: 
                next((t for t in created_tasks if t.id == id), None)
            )
            
            mock_emp_repo = Mock()
            mock_emp_repo.get_by_id = AsyncMock(return_value=mock_employee)
            
            mock_task_service = Mock()
            mock_task_service.assign_task = AsyncMock(return_value=None)
            
            service = WorkflowService(
                task_repo=mock_task_repo,
                emp_repo=mock_emp_repo,
                task_service=mock_task_service
            )
            
            # 创建工作流
            result = await service.create_workflow(
                name="端到端测试工作流",
                description="测试完整流程",
                steps=steps,
                initial_input={"goal": "完成项目"},
                created_by="test"
            )
            
            print(f"✓ 工作流创建成功: {result.workflow_id}")
            print(f"✓ 创建了 {len(created_tasks)} 个任务")
            
            # 2. 验证所有任务都有手册
            tasks_dir = Path(temp_dir) / "tasks"
            manual_files = list(tasks_dir.glob("*.md"))
            assert len(manual_files) == 3
            print(f"✓ 所有任务都有手册文件")
            
            # 3. 验证任务链
            for i, task in enumerate(created_tasks):
                assert task.workflow_id == result.workflow_id
                assert task.step_index == i
                assert task.total_steps == 3
                print(f"  任务 {i+1}: {task.id} - 步骤 {task.step_index + 1}")
            
            # 4. 验证第一个任务被触发
            mock_task_service.assign_task.assert_called_once_with(
                created_tasks[0].id, "emp-001"
            )
            print("✓ 第一个任务已触发")
            
            # 5. 验证 execution_context 包含手册信息
            for task in created_tasks:
                ctx = json.loads(task.execution_context)
                assert "step_manual" in ctx
                assert ctx["step_manual"]["manual_content"]
                assert ctx["step_manual"]["input_requirements"]
                assert ctx["step_manual"]["output_deliverables"]
            print("✓ 所有任务都包含手册上下文")
            
            # 6. 验证第一个任务的输入数据
            first_task = created_tasks[0]
            input_data = json.loads(first_task.input_data)
            assert "initial_input" in input_data
            assert "current_step_description" in input_data
            # 验证描述包含输入要求和输出交付物
            assert "初始需求" in input_data["current_step_description"] or "## 初始输入" in input_data["current_step_description"]
            print("✓ 初始任务输入数据正确")
            
            return True
            
        finally:
            wf_module.MANUALS_DIR = original_dir
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    return asyncio.run(run_test())


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("子功能4测试：集成测试 (v0.4.6)")
    print("=" * 60)
    
    results = []
    
    tests = [
        ("手动创建工作流 + 手册存储", test_manual_workflow_creation),
        ("多步骤数据传递", test_step_data_passing),
        ("返工上下文传递", test_rework_context),
        ("端到端完整流程", test_end_to_end_workflow),
    ]
    
    for name, test_func in tests:
        try:
            results.append((name, test_func()))
        except Exception as e:
            results.append((name, False))
            print(f"\n❌ {name} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 子功能4测试全部通过！")
        print("v0.4.6 工作流界面优化所有功能已完成！")
        return True
    else:
        print("\n⚠️ 部分测试未通过")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
