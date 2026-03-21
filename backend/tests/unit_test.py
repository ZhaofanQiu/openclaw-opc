#!/usr/bin/env python3
"""
v0.3.0-beta 第一轮单元测试脚本 (自包含版本)
"""

import subprocess
import time
import sys
import os

BASE_URL = "http://localhost:8080"
API_KEY = "opc_live_1LhHV72Md3QSFUosi4ovUj4XCTg3qKzd"

def run_curl(endpoint, method="GET", data=None):
    """Run curl command."""
    url = f"{BASE_URL}{endpoint}"
    cmd = ["curl", "-s", "-H", f"X-API-Key: {API_KEY}", "-H", "Content-Type: application/json"]
    
    if method == "POST" and data:
        cmd.extend(["-X", "POST", "-d", data])
    elif method == "DELETE":
        cmd.extend(["-X", "DELETE"])
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test(name, endpoint, method="GET", data=None):
    """Run a single test."""
    success, stdout, stderr = run_curl(endpoint, method, data)
    
    if success and stdout and '"detail"' not in stdout:
        print(f"✅ {name}: PASS")
        return True
    else:
        print(f"❌ {name}: FAIL")
        if stderr:
            print(f"   Error: {stderr[:100]}")
        if stdout:
            print(f"   Response: {stdout[:100]}")
        return False

def main():
    print("=" * 50)
    print("v0.3.0-beta 第一轮单元功能测试")
    print("=" * 50)
    
    # Check if service is running
    ok, _, _ = run_curl("/health")
    if not ok:
        print("⚠️  服务未运行，请在另一个终端启动:")
        print("   cd backend && source venv/bin/activate && python -m uvicorn src.main:app --host 0.0.0.0 --port 8080")
        return 1
    
    results = []
    
    # 系统健康检查
    results.append(test("系统健康检查", "/health"))
    
    # 预算模块
    results.append(test("公司预算查询", "/api/budget/company"))
    results.append(test("Agent预算列表", "/api/budget/agents"))
    
    # Agent模块
    results.append(test("列出所有Agent", "/api/agents"))
    
    # 任务模块
    results.append(test("列出所有任务", "/api/tasks"))
    
    # 报告模块
    results.append(test("预算趋势报告", "/api/reports/budget-trend?days=7"))
    results.append(test("Agent状态统计", "/api/reports/agent-status"))
    results.append(test("任务状态统计", "/api/reports/task-status"))
    
    # 配置模块
    results.append(test("系统配置查询", "/api/config"))
    
    # 通知模块
    results.append(test("通知列表", "/api/notifications"))
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print("=" * 50)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
