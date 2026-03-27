"""
子功能1测试脚本：验证数据模型扩展 (v0.4.6) - 更新版

测试内容：
1. WorkflowStepConfig 支持新字段
2. WorkflowStepAssist 支持新字段
3. API Response 模型支持新字段
4. 工作流创建时手册存储到标准路径 (data/manuals/tasks/{task_id}.md)

注意：工作流步骤手册采用与标准任务手册相同的路径规则。
"""

import json
import os
import tempfile
import shutil
from pathlib import Path


def test_data_model_extension():
    """测试数据模型扩展"""
    print("=" * 60)
    print("测试 1: 数据模型扩展")
    print("=" * 60)
    
    from opc_core.services.workflow_service import WorkflowStepConfig
    from opc_core.services.partner_service import WorkflowStepAssist
    from opc_core.api.partner import WorkflowStepAssistResponse
    
    # 测试 WorkflowStepConfig
    config = WorkflowStepConfig(
        employee_id='emp-001',
        title='内容撰写',
        description='撰写文章正文',
        estimated_cost=150.0,
        manual_content='## 执行手册\n\n1. 阅读选题报告',
        input_requirements='选题报告',
        output_deliverables='文章正文'
    )
    
    assert config.manual_content is not None
    assert config.input_requirements is not None
    assert config.output_deliverables is not None
    print("✓ WorkflowStepConfig 支持新字段")
    
    # 测试 WorkflowStepAssist
    assist = WorkflowStepAssist(
        title='内容撰写',
        description='撰写文章正文',
        assigned_to='emp-001',
        employee_name='小明',
        estimated_cost=150.0,
        cost_reasoning='中等复杂度',
        manual_content='## 执行手册',
        input_requirements='选题报告',
        output_deliverables='文章正文'
    )
    
    assert assist.manual_content is not None
    assert assist.input_requirements is not None
    assert assist.output_deliverables is not None
    print("✓ WorkflowStepAssist 支持新字段")
    
    # 测试 API Response
    response = WorkflowStepAssistResponse(
        title='内容撰写',
        description='撰写文章正文',
        assigned_to='emp-001',
        employee_name='小明',
        estimated_cost=150.0,
        cost_reasoning='中等复杂度',
        manual_content='## 执行手册',
        input_requirements='选题报告',
        output_deliverables='文章正文'
    )
    
    assert response.manual_content is not None
    print("✓ WorkflowStepAssistResponse 支持新字段")
    
    print("\n✅ 数据模型扩展测试通过")
    return True


def test_task_manual_file_creation():
    """测试任务手册文件创建（采用标准路径）"""
    print("\n" + "=" * 60)
    print("测试 2: 任务手册文件创建（标准路径）")
    print("=" * 60)
    
    from opc_core.services.workflow_service import (
        WorkflowStepConfig, 
        _write_task_manual_file,
        MANUALS_DIR
    )
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    original_dir = MANUALS_DIR
    
    try:
        # 临时修改手册目录
        import opc_core.services.workflow_service as wf_module
        wf_module.MANUALS_DIR = Path(temp_dir)
        
        # 创建测试步骤
        step = WorkflowStepConfig(
            employee_id='emp-001',
            title='内容撰写',
            description='撰写文章正文',
            estimated_cost=150.0,
            manual_content='## 执行手册\n\n1. 阅读选题报告',
            input_requirements='选题报告',
            output_deliverables='文章正文'
        )
        
        # 创建手册文件（使用任务ID）
        task_id = "task-wf-001"
        manual_path = _write_task_manual_file(task_id, step)
        
        # 验证文件存在（标准路径: data/manuals/tasks/{task_id}.md）
        expected_path = Path(temp_dir) / "tasks" / f"{task_id}.md"
        assert os.path.exists(expected_path), f"手册文件未创建"
        print(f"✓ 手册文件已创建: {expected_path}")
        
        # 验证文件内容
        content = expected_path.read_text(encoding="utf-8")
        assert step.title in content
        assert step.manual_content in content
        print("✓ 手册文件内容正确")
        
        # 验证与标准任务手册路径一致
        assert str(expected_path.absolute()) == manual_path
        print("✓ 路径符合标准任务手册规则")
        
        print("\n✅ 任务手册文件创建测试通过")
        return True
        
    finally:
        # 恢复原始目录并清理
        wf_module.MANUALS_DIR = original_dir
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_task_service_unchanged():
    """测试 _build_task_assignment 未修改（使用标准路径）"""
    print("\n" + "=" * 60)
    print("测试 3: TaskService 使用标准路径")
    print("=" * 60)
    
    from opc_core.services.task_service import TaskService
    from unittest.mock import Mock
    
    # 创建模拟对象
    mock_task = Mock()
    mock_task.id = "task-test-001"
    mock_task.title = "测试任务"
    mock_task.description = "测试描述"
    mock_task.workflow_id = "wf-001"  # 工作流任务
    mock_task.execution_context = json.dumps({
        "step_manual": {
            "manual_content": "手册内容"
            # 注意：没有 manual_path，使用标准路径
        }
    })
    
    mock_employee = Mock()
    mock_employee.id = "emp-001"
    mock_employee.name = "测试员工"
    mock_employee.openclaw_agent_id = "opc-agent-001"
    mock_employee.monthly_budget = 1000.0
    mock_employee.used_budget = 100.0
    mock_employee.remaining_budget = 900.0
    
    # 创建 TaskService
    service = TaskService(task_repo=Mock(), emp_repo=Mock())
    
    # 调用 _build_task_assignment
    assignment = service._build_task_assignment(mock_task, mock_employee)
    
    # 验证使用标准任务手册路径
    expected_path = f"/home/user/opc/manuals/tasks/{mock_task.id}.md"
    assert assignment.task_manual_path == expected_path
    print(f"✓ task_manual_path 使用标准路径: {assignment.task_manual_path}")
    
    # 验证没有 step_manual_path 字段
    assert not hasattr(assignment, 'step_manual_path')
    print("✓ 无 step_manual_path 字段（使用标准 task_manual_path）")
    
    print("\n✅ TaskService 使用标准路径测试通过")
    return True


def test_prompt_generation():
    """测试 Partner Prompt 更新"""
    print("\n" + "=" * 60)
    print("测试 4: Partner Prompt 生成")
    print("=" * 60)
    
    from opc_core.services.partner_service import PartnerService
    import inspect
    
    source = inspect.getsource(PartnerService._build_workflow_assist_prompt)
    
    assert "manual_content" in source
    assert "input_requirements" in source
    assert "output_deliverables" in source
    
    print("✓ Prompt 包含所有新字段要求")
    print("\n✅ Partner Prompt 测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("子功能1测试：数据模型扩展 (v0.4.6) - 标准路径版")
    print("=" * 60)
    
    results = []
    
    tests = [
        ("数据模型扩展", test_data_model_extension),
        ("任务手册文件创建（标准路径）", test_task_manual_file_creation),
        ("TaskService 使用标准路径", test_task_service_unchanged),
        ("Partner Prompt", test_prompt_generation),
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
        print("\n🎉 子功能1测试全部通过！")
        print("工作流步骤手册采用标准任务手册路径: data/manuals/tasks/{task_id}.md")
        return True
    else:
        print("\n⚠️ 部分测试未通过")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
