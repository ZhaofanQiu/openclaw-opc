#!/usr/bin/env python3
"""
P0 功能集成测试 - 手动验证脚本

使用方法:
    python3 test_p0_manual.py

此脚本验证 P0 所有核心功能是否正常工作
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-openclaw/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("[测试 1/5] 模块导入测试")
    print("=" * 60)
    
    try:
        # Database
        from opc_database.models import Task
        print("✅ opc_database.models.Task")
        
        # OpenClaw
        from opc_openclaw.interaction import TaskAssignment, ResponseParser, ParsedReport
        print("✅ opc_openclaw.interaction.TaskAssignment")
        print("✅ opc_openclaw.interaction.ResponseParser")
        print("✅ opc_openclaw.interaction.ParsedReport")
        
        # Core Services
        from opc_core.services import (
            WorkflowService,
            WorkflowStepConfig,
            WorkflowResult,
            WorkflowProgress,
            WorkflowError,
            WorkflowNotFoundError,
            InvalidStepConfigError,
            ReworkLimitExceeded,
            InvalidReworkTarget,
        )
        print("✅ opc_core.services.WorkflowService")
        print("✅ opc_core.services.WorkflowStepConfig")
        print("✅ opc_core.services.WorkflowResult")
        print("✅ opc_core.services.WorkflowProgress")
        print("✅ opc_core.services.Exceptions")
        
        # Core API
        from opc_core.api.workflows import router
        print("✅ opc_core.api.workflows.router")
        
        print("\n✅ 所有模块导入成功！")
        return True
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        return False


def test_task_model_fields():
    """测试 Task 模型新字段"""
    print("\n" + "=" * 60)
    print("[测试 2/5] Task 模型字段测试")
    print("=" * 60)
    
    from opc_database.models import Task
    
    # 创建 Task 实例
    task = Task()
    
    # 检查 v0.4.2 新增字段
    fields_to_check = [
        'workflow_id',
        'step_index',
        'total_steps',
        'depends_on',
        'next_task_id',
        'input_data',
        'output_data',
        'is_rework',
        'rework_target',
        'rework_triggered_by',
        'rework_reason',
        'rework_instructions',
        'execution_log',
    ]
    
    for field in fields_to_check:
        if hasattr(task, field):
            print(f"✅ Task.{field}")
        else:
            print(f"❌ Task.{field} - 缺失！")
            return False
    
    # 检查新增方法
    methods_to_check = [
        'is_workflow_task',
        'is_first_step',
        'is_last_step',
        'get_progress',
        'set_input_data',
        'set_output_data',
        'add_execution_log',
    ]
    
    for method in methods_to_check:
        if hasattr(task, method) and callable(getattr(task, method)):
            print(f"✅ Task.{method}()")
        else:
            print(f"❌ Task.{method}() - 缺失！")
            return False
    
    print("\n✅ Task 模型扩展成功！")
    return True


def test_workflow_service_structure():
    """测试 WorkflowService 结构"""
    print("\n" + "=" * 60)
    print("[测试 3/5] WorkflowService 结构测试")
    print("=" * 60)
    
    from opc_core.services import WorkflowService, WorkflowStepConfig
    
    # 检查必要方法
    methods = [
        'create_workflow',
        'on_task_completed',
        'on_task_failed',
        'request_rework',
        'get_workflow_progress',
        'get_workflow_tasks',
    ]
    
    for method in methods:
        if hasattr(WorkflowService, method):
            print(f"✅ WorkflowService.{method}()")
        else:
            print(f"❌ WorkflowService.{method}() - 缺失！")
            return False
    
    # 检查 WorkflowStepConfig
    from dataclasses import fields
    step_fields = [f.name for f in fields(WorkflowStepConfig)]
    expected_fields = ['employee_id', 'title', 'description', 'estimated_cost']
    for field in expected_fields:
        if field in step_fields:
            print(f"✅ WorkflowStepConfig.{field}")
        else:
            print(f"❌ WorkflowStepConfig.{field} - 缺失！")
            return False
    
    print("\n✅ WorkflowService 结构正确！")
    return True


def test_response_parser():
    """测试 ResponseParser"""
    print("\n" + "=" * 60)
    print("[测试 4/5] ResponseParser 测试")
    print("=" * 60)
    
    from opc_openclaw.interaction import ResponseParser, ParsedReport
    
    parser = ResponseParser()
    
    # 测试解析 OPC-REPORT
    content = """
---OPC-OUTPUT---
{
  "review_passed": true,
  "issues": []
}
---END-OUTPUT---

---OPC-REPORT---
task_id: test-001
status: completed
tokens_used: 500
summary: 任务完成
---END-REPORT---

---OPC-REWORK---
target_step: 0
reason: 需要补充数据
instructions: 请添加更多参考资料
---END-REWORK---
"""
    
    report = parser.parse(content, expected_task_id='test-001')
    
    checks = [
        (report.is_valid, "报告有效性"),
        (report.task_id == 'test-001', "任务ID"),
        (report.status == 'completed', "状态"),
        (report.tokens_used == 500, "Token消耗"),
        (report.structured_output is not None, "结构化输出"),
        (report.needs_rework == True, "返工标记"),
        (report.rework_target_step == 0, "返工目标步骤"),
        (report.rework_reason == '需要补充数据', "返工原因"),
    ]
    
    for passed, name in checks:
        if passed:
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - 验证失败！")
            return False
    
    print("\n✅ ResponseParser 工作正常！")
    return True


def test_api_routes():
    """测试 API 路由"""
    print("\n" + "=" * 60)
    print("[测试 5/5] API 路由测试")
    print("=" * 60)
    
    from opc_core.api.workflows import router
    
    expected_routes = [
        ('POST', '/workflows'),
        ('GET', '/workflows'),
        ('GET', '/workflows/{workflow_id}'),
        ('GET', '/workflows/{workflow_id}/progress'),
        ('POST', '/workflows/{workflow_id}/rework'),
        ('DELETE', '/workflows/{workflow_id}'),
    ]
    
    found_routes = []
    for route in router.routes:
        for method in route.methods:
            if method != 'HEAD':  # 忽略 HEAD
                found_routes.append((method, route.path))
    
    for method, path in expected_routes:
        if (method, path) in found_routes:
            print(f"✅ {method} {path}")
        else:
            print(f"❌ {method} {path} - 未找到！")
            return False
    
    print("\n✅ API 路由完整！")
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenClaw OPC v0.4.2 - P0 功能集成测试")
    print("=" * 60)
    
    results = []
    
    results.append(("模块导入", test_imports()))
    results.append(("Task 模型字段", test_task_model_fields()))
    results.append(("WorkflowService 结构", test_workflow_service_structure()))
    results.append(("ResponseParser", test_response_parser()))
    results.append(("API 路由", test_api_routes()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！P0 功能完整可用！")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查实现！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
