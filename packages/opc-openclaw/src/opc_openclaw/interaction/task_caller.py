"""
opc-openclaw: 任务调用器

向 Agent 分配任务并获取响应

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .messenger import CLIMessenger, MessageType


@dataclass
class TaskAssignment:
    """任务分配信息"""

    task_id: str
    title: str
    description: str
    agent_id: str  # OpenClaw Agent ID（必须以 opc- 开头）
    agent_name: str  # 员工名称（用于消息）
    employee_id: str  # OPC 员工ID
    company_manual_path: str  # 公司手册绝对路径
    employee_manual_path: str  # 员工手册绝对路径
    task_manual_path: str  # 任务手册绝对路径
    timeout: int = 900  # 超时时间（秒），默认 15 分钟

    # 预算信息（v2.0.0 新增）
    monthly_budget: float = 0.0  # 本月预算（OC币）
    used_budget: float = 0.0  # 已使用预算
    remaining_budget: float = 0.0  # 剩余预算

    # ========== v0.4.2 新增：工作流支持 ==========
    # 工作流上下文
    workflow_id: Optional[str] = None  # 工作流ID
    step_index: int = 0  # 当前步骤索引
    total_steps: int = 1  # 工作流总步骤数

    # 结构化数据传递
    input_data: Optional[dict] = None  # 输入数据（包含前置步骤输出）

    # 返工上下文
    is_rework: bool = False  # 是否为返工任务
    rework_context: Optional[dict] = None  # 返工上下文信息


@dataclass
class TaskResponse:
    """任务响应"""

    success: bool
    content: str = ""  # Agent 回复内容
    session_key: Optional[str] = None  # 会话标识
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        """总 Token 消耗"""
        return self.tokens_input + self.tokens_output


class TaskCaller:
    """
    任务调用器

    封装向 Agent 分配任务的完整流程：
    1. 构建任务消息（包含手册路径和 skill 指引）
    2. 使用 CLIMessenger 发送消息
    3. 解析响应
    """

    def __init__(self, messenger: Optional[CLIMessenger] = None):
        """
        初始化

        Args:
            messenger: CLIMessenger 实例（可选）
        """
        self.messenger = messenger or CLIMessenger()

    def _build_message(self, task: TaskAssignment) -> str:
        """
        构建任务分配消息

        支持工作流任务和返工任务
        """
        # 确保路径是绝对路径
        company_path = self._to_absolute_path(task.company_manual_path)
        employee_path = self._to_absolute_path(task.employee_manual_path)
        task_path = self._to_absolute_path(task.task_manual_path)

        sections = []

        # ========== 标题部分 ==========
        if task.workflow_id and task.total_steps > 1:
            sections.append(f"# 工作流任务: {task.title}")
            sections.append(f"**步骤**: {task.step_index + 1}/{task.total_steps}")
            sections.append(f"**工作流ID**: {task.workflow_id}")
        else:
            sections.append(f"# 任务分配: {task.title}")

        sections.append(f"\n你是 {task.agent_name}（ID: {task.employee_id}）\n")

        # ========== 返工提示（如适用）==========
        if task.is_rework and task.rework_context:
            ctx = task.rework_context
            sections.append("## ⚠️ 返工任务")
            sections.append(f"**返工次数**: {ctx.get('rework_count', 1)}/{ctx.get('max_rework', 3)}")
            sections.append(f"**返工原因**: {ctx.get('reason', '未指定')}")
            if ctx.get('instructions'):
                sections.append(f"**返工要求**: {ctx.get('instructions')}")
            if ctx.get('triggered_by_name'):
                sections.append(f"**触发者**: {ctx.get('triggered_by_name')}")
            sections.append("\n---\n")

        # ========== 前置步骤输出（工作流）==========
        if task.input_data and task.input_data.get("previous_outputs"):
            sections.append("## 📥 前置步骤输出")
            for prev in task.input_data["previous_outputs"]:
                step_num = prev.get("step_index", 0) + 1
                emp_name = prev.get("employee_name", "未知员工")
                sections.append(f"\n### Step {step_num}: {emp_name}")

                # 输出摘要
                summary = prev.get("output_summary", "")
                if summary:
                    sections.append(f"**执行摘要**: {summary[:200]}..." if len(summary) > 200 else f"**执行摘要**: {summary}")

                # 结构化输出（可选展示）
                structured = prev.get("structured_output")
                if structured:
                    import json
                    sections.append("**结构化数据**:")
                    sections.append(f"```json\n{json.dumps(structured, ensure_ascii=False, indent=2)[:500]}...\n```" if len(json.dumps(structured)) > 500 else f"```json\n{json.dumps(structured, ensure_ascii=False, indent=2)}\n```")

                # 元数据
                metadata = prev.get("metadata", {})
                if metadata:
                    tokens = metadata.get("tokens_used", 0)
                    sections.append(f"*Token消耗: {tokens}*")

            sections.append("\n---\n")

        # ========== 手册路径 ==========
        sections.append("## 📚 执行前必须阅读以下手册")
        sections.append(f"1. 公司手册: `{company_path}`")
        sections.append(f"2. 员工手册: `{employee_path}`")
        sections.append(f"3. 任务手册: `{task_path}`")
        sections.append("\n**重要**: 使用上述绝对路径读取手册文件。\n")

        # ========== 任务描述 ==========
        sections.append("## 📝 你的任务")
        sections.append(task.description)

        # ========== 预算信息 ==========
        if task.monthly_budget > 0:
            sections.append("\n## 💰 预算信息")
            sections.append(f"- 本月预算: {task.monthly_budget:.2f} OC币")
            sections.append(f"- 已使用: {task.used_budget:.2f} OC币")
            sections.append(f"- 剩余: {task.remaining_budget:.2f} OC币")

        # ========== 输出格式要求 ==========
        sections.append("\n## ⚠️ 输出格式要求")
        sections.append("任务完成后，在回复末尾包含以下报告块：\n")
        sections.append("```")
        sections.append("---OPC-REPORT---")
        sections.append(f"task_id: {task.task_id}")
        sections.append("status: completed|failed|needs_revision")
        sections.append("tokens_used: <实际消耗的token数>")
        sections.append("summary: <任务完成总结>")
        sections.append("result_files: <结果文件绝对路径，逗号分隔>")
        sections.append("---END-REPORT---")
        sections.append("```\n")

        # 结构化输出要求
        sections.append("**结构化输出**（可选，JSON格式）：")
        sections.append("```")
        sections.append("---OPC-OUTPUT---")
        sections.append("{")
        sections.append('  "key1": "value1",')
        sections.append('  "key2": ["item1", "item2"]')
        sections.append("}")
        sections.append("---END-OUTPUT---")
        sections.append("```\n")

        # 返工标记（仅工作流）
        if task.workflow_id:
            sections.append("**如需返工到上游步骤**，添加：")
            sections.append("```")
            sections.append("---OPC-REWORK---")
            sections.append("target_step: <目标步骤索引(从0开始)>")
            sections.append("reason: <返工原因>")
            sections.append("instructions: <返工指令>")
            sections.append("---END-REWORK---")
            sections.append("```\n")

        sections.append("---")
        sections.append("立即开始：先阅读手册，然后执行任务！")

        return "\n".join(sections)

    def _to_absolute_path(self, path: str) -> str:
        """
        转换为绝对路径

        Args:
            path: 路径（可能是相对或绝对）

        Returns:
            绝对路径
        """
        if not path:
            return ""
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(p.absolute())

    async def assign_task(self, task: TaskAssignment) -> TaskResponse:
        """
        分配任务给 Agent

        Args:
            task: 任务分配信息

        Returns:
            TaskResponse
        """
        # 构建消息
        message = self._build_message(task)

        # 发送消息
        response = await self.messenger.send(
            agent_id=task.agent_id,
            message=message,
            message_type=MessageType.TASK,
            timeout=task.timeout,
        )

        # 转换为 TaskResponse
        return TaskResponse(
            success=response.success,
            session_key=response.session_key,
            content=response.content,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            error=response.error,
        )

    async def send_follow_up(
        self,
        agent_id: str,
        session_key: str,
        message: str,
        timeout: int = 900,
    ) -> TaskResponse:
        """
        发送跟进消息

        Args:
            agent_id: Agent ID
            session_key: 会话标识
            message: 跟进消息
            timeout: 超时时间

        Returns:
            TaskResponse

        Note:
            CLI 模式不支持会话保持，此方法是预留接口
        """
        # CLI 模式不支持会话保持，发送新消息
        response = await self.messenger.send(
            agent_id=agent_id,
            message=message,
            message_type=MessageType.TASK,
            timeout=timeout,
        )

        return TaskResponse(
            success=response.success,
            session_key=response.session_key,
            content=response.content,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
            error=response.error,
        )


__all__ = ["TaskCaller", "TaskAssignment", "TaskResponse"]