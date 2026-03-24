"""
opc-openclaw: CLI 消息发送器

通过 OpenClaw CLI 向 Agent 发送消息

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1
"""

import asyncio
import json
import os
import shlex
from dataclasses import dataclass
from enum import Enum as PyEnum
from typing import Any, Dict, Optional


class MessageType(PyEnum):
    """消息类型"""

    TASK = "task"  # 任务分配
    WAKEUP = "wakeup"  # 唤醒
    NOTIFICATION = "notification"  # 通知


@dataclass
class MessageResponse:
    """消息响应"""

    success: bool
    content: str = ""
    session_key: Optional[str] = None
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        """总Token消耗"""
        return self.tokens_input + self.tokens_output


class CLIMessenger:
    """
    CLI 消息发送器

    通过 openclaw CLI 命令向 Agent 发送消息：
    openclaw agent --agent <agent_id> --message "..." --json --timeout <sec>
    """

    OPENCLAW_BIN = os.getenv("OPENCLAW_BIN", "openclaw")

    def __init__(self, openclaw_bin: Optional[str] = None):
        """
        初始化

        Args:
            openclaw_bin: OpenClaw CLI 路径，默认从环境变量读取
        """
        self.openclaw_bin = openclaw_bin or self.OPENCLAW_BIN

    async def send(
        self,
        agent_id: str,
        message: str,
        message_type: MessageType = MessageType.TASK,
        timeout: int = 900,  # 默认 15 分钟
    ) -> MessageResponse:
        """
        发送消息给 Agent

        使用 CLI: openclaw agent --agent <id> --message "..." --json --timeout <sec>

        Args:
            agent_id: Agent ID（必须以 opc_ 开头）
            message: 消息内容（纯文本）
            message_type: 消息类型（用于日志）
            timeout: 超时时间（秒），默认 900（15 分钟）

        Returns:
            MessageResponse: 包含响应内容、token 消耗等信息
        """
        # 构建 CLI 命令
        cmd = [
            self.openclaw_bin,
            "agent",
            "--agent", agent_id,
            "--message", message,
            "--json",
            "--timeout", str(timeout),
        ]

        try:
            # 使用 asyncio 创建子进程（非阻塞）
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 等待完成（带超时缓冲）
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout + 10  # 额外 10 秒缓冲
                )
            except asyncio.TimeoutError:
                proc.kill()
                return MessageResponse(
                    success=False,
                    error=f"Timeout after {timeout + 10}s"
                )

            # 检查返回码
            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                return MessageResponse(
                    success=False,
                    error=f"CLI error (code {proc.returncode}): {error_msg}"
                )

            # 解析响应
            stdout_text = stdout.decode("utf-8", errors="replace").strip()
            return self._parse_response(stdout_text)

        except FileNotFoundError:
            return MessageResponse(
                success=False,
                error=f"OpenClaw CLI not found: {self.openclaw_bin}"
            )
        except Exception as e:
            return MessageResponse(success=False, error=str(e))

    def _parse_response(self, stdout: str) -> MessageResponse:
        """
        解析 CLI JSON 响应

        OpenClaw CLI 输出格式：
        {
            "runId": "...",
            "status": "ok",
            "result": {
                "payloads": [{"text": "..."}],
                "meta": {
                    "agentMeta": {
                        "sessionId": "...",
                        "usage": {"input": 65, "output": 41}
                    }
                }
            }
        }
        """
        if not stdout:
            return MessageResponse(success=True, content="")

        # 提取 JSON 部分（过滤掉 Config warnings 等非 JSON 输出）
        json_start = stdout.find("{")
        if json_start == -1:
            return MessageResponse(success=True, content=stdout.strip())

        json_text = stdout[json_start:]

        try:
            data = json.loads(json_text)

            if not isinstance(data, dict):
                return MessageResponse(success=True, content=str(data))

            # 检查状态
            status = data.get("status", "")
            if status == "error":
                return MessageResponse(
                    success=False,
                    error=data.get("error", "Unknown error")
                )

            result = data.get("result", {})

            # 提取文本内容（从 payloads）
            content = ""
            payloads = result.get("payloads", [])
            if payloads and isinstance(payloads, list):
                texts = [p.get("text", "") for p in payloads if p.get("text")]
                content = "\n".join(texts)

            # 提取 session_key（从 meta.agentMeta.sessionId）
            session_key = None
            meta = result.get("meta", {})
            if isinstance(meta, dict):
                agent_meta = meta.get("agentMeta", {})
                if isinstance(agent_meta, dict):
                    session_key = agent_meta.get("sessionKey") or agent_meta.get("sessionId")

            # 提取 token 信息（从 meta.agentMeta.usage）
            tokens_input = 0
            tokens_output = 0
            if isinstance(meta, dict):
                agent_meta = meta.get("agentMeta", {})
                if isinstance(agent_meta, dict):
                    usage = agent_meta.get("usage", {})
                    if isinstance(usage, dict):
                        tokens_input = usage.get("input", 0)
                        tokens_output = usage.get("output", 0)

            return MessageResponse(
                success=status == "ok",
                content=content,
                session_key=session_key,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
            )

        except json.JSONDecodeError:
            # 非 JSON 响应，直接返回文本
            return MessageResponse(success=True, content=stdout.strip())

    async def check_response(self, session_key: str) -> MessageResponse:
        """
        检查会话响应（预留接口，CLI 模式不支持异步查询）

        Args:
            session_key: 会话标识

        Returns:
            MessageResponse

        Note:
            CLI 模式是同步阻塞的，此方法预留用于未来扩展
        """
        return MessageResponse(
            success=False,
            error="CLI mode does not support async response checking. Use send() with appropriate timeout."
        )


# 向后兼容：保留 Messenger 别名
Messenger = CLIMessenger

__all__ = [
    "CLIMessenger",
    "Messenger",  # 向后兼容
    "MessageType",
    "MessageResponse",
]