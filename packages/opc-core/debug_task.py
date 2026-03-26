#!/usr/bin/env python3
"""
opc-core 调试脚本：完整任务执行流程验证

功能：
1. 创建测试任务
2. 分配给员工
3. 执行并捕获完整响应
4. 验证 OPC-REPORT 格式和 result_files
"""

import sys
import asyncio
import json
from datetime import datetime

# 添加路径
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-core/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-database/src')
sys.path.insert(0, '/root/.openclaw/workspace/openclaw-opc/packages/opc-openclaw/src')

from opc_database import get_session
from opc_database.models import Task, TaskStatus
from opc_database.repositories import TaskRepository, EmployeeRepository
from opc_core.services import TaskService
from opc_openclaw import ResponseParser


async def debug_task_execution():
    """完整调试任务执行流程"""
    
    print("=" * 70)
    print("【调试开始】opc-core 任务执行流程验证")
    print("=" * 70)
    
    async with get_session() as session:
        task_repo = TaskRepository(session)
        emp_repo = EmployeeRepository(session)
        
        # ========== 步骤 1: 查找员工 ==========
        print("\n【步骤 1】查找可用员工...")
        employees = await emp_repo.get_all()
        target_emp = None
        for emp in employees:
            if "小王" in emp.name or emp.openclaw_agent_id:
                target_emp = emp
                print(f"  ✓ 找到员工: {emp.name} (ID: {emp.id})")
                print(f"    Agent ID: {emp.openclaw_agent_id}")
                print(f"    状态: {emp.status}")
                break
        
        if not target_emp:
            print("  ✗ 未找到可用员工")
            return
        
        # ========== 步骤 2: 创建任务 ==========
        print("\n【步骤 2】创建任务...")
        import uuid
        task = Task(
            id=f"debug_{uuid.uuid4().hex[:8]}",
            title="咏鸡",
            description="写一首赞美鸡的七言绝句",
            status=TaskStatus.PENDING.value,
            priority="normal",
            estimated_cost=50.0,
            assigned_to=target_emp.id
        )
        await task_repo.create(task)
        print(f"  ✓ 任务创建成功: {task.id}")
        print(f"    标题: {task.title}")
        print(f"    描述: {task.description}")
        
        # ========== 步骤 3: 构建任务消息 ==========
        print("\n【步骤 3】构建发送给 Agent 的任务消息...")
        from opc_openclaw.interaction.task_caller import TaskCaller, TaskAssignment
        
        assignment = TaskAssignment(
            task_id=task.id,
            title=task.title,
            description=task.description,
            agent_id=target_emp.openclaw_agent_id,
            agent_name=target_emp.name,
            employee_id=target_emp.id,
            company_manual_path="/home/user/opc/manuals/company.md",
            employee_manual_path=f"/home/user/opc/manuals/employees/{target_emp.id}.md",
            task_manual_path=f"/home/user/opc/manuals/tasks/{task.id}.md",
            timeout=900,
            monthly_budget=target_emp.monthly_budget,
            used_budget=target_emp.used_budget,
            remaining_budget=target_emp.remaining_budget,
        )
        
        task_caller = TaskCaller()
        message = task_caller._build_message(assignment)
        
        print(f"  ✓ 任务消息已构建")
        print(f"\n【发送给 Agent 的完整消息】\n{'='*70}")
        print(message)
        print(f"{'='*70}")
        
        # ========== 步骤 4: 发送任务给 Agent ==========
        print("\n【步骤 4】发送任务给 Agent (可能需要 15-60 秒)...")
        print(f"  目标 Agent: {target_emp.openclaw_agent_id}")
        print(f"  超时时间: 900 秒")
        print(f"  开始时间: {datetime.now().strftime('%H:%M:%S')}")
        
        response = await task_caller.assign_task(assignment)
        
        print(f"  完成时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"\n【Agent 原始响应 - 完整内容】\n{'='*70}")
        print(response.content if response.content else "(空响应)")
        print(f"{'='*70}")
        
        # ========== 步骤 5: 解析响应 ==========
        print("\n【步骤 5】解析 Agent 响应...")
        report = ResponseParser.parse(response.content)
        
        print(f"  解析结果:")
        print(f"    is_valid: {report.is_valid}")
        print(f"    task_id: {repr(report.task_id)}")
        print(f"    status: {repr(report.status)}")
        print(f"    tokens_used: {report.tokens_used}")
        print(f"    summary: {repr(report.summary)}")
        print(f"    result_files: {report.result_files}")
        print(f"    errors: {report.errors}")
        
        # ========== 步骤 6: 更新任务状态 ==========
        print("\n【步骤 6】更新任务状态...")
        task_service = TaskService(task_repo, emp_repo)
        task_service._update_task_from_report(task, report, response)
        await task_repo.update(task)
        
        print(f"  ✓ 任务已更新")
        print(f"    数据库状态: {task.status}")
        print(f"    数据库 result: {repr(task.result)}")
        print(f"    数据库 result_files: {task.result_files}")
        print(f"    数据库 tokens_output: {task.tokens_output}")
        
        # ========== 步骤 7: 验证结果 ==========
        print("\n【步骤 7】验证结果...")
        
        # 重新读取任务
        task = await task_repo.get_by_id(task.id)
        
        print(f"\n【最终任务状态】")
        print(f"  任务ID: {task.id}")
        print(f"  状态: {task.status}")
        print(f"  结果: {repr(task.result)}")
        print(f"  result_files: {task.result_files}")
        print(f"  tokens_output: {task.tokens_output}")
        
        print(f"\n【验证检查项】")
        print(f"  ✓ OPC-REPORT 格式正确: {report.is_valid}")
        print(f"  ✓ task_id 匹配: {report.task_id == task.id}")
        print(f"  ✓ status 有效: {report.status in ['completed', 'failed', 'needs_revision']}")
        print(f"  ✓ tokens_used > 0: {report.tokens_used > 0}")
        print(f"  ✓ summary 不为空: {bool(report.summary)}")
        print(f"  ✗ result_files 有内容: {bool(report.result_files)} (文件路径: {report.result_files})")
        
        if not report.result_files:
            print(f"\n【问题确认】")
            print(f"  Agent 正确返回了 OPC-REPORT 格式")
            print(f"  但 result_files 字段为空")
            print(f"  原因: Agent 没有生成/提供结果文件路径")
        
        print("\n" + "=" * 70)
        print("【调试完成】")
        print("=" * 70)
        
        return {
            "task_id": task.id,
            "agent_response": response.content,
            "parsed_report": {
                "is_valid": report.is_valid,
                "task_id": report.task_id,
                "status": report.status,
                "tokens_used": report.tokens_used,
                "summary": report.summary,
                "result_files": report.result_files,
                "errors": report.errors,
            },
            "task_result": {
                "status": task.status,
                "result": task.result,
                "result_files": task.result_files,
                "tokens_output": task.tokens_output,
            }
        }


if __name__ == "__main__":
    result = asyncio.run(debug_task_execution())
    
    print("\n【返回结果摘要】")
    print(json.dumps(result, indent=2, ensure_ascii=False))
