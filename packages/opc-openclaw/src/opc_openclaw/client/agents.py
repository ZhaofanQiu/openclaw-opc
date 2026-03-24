"""
opc-openclaw: CLI Agent 客户端

通过 OpenClaw CLI 获取 Agent 信息

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.1
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional


class CLIAgentClient:
    """
    OpenClaw Agent CLI 客户端

    通过 CLI 命令获取 Agent 信息：
    - openclaw agents list
    - openclaw agent --agent <id>
    """

    OPENCLAW_BIN = os.getenv("OPENCLAW_BIN", "openclaw")

    def __init__(self, openclaw_bin: Optional[str] = None):
        """
        初始化

        Args:
            openclaw_bin: OpenClaw CLI 路径
        """
        self.openclaw_bin = openclaw_bin or self.OPENCLAW_BIN

    async def _run_cli(self, *args) -> tuple[int, str, str]:
        """
        运行 CLI 命令

        Args:
            *args: 命令参数

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = [self.openclaw_bin] + list(args)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return (
                proc.returncode,
                stdout.decode("utf-8", errors="replace").strip(),
                stderr.decode("utf-8", errors="replace").strip(),
            )
        except FileNotFoundError:
            return (-1, "", f"OpenClaw CLI not found: {self.openclaw_bin}")
        except Exception as e:
            return (-1, "", str(e))

    async def list_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有可用 Agent 列表

        命令: openclaw agents list --json

        Returns:
            Agent 列表
        """
        returncode, stdout, stderr = await self._run_cli("agents", "list", "--json")

        if returncode != 0:
            return []

        # 提取 JSON 部分（过滤掉 Config warnings）
        json_start = stdout.find("[")
        if json_start == -1:
            return []

        json_text = stdout[json_start:]

        try:
            data = json.loads(json_text)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        return []

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 详情

        命令: openclaw agent --agent <id> --json

        Args:
            agent_id: Agent ID

        Returns:
            Agent 详情，不存在返回 None
        """
        returncode, stdout, stderr = await self._run_cli(
            "agent", "--agent", agent_id, "--json"
        )

        if returncode != 0:
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    async def check_agent_health(self, agent_id: str) -> bool:
        """
        检查 Agent 是否健康可用

        Args:
            agent_id: Agent ID

        Returns:
            是否可用
        """
        # 尝试获取 agent 信息
        agent = await self.get_agent(agent_id)
        if agent:
            status = agent.get("status", "").lower()
            return status != "offline" and status != "error"

        # 备选：尝试发送一个空消息检查
        returncode, _, _ = await self._run_cli(
            "agent", "--agent", agent_id, "--message", "ping", "--timeout", "5"
        )
        return returncode == 0

    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        获取 Agent 状态

        Args:
            agent_id: Agent ID

        Returns:
            {
                "agent_id": "...",
                "status": "online/offline/busy",
                "active_sessions": 0
            }
        """
        agent = await self.get_agent(agent_id)

        if agent:
            return {
                "agent_id": agent_id,
                "status": agent.get("status", "unknown"),
                "active_sessions": agent.get("active_sessions", 0),
            }

        return {
            "agent_id": agent_id,
            "status": "unknown",
            "active_sessions": 0,
        }


# 向后兼容：保留 AgentClient 别名
AgentClient = CLIAgentClient

__all__ = ["CLIAgentClient", "AgentClient"]