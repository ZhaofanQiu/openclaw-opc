"""
opc-openclaw: 任务调用器

向 Agent 分配任务并获取响应

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .messenger import CLIMessenger, MessageResponse, MessageType


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

        消息格式：
        - 明确指示使用 opc-bridge skill
        - 提供手册绝对路径
        - 提供预算信息（v2.0.0）
        - 说明如何报告结果
        """
        # 确保路径是绝对路径
        company_path = self._to_absolute_path(task.company_manual_path)
        employee_path = self._to_absolute_path(task.employee_manual_path)
        task_path = self._to_absolute_path(task.task_manual_path)

        # 预算信息部分
        budget_section = ""
        if task.monthly_budget > 0:
            budget_section = f"""## 💰 预算信息

- **本月预算**: {task.monthly_budget:.2f} OC币
- **已使用**: {task.used_budget:.2f} OC币
- **剩余**: {task.remaining_budget:.2f} OC币

⚠️ **注意**: 请高效使用 Token，注意预算限制。

"""

        message = f"""# 任务分配: {task.title}

你是 {task.agent_name}，是 OpenClaw OPC 的一名员工（ID: {task.employee_id}）。

## 📚 执行前必须阅读以下手册（使用绝对路径）

请先阅读以下手册文件：
1. 公司手册: {company_path}
2. 员工手册: {employee_path}
3. 任务手册: {task_path}

**重要**：使用上述绝对路径读取手册文件，不要假设相对路径。

## 📝 任务信息

- **任务ID**: {task.task_id}
- **标题**: {task.title}
- **描述**: {task.description}

{budget_section}## ⚠️ 关键要求

1. **先读手册，再执行任务**（使用上述绝对路径）

2. **任务完成后，在回复中包含报告**（必须）：

   使用以下格式在回复末尾报告任务完成情况：
   
   ```
   ---OPC-REPORT---
   task_id: {task.task_id}
   status: completed|failed|needs_revision
   tokens_used: <实际消耗的token数>
   summary: <任务完成总结>
   result_files: <结果文件绝对路径，逗号分隔，可选>
   ---END-REPORT---
   ```

3. **结果文件**: 将工作成果保存到文件，使用**绝对路径**

立即开始：先阅读手册，然后执行任务！
---
"""
        return message

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