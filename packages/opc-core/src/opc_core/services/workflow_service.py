"""
opc-core: 工作流服务 (v0.4.6)

工作流编排服务 - 支持多 Agent 串行协作

核心功能:
- 创建工作流 (多步骤任务链)
- 任务完成回调，自动触发下一步
- 返工机制（下游→上游）
- v0.4.6: 工作流步骤手册支持（采用标准任务手册方式）

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.6
"""

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from opc_database.models import Task, TaskStatus
from opc_database.repositories import TaskRepository, EmployeeRepository


# v0.4.6: 标准手册存储路径（与 task_service.py 保持一致）
MANUALS_DIR = Path("data/manuals")


class WorkflowError(Exception):
    """工作流错误"""
    pass


class WorkflowNotFoundError(WorkflowError):
    """工作流不存在"""
    pass


class InvalidStepConfigError(WorkflowError):
    """无效的步骤配置"""
    pass


class ReworkLimitExceeded(WorkflowError):
    """超过返工次数上限"""
    pass


class InvalidReworkTarget(WorkflowError):
    """无效的返工目标"""
    pass


def _write_task_manual_file(task_id: str, step: "WorkflowStepConfig") -> str:
    """
    写入任务手册文件 (v0.4.6)
    
    采用与标准任务手册相同的路径规则: data/manuals/tasks/{task_id}.md
    
    Args:
        task_id: 任务ID
        step: 步骤配置
        
    Returns:
        手册文件绝对路径
    """
    # 确保目录存在
    tasks_dir = MANUALS_DIR / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建手册文件路径（与标准任务手册相同）
    manual_path = tasks_dir / f"{task_id}.md"
    
    # 构建手册内容（包含工作流步骤特定信息）
    content = f"""# 任务手册: {step.title}

## 任务信息
- **任务ID**: {task_id}
- **标题**: {step.title}
- **描述**: {step.description}

## 执行手册
{step.manual_content or "无特定执行手册，请参考任务描述和员工手册。"}

## 输入要求
{step.input_requirements or "无特定输入要求。"}

## 输出交付物
{step.output_deliverables or "无特定输出要求，请按任务描述完成工作。"}

---
*此手册由 OpenClaw OPC 系统自动生成*
"""
    
    # 写入文件
    manual_path.write_text(content, encoding="utf-8")
    
    return str(manual_path.absolute())


@dataclass
class WorkflowStepConfig:
    """工作流步骤配置 (v0.4.6 - 支持步骤手册)"""
    employee_id: str          # 执行员工ID
    title: str                # 步骤标题
    description: str          # 步骤描述
    estimated_cost: float = 0.0  # 预估成本
    # v0.4.6 新增：步骤手册相关字段
    manual_content: Optional[str] = None      # 步骤执行手册
    input_requirements: Optional[str] = None  # 输入要求说明
    output_deliverables: Optional[str] = None # 输出交付物说明


@dataclass
class WorkflowResult:
    """工作流创建结果"""
    workflow_id: str
    first_task_id: str
    task_ids: list[str]
    status: str = "pending"


@dataclass
class WorkflowProgress:
    """工作流进度信息"""
    workflow_id: str
    total_steps: int
    completed_steps: int
    current_step: int
    status: str
    progress_percent: float


class WorkflowService:
    """
    工作流服务

    协调多步骤任务执行，支持：
    - 串行步骤执行
    - 步骤间数据传递
    - 返工机制
    """

    def __init__(
        self,
        task_repo: TaskRepository,
        emp_repo: EmployeeRepository,
        task_service,  # TaskService 实例
    ):
        self.task_repo = task_repo
        self.emp_repo = emp_repo
        self.task_service = task_service

    # ============================================================
    # 核心方法: 创建工作流
    # ============================================================

    async def create_workflow(
        self,
        name: str,
        description: Optional[str],
        steps: list[WorkflowStepConfig],
        initial_input: dict,
        created_by: str,
        max_rework_per_step: int = 2,
    ) -> WorkflowResult:
        """
        创建工作流

        流程:
        1. 验证步骤配置（员工存在且有Agent绑定）
        2. 为每个步骤创建 Task
        3. 建立链表关系 (depends_on/next_task_id)
        4. 设置初始输入数据
        5. 触发第一个任务

        Args:
            name: 工作流名称
            description: 工作流描述
            steps: 步骤配置列表
            initial_input: 初始输入数据
            created_by: 创建者ID
            max_rework_per_step: 每个步骤最大返工次数

        Returns:
            WorkflowResult: 创建结果

        Raises:
            InvalidStepConfigError: 步骤配置无效
        """
        if not steps:
            raise InvalidStepConfigError("Workflow must have at least one step")

        if len(steps) < 2:
            raise InvalidStepConfigError("Workflow must have at least 2 steps for multi-agent collaboration")

        # 生成工作流ID
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        total_steps = len(steps)

        # 验证所有员工
        for i, step in enumerate(steps):
            employee = await self.emp_repo.get_by_id(step.employee_id)
            if not employee:
                raise InvalidStepConfigError(f"Step {i}: Employee {step.employee_id} not found")
            if not employee.openclaw_agent_id:
                raise InvalidStepConfigError(f"Step {i}: Employee {step.employee_id} has no agent bound")

        # 创建任务列表
        tasks: list[Task] = []
        prev_task_id: Optional[str] = None

        for i, step in enumerate(steps):
            # 创建任务ID
            task_id = f"task-{uuid.uuid4().hex[:8]}"
            
            # v0.4.6: 为步骤创建手册文件（采用标准任务手册路径）
            if step.manual_content:
                _write_task_manual_file(task_id, step)
            
            # 构建 execution_context 包含步骤手册信息 (v0.4.6)
            execution_context = {
                "step_manual": {
                    "title": step.title,
                    "description": step.description,
                    "manual_content": step.manual_content or "",
                    "input_requirements": step.input_requirements or "",
                    "output_deliverables": step.output_deliverables or "",
                    # manual_path 不需要存储，因为采用标准路径: data/manuals/tasks/{task_id}.md
                }
            }

            # 创建任务
            task = Task(
                id=task_id,
                title=f"{name} - Step {i+1}: {step.title}",
                description=step.description,
                status=TaskStatus.PENDING.value,
                assigned_to=step.employee_id,
                assigned_by=created_by,
                estimated_cost=step.estimated_cost,
                max_rework=max_rework_per_step,
                # 工作流字段
                workflow_id=workflow_id,
                step_index=i,
                total_steps=total_steps,
                depends_on=prev_task_id,
                next_task_id=None,  # 稍后设置
                # v0.4.6: 存储步骤手册到 execution_context
                execution_context=json.dumps(execution_context, ensure_ascii=False),
            )

            # 设置初始输入（仅第一个任务）
            if i == 0:
                # v0.4.6: 构建初始步骤描述
                initial_step_description = self._build_initial_step_description(
                    step, initial_input
                )
                
                task.set_input_data({
                    "workflow_context": {
                        "workflow_id": workflow_id,
                        "workflow_name": name,
                        "total_steps": total_steps,
                        "current_step": 1,
                    },
                    "initial_input": initial_input,
                    "previous_outputs": [],
                    "current_step_description": initial_step_description,  # v0.4.6
                })
                
                # v0.4.6: 更新任务描述
                if initial_step_description:
                    original_desc = task.description or ""
                    task.description = f"{original_desc}\n\n{initial_step_description}".strip()

            # 保存任务
            task = await self.task_repo.create(task)
            tasks.append(task)

            # 更新前一个任务的 next_task_id
            if prev_task_id and tasks:
                prev_task = tasks[-2] if len(tasks) >= 2 else None
                if prev_task:
                    prev_task.next_task_id = task.id
                    await self.task_repo.update(prev_task)

            prev_task_id = task.id

        # 触发第一个任务
        first_task = tasks[0]
        await self.task_service.assign_task(first_task.id, first_task.assigned_to)

        return WorkflowResult(
            workflow_id=workflow_id,
            first_task_id=first_task.id,
            task_ids=[t.id for t in tasks],
            status="running",
        )

    # ============================================================
    # 核心方法: 任务完成回调
    # ============================================================

    async def on_task_completed(self, task_id: str) -> Optional[Task]:
        """
        任务完成回调

        当任务完成时自动触发：
        1. 检查是否为工作流任务
        2. 如果不是最后一步，触发下一步
        3. 如果是最后一步，标记工作流完成

        Args:
            task_id: 完成的任务ID

        Returns:
            触发的下一个任务（如果有）
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task or not task.workflow_id:
            return None  # 非工作流任务

        # 检查是否为最后一步
        if task.is_last_step():
            await self._finalize_workflow(task.workflow_id)
            return None

        # 触发下一步
        return await self._trigger_next_step(task)

    async def on_task_failed(self, task_id: str, error: str) -> None:
        """
        任务失败回调

        暂停工作流后续步骤，记录失败状态
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task or not task.workflow_id:
            return

        # 暂停下游任务
        await self._pause_downstream_tasks(task_id)

        # 记录执行日志
        task.add_execution_log({
            "event": "task_failed",
            "step_index": task.step_index,
            "error": error,
        })
        await self.task_repo.update(task)

    # ============================================================
    # 返工机制
    # ============================================================

    async def request_rework(
        self,
        from_task_id: str,
        to_task_id: str,
        reason: str,
        instructions: str,
    ) -> Task:
        """
        请求返工

        规则：
        1. 只能向前返工（下游→上游，step_index 减小）
        2. 检查目标节点返工次数上限
        3. 创建返工任务，关联到原任务链
        4. 暂停当前及后续所有步骤
        5. 触发返工任务执行

        Args:
            from_task_id: 当前节点（发现需要返工的节点）
            to_task_id: 目标节点（需要返工的节点）
            reason: 返工原因
            instructions: 返工指令

        Returns:
            新创建的返工任务

        Raises:
            WorkflowNotFoundError: 任务不存在
            InvalidReworkTarget: 返工目标无效
            ReworkLimitExceeded: 超过返工次数上限
        """
        from_task = await self.task_repo.get_by_id(from_task_id)
        to_task = await self.task_repo.get_by_id(to_task_id)

        if not from_task or not to_task:
            raise WorkflowNotFoundError("Task not found")

        if from_task.workflow_id != to_task.workflow_id:
            raise InvalidReworkTarget("Tasks do not belong to the same workflow")

        # 只能向前返工
        if to_task.step_index >= from_task.step_index:
            raise InvalidReworkTarget(
                f"Can only rework upstream tasks. "
                f"Target step {to_task.step_index} >= current step {from_task.step_index}"
            )

        # 检查返工次数
        if not to_task.can_rework():
            raise ReworkLimitExceeded(
                f"Task {to_task_id} has reached max rework limit ({to_task.max_rework})"
            )

        # 暂停下游任务
        await self._pause_downstream_tasks(from_task_id)

        # 创建返工任务
        rework_task = await self._create_rework_task(
            original_task=to_task,
            triggered_by=from_task_id,
            reason=reason,
            instructions=instructions,
        )

        # 触发返工任务
        await self.task_service.assign_task(rework_task.id, rework_task.assigned_to)

        return rework_task

    async def _create_rework_task(
        self,
        original_task: Task,
        triggered_by: str,
        reason: str,
        instructions: str,
    ) -> Task:
        """创建返工任务"""
        # 获取触发者信息
        trigger_task = await self.task_repo.get_by_id(triggered_by)
        trigger_emp = await self.emp_repo.get_by_id(trigger_task.assigned_to) if trigger_task else None

        # 复制原任务，增加 rework_count
        rework_task = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            title=f"{original_task.title} (返工 #{original_task.rework_count + 1})",
            description=original_task.description,
            status=TaskStatus.PENDING.value,
            assigned_to=original_task.assigned_to,
            assigned_by=original_task.assigned_by,
            estimated_cost=original_task.estimated_cost,
            rework_count=original_task.rework_count + 1,
            max_rework=original_task.max_rework,
            # 工作流字段
            workflow_id=original_task.workflow_id,
            step_index=original_task.step_index,
            total_steps=original_task.total_steps,
            depends_on=original_task.depends_on,
            next_task_id=original_task.next_task_id,
            # 返工标记
            is_rework=True,
            rework_target=original_task.id,
            rework_triggered_by=triggered_by,
            rework_reason=reason,
            rework_instructions=instructions,
        )

        # 构建输入数据（包含返工上下文）
        input_data = json.loads(original_task.input_data) if original_task.input_data else {}
        input_data["upstream_rework_notes"] = {
            "triggered_by_step": trigger_task.step_index if trigger_task else None,
            "triggered_by_employee": trigger_emp.name if trigger_emp else None,
            "reason": reason,
            "instructions": instructions,
        }
        rework_task.set_input_data(input_data)

        # 记录执行日志
        rework_task.add_execution_log({
            "event": "rework_created",
            "original_task_id": original_task.id,
            "rework_count": rework_task.rework_count,
            "triggered_by": triggered_by,
            "reason": reason,
        })

        return await self.task_repo.create(rework_task)

    # ============================================================
    # 内部方法
    # ============================================================

    async def _trigger_next_step(self, current_task: Task) -> Optional[Task]:
        """
        触发下一步任务 (v0.4.6 - 增强数据传递)
        
        功能：
        1. 获取前一步的输出数据
        2. 构建下一步的输入数据（包含前序输出汇总）
        3. 触发任务分配
        
        Args:
            current_task: 当前完成的任务
            
        Returns:
            触发的下一个任务，如果没有下一步则返回 None
        """
        if not current_task.next_task_id:
            return None

        next_task = await self.task_repo.get_by_id(current_task.next_task_id)
        if not next_task:
            return None

        # v0.4.6: 获取前一步的输出数据
        previous_output = await self._get_previous_output(current_task)
        
        # v0.4.6: 获取下一步的执行上下文（包含手册信息）
        next_step_context = self._get_step_context(next_task)
        
        # v0.4.6: 构建步骤描述（包含输入要求和输出交付物）
        step_description = self._build_step_description(
            next_task, 
            previous_output,
            next_step_context
        )

        # 构建 previous_outputs 历史
        input_data = json.loads(next_task.input_data) if next_task.input_data else {}
        previous_outputs = input_data.get("previous_outputs", [])

        # 添加当前步骤的输出到历史
        previous_outputs.append(previous_output)

        # v0.4.6: 更新下一步的输入数据
        next_task.set_input_data({
            "workflow_context": {
                "workflow_id": next_task.workflow_id,
                "total_steps": next_task.total_steps,
                "current_step": next_task.step_index + 1,
            },
            "previous_outputs": previous_outputs,
            "current_step_description": step_description,  # v0.4.6: 添加步骤描述
        })
        
        # v0.4.6: 更新任务描述（包含完整上下文）
        if step_description:
            original_desc = next_task.description or ""
            next_task.description = f"{original_desc}\n\n{step_description}".strip()

        await self.task_repo.update(next_task)

        # 触发分配
        await self.task_service.assign_task(next_task.id, next_task.assigned_to)

        return next_task

    async def _get_previous_output(self, task: Task) -> dict:
        """
        获取前一步的输出数据 (v0.4.6)
        
        提取前一步的结构化输出，便于下一步使用
        
        Args:
            task: 完成的任务
            
        Returns:
            包含输出摘要和元数据的字典
        """
        output_data = json.loads(task.output_data) if task.output_data else {}
        employee = await self.emp_repo.get_by_id(task.assigned_to)
        
        return {
            "step_index": task.step_index,
            "step_title": task.title,
            "task_id": task.id,
            "employee_id": task.assigned_to,
            "employee_name": employee.name if employee else "Unknown",
            "output_summary": output_data.get("summary", ""),
            "structured_output": output_data.get("structured_output", {}),
            "deliverables": output_data.get("deliverables", []),
            "metadata": output_data.get("metadata", {}),
            "completed_at": task.completed_at,
        }
    
    def _get_step_context(self, task: Task) -> dict:
        """
        获取步骤执行上下文 (v0.4.6)
        
        从 execution_context 解析步骤手册信息
        
        Args:
            task: 任务对象
            
        Returns:
            包含步骤手册信息的字典
        """
        if not task.execution_context:
            return {}
        
        try:
            context = json.loads(task.execution_context)
            return context.get("step_manual", {})
        except (json.JSONDecodeError, AttributeError):
            return {}
    
    def _build_step_description(
        self, 
        task: Task, 
        previous_output: dict,
        step_context: dict
    ) -> str:
        """
        构建步骤执行描述 (v0.4.6)
        
        生成包含前序输出、输入要求、输出交付物的完整描述
        
        Args:
            task: 当前任务
            previous_output: 前一步的输出
            step_context: 步骤上下文（包含手册信息）
            
        Returns:
            格式化的步骤描述
        """
        sections = []
        
        # 1. 前序步骤输出摘要
        if previous_output.get("output_summary"):
            sections.append("## 前序步骤输出")
            sections.append(f"**步骤 {previous_output['step_index'] + 1}**: {previous_output.get('step_title', '')}")
            sections.append(f"**执行者**: {previous_output.get('employee_name', 'Unknown')}")
            sections.append(f"**输出摘要**:\n{previous_output['output_summary']}")
            
            # 如果有结构化输出，添加关键信息
            structured = previous_output.get("structured_output", {})
            if structured:
                sections.append("**关键数据**:")
                for key, value in structured.items():
                    if isinstance(value, (str, int, float)):
                        sections.append(f"  - {key}: {value}")
            
            sections.append("")  # 空行分隔
        
        # 2. 当前步骤输入要求
        input_req = step_context.get("input_requirements", "")
        if input_req:
            sections.append("## 输入要求")
            sections.append(input_req)
            sections.append("")
        
        # 3. 当前步骤输出交付物
        output_del = step_context.get("output_deliverables", "")
        if output_del:
            sections.append("## 输出交付物要求")
            sections.append(output_del)
            sections.append("")
            sections.append("**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。")
        
        return "\n".join(sections) if sections else ""

    def _build_initial_step_description(
        self,
        step: WorkflowStepConfig,
        initial_input: dict
    ) -> str:
        """
        构建初始步骤执行描述 (v0.4.6)
        
        为工作流第一个步骤生成包含初始输入、输入要求、输出交付物的描述
        
        Args:
            step: 步骤配置
            initial_input: 初始输入数据
            
        Returns:
            格式化的步骤描述
        """
        sections = []
        
        # 1. 初始输入
        if initial_input:
            sections.append("## 初始输入")
            if isinstance(initial_input, dict):
                for key, value in initial_input.items():
                    sections.append(f"**{key}**: {value}")
            else:
                sections.append(str(initial_input))
            sections.append("")
        
        # 2. 输入要求
        if step.input_requirements:
            sections.append("## 输入要求")
            sections.append(step.input_requirements)
            sections.append("")
        
        # 3. 输出交付物
        if step.output_deliverables:
            sections.append("## 输出交付物要求")
            sections.append(step.output_deliverables)
            sections.append("")
            sections.append("**重要**: 请确保你的 OPC-REPORT 中包含上述交付物。")
        
        return "\n".join(sections) if sections else ""

    async def _pause_downstream_tasks(self, from_task_id: str) -> None:
        """暂停从指定任务开始的所有下游任务"""
        current_id = from_task_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            task = await self.task_repo.get_by_id(current_id)
            if not task:
                break

            # 如果任务还在 pending/assigned 状态，标记为暂停
            if task.status in [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value]:
                task.status = TaskStatus.FAILED.value  # 或使用新的状态
                await self.task_repo.update(task)

            current_id = task.next_task_id

    async def _finalize_workflow(self, workflow_id: str) -> None:
        """标记工作流完成"""
        # 收集最终结果
        tasks = await self.task_repo.get_by_workflow(workflow_id)
        if tasks:
            last_task = max(tasks, key=lambda t: t.step_index)

            # 记录完成日志
            last_task.add_execution_log({
                "event": "workflow_completed",
                "workflow_id": workflow_id,
                "total_steps": len(tasks),
            })
            await self.task_repo.update(last_task)

    # ============================================================
    # 查询方法
    # ============================================================

    async def get_workflow_progress(self, workflow_id: str) -> Optional[WorkflowProgress]:
        """获取工作流进度"""
        tasks = await self.task_repo.get_by_workflow(workflow_id)
        if not tasks:
            return None

        total_steps = tasks[0].total_steps
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED.value)

        # 找到当前进行中的步骤
        current_step = completed
        status = "running"

        if completed == total_steps:
            status = "completed"
        elif any(t.status == TaskStatus.FAILED.value for t in tasks):
            status = "failed"

        return WorkflowProgress(
            workflow_id=workflow_id,
            total_steps=total_steps,
            completed_steps=completed,
            current_step=current_step,
            status=status,
            progress_percent=round(completed / total_steps * 100, 1),
        )

    async def get_workflow_tasks(self, workflow_id: str) -> list[Task]:
        """获取工作流的所有任务"""
        return await self.task_repo.get_by_workflow(workflow_id)


__all__ = [
    "WorkflowService",
    "WorkflowStepConfig",
    "WorkflowResult",
    "WorkflowProgress",
    "WorkflowError",
    "WorkflowNotFoundError",
    "InvalidStepConfigError",
    "ReworkLimitExceeded",
    "InvalidReworkTarget",
]
