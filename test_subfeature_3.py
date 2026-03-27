"""
子功能3测试脚本：工作流执行引擎 (v0.4.6)

测试内容：
1. _get_previous_output 正确提取前一步输出
2. _get_step_context 正确解析步骤上下文
3. _build_step_description 正确构建步骤描述
4. _build_initial_step_description 正确构建初始描述
5. _trigger_next_step 正确传递数据到下一步
"""

import json
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')

from opc_core.services.workflow_service import WorkflowService, WorkflowStepConfig


def test_get_previous_output():
    """测试 _get_previous_output"""
    print("=" * 60)
    print("测试 1: _get_previous_output")
    print("=" * 60)
    
    async def run_test():
        # 创建模拟任务
        mock_task = Mock()
        mock_task.step_index = 0
        mock_task.title = "Step 1: 调研"
        mock_task.id = "task-001"
        mock_task.assigned_to = "emp-001"
        mock_task.completed_at = "2026-03-28T10:00:00"
        mock_task.output_data = json.dumps({
            "summary": "完成了AI趋势调研，发现三大关键方向",
            "structured_output": {
                "trend_1": "多模态AI",
                "trend_2": "AI Agent",
                "trend_3": "边缘AI"
            },
            "deliverables": ["调研报告.md"],
            "metadata": {"confidence": 0.95}
        })
        
        # 创建模拟 employee
        mock_employee = Mock()
        mock_employee.name = "研究员小王"
        
        # 创建 service 实例并模拟 emp_repo
        service = WorkflowService(
            task_repo=Mock(),
            emp_repo=Mock(),
            task_service=Mock()
        )
        service.emp_repo.get_by_id = AsyncMock(return_value=mock_employee)
        
        result = await service._get_previous_output(mock_task)
        
        assert result["step_index"] == 0
        assert result["step_title"] == "Step 1: 调研"
        assert result["employee_name"] == "研究员小王"
        assert "output_summary" in result
        assert "structured_output" in result
        assert "deliverables" in result
        
        print("✓ 输出结构正确")
        print(f"  - 步骤索引: {result['step_index']}")
        print(f"  - 执行者: {result['employee_name']}")
        print(f"  - 输出摘要: {result['output_summary'][:50]}...")
        return True
    
    return asyncio.run(run_test())


def test_get_step_context():
    """测试 _get_step_context"""
    print("\n" + "=" * 60)
    print("测试 2: _get_step_context")
    print("=" * 60)
    
    # 创建包含步骤手册上下文的任务
    mock_task = Mock()
    mock_task.execution_context = json.dumps({
        "step_manual": {
            "title": "撰写报告",
            "description": "撰写调研报告",
            "manual_content": "## 报告结构\n1. 摘要\n2. 正文\n3. 结论",
            "input_requirements": "需要调研数据和分析结果",
            "output_deliverables": "完整的调研报告（2000字以上）"
        }
    })
    
    service = WorkflowService(
        task_repo=Mock(),
        emp_repo=Mock(),
        task_service=Mock()
    )
    
    result = service._get_step_context(mock_task)
    
    assert result["title"] == "撰写报告"
    assert result["input_requirements"] == "需要调研数据和分析结果"
    assert result["output_deliverables"] == "完整的调研报告（2000字以上）"
    
    print("✓ 上下文解析正确")
    print(f"  - 标题: {result['title']}")
    print(f"  - 输入要求: {result['input_requirements']}")
    print(f"  - 输出交付物: {result['output_deliverables']}")
    
    # 测试空上下文
    mock_task_empty = Mock()
    mock_task_empty.execution_context = None
    result_empty = service._get_step_context(mock_task_empty)
    assert result_empty == {}
    print("✓ 空上下文处理正确")
    
    return True


def test_build_step_description():
    """测试 _build_step_description"""
    print("\n" + "=" * 60)
    print("测试 3: _build_step_description")
    print("=" * 60)
    
    service = WorkflowService(
        task_repo=Mock(),
        emp_repo=Mock(),
        task_service=Mock()
    )
    
    # 模拟前序输出
    previous_output = {
        "step_index": 0,
        "step_title": "Step 1: 调研",
        "employee_name": "研究员小王",
        "output_summary": "完成了AI趋势调研，发现三大关键方向",
        "structured_output": {
            "trend_1": "多模态AI",
            "trend_2": "AI Agent"
        },
        "deliverables": ["调研报告.md"]
    }
    
    # 模拟步骤上下文
    step_context = {
        "input_requirements": "需要调研数据",
        "output_deliverables": "撰写完整的报告"
    }
    
    mock_task = Mock()
    
    result = service._build_step_description(mock_task, previous_output, step_context)
    
    # 验证结果包含所有部分
    assert "## 前序步骤输出" in result
    assert "研究员小王" in result
    assert "完成了AI趋势调研" in result
    assert "## 输入要求" in result
    assert "需要调研数据" in result
    assert "## 输出交付物要求" in result
    assert "撰写完整的报告" in result
    assert "OPC-REPORT" in result
    
    print("✓ 步骤描述构建正确")
    print("  生成的描述包含:")
    print("  - 前序步骤输出")
    print("  - 输入要求")
    print("  - 输出交付物要求")
    
    # 测试无前序输出的情况
    result_no_prev = service._build_step_description(mock_task, {}, step_context)
    assert "## 前序步骤输出" not in result_no_prev
    assert "## 输入要求" in result_no_prev
    print("✓ 无前序输出时正确处理")
    
    return True


def test_build_initial_step_description():
    """测试 _build_initial_step_description"""
    print("\n" + "=" * 60)
    print("测试 4: _build_initial_step_description")
    print("=" * 60)
    
    service = WorkflowService(
        task_repo=Mock(),
        emp_repo=Mock(),
        task_service=Mock()
    )
    
    # 创建步骤配置
    step = WorkflowStepConfig(
        employee_id="emp-001",
        title="需求分析",
        description="分析用户需求",
        estimated_cost=100.0,
        manual_content="分析手册",
        input_requirements="用户提供的需求文档",
        output_deliverables="需求分析报告"
    )
    
    # 初始输入
    initial_input = {
        "project_name": "AI助手项目",
        "budget": 10000
    }
    
    result = service._build_initial_step_description(step, initial_input)
    
    # 验证结果
    assert "## 初始输入" in result
    assert "AI助手项目" in result
    assert "## 输入要求" in result
    assert "用户提供的需求文档" in result
    assert "## 输出交付物要求" in result
    assert "需求分析报告" in result
    
    print("✓ 初始步骤描述构建正确")
    print("  生成的描述包含:")
    print("  - 初始输入")
    print("  - 输入要求")
    print("  - 输出交付物要求")
    
    return True


def test_trigger_next_step_integration():
    """测试 _trigger_next_step 集成"""
    print("\n" + "=" * 60)
    print("测试 5: _trigger_next_step 集成")
    print("=" * 60)
    
    async def run_test():
        # 创建模拟对象
        mock_current_task = Mock()
        mock_current_task.next_task_id = "task-002"
        mock_current_task.step_index = 0
        mock_current_task.assigned_to = "emp-001"
        mock_current_task.output_data = json.dumps({
            "summary": "第一步完成",
            "structured_output": {"key": "value"}
        })
        
        mock_next_task = Mock()
        mock_next_task.id = "task-002"
        mock_next_task.step_index = 1
        mock_next_task.total_steps = 3
        mock_next_task.workflow_id = "wf-001"
        mock_next_task.assigned_to = "emp-002"
        mock_next_task.description = "第二步"
        mock_next_task.input_data = json.dumps({
            "previous_outputs": []
        })
        mock_next_task.execution_context = json.dumps({
            "step_manual": {
                "input_requirements": "需要第一步的输出",
                "output_deliverables": "第二步的结果"
            }
        })
        
        mock_employee = Mock()
        mock_employee.name = "员工A"
        
        # 创建 service
        mock_task_repo = Mock()
        mock_task_repo.get_by_id = AsyncMock(side_effect=lambda id: 
            mock_current_task if id == "task-001" else mock_next_task
        )
        mock_task_repo.update = AsyncMock(return_value=mock_next_task)
        
        mock_emp_repo = Mock()
        mock_emp_repo.get_by_id = AsyncMock(return_value=mock_employee)
        
        mock_task_service = Mock()
        mock_task_service.assign_task = AsyncMock(return_value=None)
        
        service = WorkflowService(
            task_repo=mock_task_repo,
            emp_repo=mock_emp_repo,
            task_service=mock_task_service
        )
        
        # 执行测试
        result = await service._trigger_next_step(mock_current_task)
        
        # 验证
        assert result is not None
        assert result.id == "task-002"
        
        # 验证 set_input_data 被调用
        assert mock_next_task.set_input_data.called
        call_args = mock_next_task.set_input_data.call_args[0][0]
        
        assert "workflow_context" in call_args
        assert call_args["workflow_context"]["current_step"] == 2
        assert "previous_outputs" in call_args
        assert len(call_args["previous_outputs"]) == 1
        assert "current_step_description" in call_args
        
        print("✓ _trigger_next_step 执行正确")
        print("  - 输入数据包含 workflow_context")
        print("  - previous_outputs 正确更新")
        print("  - current_step_description 已添加")
        
        # 验证 assign_task 被调用
        mock_task_service.assign_task.assert_called_once_with("task-002", "emp-002")
        print("✓ 下一步任务已触发")
        
        return True
    
    return asyncio.run(run_test())


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("子功能3测试：工作流执行引擎 (v0.4.6)")
    print("=" * 60)
    
    results = []
    
    tests = [
        ("_get_previous_output", test_get_previous_output),
        ("_get_step_context", test_get_step_context),
        ("_build_step_description", test_build_step_description),
        ("_build_initial_step_description", test_build_initial_step_description),
        ("_trigger_next_step 集成", test_trigger_next_step_integration),
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
        print("\n🎉 子功能3测试全部通过！")
        print("工作流执行引擎已增强，支持步骤间数据传递")
        return True
    else:
        print("\n⚠️ 部分测试未通过")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
