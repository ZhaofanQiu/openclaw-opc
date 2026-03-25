"""
opc-core: 工作流性能测试 (v0.4.2-stable)

测试工作流操作的性能表现
"""

import asyncio
import time
import json
from unittest.mock import AsyncMock, MagicMock

import sys
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')

from opc_core.services import WorkflowService, WorkflowStepConfig


class PerformanceTester:
    """性能测试工具"""

    def __init__(self):
        self.results = []

    def mock_services(self):
        """创建 mock 服务"""
        mock_task_repo = MagicMock()
        mock_emp_repo = MagicMock()
        mock_task_service = MagicMock()

        # Mock employee
        emp = MagicMock()
        emp.id = "emp-001"
        emp.name = "Test Employee"
        emp.openclaw_agent_id = "opc-worker-1"
        emp.monthly_budget = 1000.0
        emp.used_budget = 0.0

        mock_emp_repo.get_by_id = AsyncMock(return_value=emp)

        created_tasks = []
        async def mock_create(task):
            created_tasks.append(task)
            return task
        mock_task_repo.create = AsyncMock(side_effect=mock_create)
        mock_task_repo.update = AsyncMock()
        mock_task_service.assign_task = AsyncMock()

        service = WorkflowService(mock_task_repo, mock_emp_repo, mock_task_service)
        return service, created_tasks

    async def test_create_workflow_performance(self):
        """测试创建工作流性能"""
        print("=" * 60)
        print("[性能测试] 创建工作流")
        print("=" * 60)

        service, _ = self.mock_services()

        # 测试不同步骤数
        step_counts = [2, 3, 5, 10]

        for count in step_counts:
            steps = [
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title=f"Step {i+1}",
                    description=f"Description for step {i+1}",
                    estimated_cost=100.0,
                )
                for i in range(count)
            ]

            start = time.perf_counter()
            result = await service.create_workflow(
                name=f"Test Workflow {count} steps",
                description="Performance test",
                steps=steps,
                initial_input={"test": "data"},
                created_by="test",
            )
            elapsed = time.perf_counter() - start

            status = "✅ PASS" if elapsed < 1.0 else "⚠️ SLOW"
            print(f"  {status} {count} 步骤: {elapsed:.4f}s (目标: <1s)")
            self.results.append(("create_workflow", count, elapsed))

    async def test_build_input_data_performance(self):
        """测试构建输入数据性能"""
        print("\n" + "=" * 60)
        print("[性能测试] 构建输入数据结构")
        print("=" * 60)

        service, _ = self.mock_services()

        # 测试不同大小的 previous_outputs - 使用 create_workflow 间接测试
        sizes = [0, 1, 5, 10]

        for size in sizes:
            steps = [
                WorkflowStepConfig(
                    employee_id="emp-001",
                    title=f"Step {i+1}",
                    description=f"Description for step {i+1}",
                    estimated_cost=100.0,
                )
                for i in range(min(size + 2, 5))  # 至少2个步骤
            ]

            start = time.perf_counter()
            for _ in range(100):  # 运行100次取平均
                result = await service.create_workflow(
                    name=f"Test Workflow {size}",
                    description="Performance test",
                    steps=steps,
                    initial_input={"test": "data" * size * 100},  # 增大初始数据
                    created_by="test",
                )
            elapsed = (time.perf_counter() - start) / 100

            status = "✅ PASS" if elapsed < 0.01 else "⚠️ SLOW"
            print(f"  {status} 数据量 {size*100} bytes: {elapsed:.6f}s (目标: <0.01s)")
            self.results.append(("build_input_data", size, elapsed))

    async def test_progress_calculation_performance(self):
        """测试进度计算性能"""
        print("\n" + "=" * 60)
        print("[性能测试] 进度计算")
        print("=" * 60)

        service, _ = self.mock_services()

        # Mock tasks
        tasks = [
            MagicMock(
                status="completed" if i < 5 else "pending",
                step_index=i,
                total_steps=10,
            )
            for i in range(10)
        ]

        service.task_repo.get_by_workflow = AsyncMock(return_value=tasks)

        start = time.perf_counter()
        for _ in range(1000):  # 运行1000次
            progress = await service.get_workflow_progress("wf-001")
        elapsed = (time.perf_counter() - start) / 1000

        status = "✅ PASS" if elapsed < 0.001 else "⚠️ SLOW"
        print(f"  {status} 进度计算: {elapsed:.6f}s (目标: <0.001s)")
        self.results.append(("progress_calculation", 10, elapsed))

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("性能测试摘要")
        print("=" * 60)

        all_pass = True
        for test_name, param, elapsed in self.results:
            if test_name == "create_workflow":
                passed = elapsed < 1.0
            elif test_name == "build_input_data":
                passed = elapsed < 0.01
            elif test_name == "progress_calculation":
                passed = elapsed < 0.001
            else:
                passed = True

            if not passed:
                all_pass = False

        if all_pass:
            print("🎉 所有性能测试通过！")
        else:
            print("⚠️ 部分性能测试未达标")

        print("\n详细结果:")
        for test_name, param, elapsed in self.results:
            print(f"  {test_name} ({param}): {elapsed:.6f}s")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("OpenClaw OPC v0.4.2 - 工作流性能测试")
    print("=" * 60)

    tester = PerformanceTester()

    await tester.test_create_workflow_performance()
    await tester.test_build_input_data_performance()
    await tester.test_progress_calculation_performance()

    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
