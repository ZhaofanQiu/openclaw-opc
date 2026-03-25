#!/usr/bin/env python3
"""
v0.4.2 场景测试执行脚本

执行实际应用场景的端到端测试

用法:
    python run_scenario_tests.py [options]

选项:
    --all         运行所有测试
    --content     仅运行内容创作场景
    --code        仅运行代码审查场景
    --service     仅运行客服场景
    --data        仅运行数据报告场景
    --e2e         仅运行端到端测试
    --perf        仅运行性能测试
"""

import sys
import subprocess
import argparse
from pathlib import Path

# 测试模块映射
TEST_MODULES = {
    "content": "tests/e2e/test_scenario_workflows.py::TestContentCreationWorkflow",
    "code": "tests/e2e/test_scenario_workflows.py::TestCodeReviewWorkflow",
    "service": "tests/e2e/test_scenario_workflows.py::TestCustomerServiceWorkflow",
    "data": "tests/e2e/test_scenario_workflows.py::TestDataReportWorkflow",
    "integration": "tests/e2e/test_scenario_workflows.py::TestCrossScenarioIntegration",
    "e2e": "tests/e2e/test_scenario_workflows.py::TestEndToEndWorkflow",
    "perf": "tests/e2e/test_scenario_workflows.py::TestPerformance",
    "error": "tests/e2e/test_scenario_workflows.py::TestErrorHandling",
}


def run_tests(test_paths: list, verbose: bool = True):
    """运行测试"""
    cmd = ["python3", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["--tb=short", "-x"])  # 短错误回溯，遇到失败停止
    cmd.extend(test_paths)
    
    print(f"执行命令: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="v0.4.2 场景测试执行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python run_scenario_tests.py --all
    python run_scenario_tests.py --content --code
    python run_scenario_tests.py --e2e
        """
    )
    
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--content", action="store_true", help="内容创作场景")
    parser.add_argument("--code", action="store_true", help="代码审查场景")
    parser.add_argument("--service", action="store_true", help="客服场景")
    parser.add_argument("--data", action="store_true", help="数据报告场景")
    parser.add_argument("--integration", action="store_true", help="集成测试")
    parser.add_argument("--e2e", action="store_true", help="端到端测试")
    parser.add_argument("--perf", action="store_true", help="性能测试")
    parser.add_argument("--error", action="store_true", help="错误处理测试")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式")
    
    args = parser.parse_args()
    
    # 如果没有指定任何测试，显示帮助
    if not any([
        args.all, args.content, args.code, args.service, args.data,
        args.integration, args.e2e, args.perf, args.error
    ]):
        parser.print_help()
        return 0
    
    # 收集要运行的测试
    tests_to_run = []
    
    if args.all:
        tests_to_run = ["tests/e2e/test_scenario_workflows.py"]
    else:
        if args.content:
            tests_to_run.append(TEST_MODULES["content"])
        if args.code:
            tests_to_run.append(TEST_MODULES["code"])
        if args.service:
            tests_to_run.append(TEST_MODULES["service"])
        if args.data:
            tests_to_run.append(TEST_MODULES["data"])
        if args.integration:
            tests_to_run.append(TEST_MODULES["integration"])
        if args.e2e:
            tests_to_run.append(TEST_MODULES["e2e"])
        if args.perf:
            tests_to_run.append(TEST_MODULES["perf"])
        if args.error:
            tests_to_run.append(TEST_MODULES["error"])
    
    # 执行测试
    print("\n" + "=" * 60)
    print("v0.4.2 实际应用场景测试")
    print("=" * 60 + "\n")
    
    returncode = run_tests(tests_to_run, verbose=not args.quiet)
    
    if returncode == 0:
        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 测试失败")
        print("=" * 60)
    
    return returncode


if __name__ == "__main__":
    sys.exit(main())
