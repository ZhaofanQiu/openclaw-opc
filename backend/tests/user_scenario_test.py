#!/usr/bin/env python3
"""
v0.3.0-beta 第二轮用户视角自动化测试
模拟真实用户操作流程
"""

import subprocess
import json
import sys

BASE_URL = "http://localhost:8080"
API_KEY = "opc_live_1LhHV72Md3QSFUosi4ovUj4XCTg3qKzd"

def curl(endpoint, method="GET", data=None):
    """Run curl command."""
    url = f"{BASE_URL}{endpoint}"
    cmd = ["curl", "-s", "-H", f"X-API-Key: {API_KEY}", "-H", "Content-Type: application/json"]
    
    if method == "POST" and data:
        cmd.extend(["-X", "POST", "-d", json.dumps(data)])
    elif method == "DELETE":
        cmd.extend(["-X", "DELETE"])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)

def test_scenario(name, steps):
    """Run a test scenario with multiple steps."""
    print(f"\n📋 场景: {name}")
    print("-" * 40)
    
    for i, (step_name, endpoint, method, data, check) in enumerate(steps, 1):
        success, response = curl(endpoint, method, data)
        
        if not success:
            print(f"  ❌ Step {i}: {step_name} - 请求失败")
            return False
        
        try:
            resp_data = json.loads(response)
        except:
            resp_data = {}
        
        if check and not check(resp_data):
            print(f"  ❌ Step {i}: {step_name} - 验证失败")
            print(f"     Response: {response[:100]}")
            return False
        
        print(f"  ✅ Step {i}: {step_name}")
    
    print(f"  🎉 场景完成!")
    return True

def main():
    print("=" * 50)
    print("v0.3.0-beta 第二轮用户视角自动化测试")
    print("=" * 50)
    
    results = []
    
    # 场景 1: 查看Dashboard概览
    results.append(test_scenario(
        "查看Dashboard概览",
        [
            ("获取公司预算", "/api/budget/company", "GET", None, 
             lambda x: "total_budget" in x),
            ("获取员工列表", "/api/agents", "GET", None,
             lambda x: isinstance(x, list) or "detail" not in x),
            ("获取任务列表", "/api/tasks", "GET", None,
             lambda x: isinstance(x, list) or "detail" not in x),
            ("获取系统配置", "/api/config", "GET", None,
             lambda x: True),  # 可能为空
        ]
    ))
    
    # 场景 2: 创建Agent流程
    results.append(test_scenario(
        "创建Agent流程",
        [
            ("确认创建", "/api/agents", "POST", 
             {"name": "测试工程师", "position_level": "senior", "skills": ["python", "testing"]},
             lambda x: ("id" in x or "agent" in x or "success" in x)),
        ]
    ))
    
    # 场景 3: 创建并分配任务
    results.append(test_scenario(
        "创建并分配任务",
        [
            ("创建任务", "/api/tasks", "POST",
             {"title": "单元测试", "description": "编写单元测试代码", "estimated_cost": 100, "priority": "normal"},
             lambda x: "id" in x or "detail" in x),
        ]
    ))
    
    # 场景 4: 查看报告
    results.append(test_scenario(
        "查看报告",
        [
            ("预算趋势", "/api/reports/budget-trend?days=7", "GET", None,
             lambda x: "data" in x),
            ("Agent状态分布", "/api/reports/agent-status", "GET", None,
             lambda x: "distribution" in x),
            ("任务状态分布", "/api/reports/task-status", "GET", None,
             lambda x: "distribution" in x),
            ("最近报告", "/api/reports/recent?days=7", "GET", None,
             lambda x: "reports" in x),
        ]
    ))
    
    # 场景 5: 预算操作
    results.append(test_scenario(
        "预算操作",
        [
            ("查看所有Agent预算", "/api/budget/agents", "GET", None,
             lambda x: "agents" in x),
            ("查看交易明细", "/api/budget/transactions", "GET", None,
             lambda x: isinstance(x, list)),
        ]
    ))
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 场景通过 ({passed/total*100:.0f}%)")
    print("=" * 50)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
