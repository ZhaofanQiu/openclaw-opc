"""
OpenClaw Client - 同步/异步双模式实现

核心功能：
1. 同步模式：调用 CLI 直接等待响应
2. 异步模式：后台执行，通过状态查询获取结果
3. 纯文本通信，手册通过路径引用
4. Skill 提供手册读取和 API 调用能力
"""

import os
import json
import asyncio
import subprocess
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx
from utils.logging_config import get_logger

logger = get_logger(__name__)

# OpenClaw 配置
OPENCLAW_BIN = os.getenv("OPENCLAW_BIN", "openclaw")
OPC_API_URL = os.getenv("OPC_API_URL", "http://localhost:8080")


class ExecutionMode(Enum):
    """执行模式"""
    SYNC = "sync"       # 同步等待响应
    ASYNC = "async"     # 异步后台执行


@dataclass
class AgentResponse:
    """Agent 响应"""
    success: bool
    text: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    error: Optional[str] = None
    execution_id: Optional[str] = None  # 异步模式使用
    status: str = "completed"  # pending/running/completed/failed


@dataclass
class ExecutionRecord:
    """执行记录（用于异步模式）"""
    execution_id: str
    agent_id: str
    task_id: str
    message: str
    status: str  # pending/running/completed/failed
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    response: Optional[AgentResponse] = None
    

class OpenClawClient:
    """
    OpenClaw 客户端
    
    支持同步/异步双模式：
    - 同步：直接调用 CLI，阻塞等待响应
    - 异步：后台执行，通过 execution_id 查询状态
    """
    
    def __init__(self, 
                 openclaw_bin: str = OPENCLAW_BIN,
                 opc_api_url: str = OPC_API_URL):
        self.openclaw_bin = openclaw_bin
        self.opc_api_url = opc_api_url
        self._executions: Dict[str, ExecutionRecord] = {}  # 异步执行记录
        
    # ============ 核心发送方法 ============
    
    async def send_message(self,
                          agent_id: str,
                          message: str,
                          mode: ExecutionMode = ExecutionMode.SYNC,
                          timeout: int = 300,
                          agent_name: str = None,
                          task_id: str = None) -> AgentResponse:
        """
        发送消息给 Agent
        
        Args:
            agent_id: OpenClaw Agent ID
            message: 消息文本（包含三维度控制描述）
            mode: 执行模式（同步/异步）
            timeout: 超时时间（秒）
            agent_name: Agent名称（用于日志记录）
            task_id: 任务ID（用于日志记录）
        
        Returns:
            AgentResponse: 同步模式直接返回结果，异步模式返回 execution_id
        """
        import time
        start_time = time.time()
        
        if mode == ExecutionMode.SYNC:
            response = await self._send_sync(agent_id, message, timeout)
        else:
            response = await self._send_async(agent_id, message, timeout)
        
        # 记录交互日志
        duration_ms = int((time.time() - start_time) * 1000)
        self._log_interaction(
            agent_id=agent_id,
            agent_name=agent_name or agent_id,
            direction="outgoing",
            content=message,
            response=response.text if response.success else None,
            duration_ms=duration_ms,
            success=response.success,
            error_message=response.error,
            metadata={"mode": mode.value, "task_id": task_id, "execution_id": response.execution_id}
        )
        
        return response
    
    async def _send_sync(self, 
                        agent_id: str, 
                        message: str, 
                        timeout: int) -> AgentResponse:
        """同步发送：调用 CLI 等待响应"""
        try:
            logger.info(f"[SYNC] Sending message to agent {agent_id}")
            
            cmd = [
                self.openclaw_bin, "agent",
                "--agent", agent_id,
                "--message", message,
                "--json",
                "--timeout", str(timeout)
            ]
            
            # 使用 asyncio 创建子进程（非阻塞）
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待完成（带超时）
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout + 10
                )
            except asyncio.TimeoutError:
                proc.kill()
                return AgentResponse(
                    success=False,
                    text="",
                    error=f"Timeout after {timeout}s"
                )
            
            if proc.returncode != 0:
                error_msg = stderr.decode().strip() if stderr else "Unknown error"
                logger.error(f"[SYNC] Agent command failed: {error_msg}")
                return AgentResponse(
                    success=False,
                    text="",
                    error=error_msg
                )
            
            # 解析响应
            return self._parse_agent_response(stdout.decode())
            
        except Exception as e:
            logger.error(f"[SYNC] Failed to send message: {e}")
            return AgentResponse(
                success=False,
                text="",
                error=str(e)
            )
    
    async def _send_async(self,
                         agent_id: str,
                         message: str,
                         timeout: int) -> AgentResponse:
        """异步发送：后台执行，返回 execution_id"""
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        # 创建执行记录
        record = ExecutionRecord(
            execution_id=execution_id,
            agent_id=agent_id,
            task_id="",  # 由调用方填充
            message=message,
            status="pending",
            created_at=datetime.utcnow()
        )
        self._executions[execution_id] = record
        
        # 后台执行
        asyncio.create_task(
            self._background_execute(execution_id, agent_id, message, timeout)
        )
        
        logger.info(f"[ASYNC] Execution {execution_id} started for agent {agent_id}")
        
        return AgentResponse(
            success=True,
            text="",
            execution_id=execution_id,
            status="pending"
        )
    
    async def _background_execute(self,
                                 execution_id: str,
                                 agent_id: str,
                                 message: str,
                                 timeout: int):
        """后台执行任务"""
        record = self._executions[execution_id]
        record.status = "running"
        record.started_at = datetime.utcnow()
        
        # 调用同步方法
        response = await self._send_sync(agent_id, message, timeout)
        
        # 更新记录
        record.response = response
        record.status = "completed" if response.success else "failed"
        record.completed_at = datetime.utcnow()
        
        logger.info(f"[ASYNC] Execution {execution_id} completed: {record.status}")
    
    def _parse_agent_response(self, stdout: str) -> AgentResponse:
        """解析 Agent 响应"""
        try:
            data = json.loads(stdout)
            
            # 处理嵌套结构
            # { "status": "ok", "result": { "payloads": [{ "text": "..." }], "meta": { "agentMeta": { "usage": {...} } } } }
            text_content = ""
            tokens_input = 0
            tokens_output = 0
            
            if isinstance(data, dict):
                if "result" in data and isinstance(data["result"], dict):
                    inner = data["result"]
                    payloads = inner.get("payloads", [])
                    if payloads:
                        text_content = payloads[0].get("text", "")
                    
                    # 解析 token 使用情况
                    meta = inner.get("meta", {})
                    agent_meta = meta.get("agentMeta", {})
                    usage = agent_meta.get("usage", {})
                    tokens_input = usage.get("input", 0)
                    tokens_output = usage.get("output", 0)
                
                if not text_content:
                    payloads = data.get("payloads", [])
                    if payloads:
                        text_content = payloads[0].get("text", "")
                
                if not text_content:
                    text_content = stdout
            else:
                text_content = str(data)
            
            return AgentResponse(
                success=True,
                text=text_content,
                tokens_input=tokens_input,
                tokens_output=tokens_output
            )
            
        except json.JSONDecodeError:
            # 非 JSON 响应，返回原始文本
            return AgentResponse(
                success=True,
                text=stdout.strip()
            )
    
    # ============ 异步查询方法 ============
    
    def get_execution_status(self, execution_id: str) -> Optional[AgentResponse]:
        """
        查询异步执行状态
        
        Returns:
            None: execution_id 不存在
            AgentResponse: 当前状态（status 字段表示进度）
        """
        record = self._executions.get(execution_id)
        if not record:
            return None
        
        if record.response:
            # 已完成，返回结果
            return record.response
        else:
            # 进行中，返回状态
            return AgentResponse(
                success=True,
                text="",
                execution_id=execution_id,
                status=record.status
            )
    
    def wait_for_completion(self, 
                           execution_id: str,
                           poll_interval: int = 2,
                           timeout: int = 300) -> Optional[AgentResponse]:
        """
        等待异步执行完成
        
        轮询等待直到任务完成或超时
        """
        import time
        start_time = time.time()
        
        while True:
            response = self.get_execution_status(execution_id)
            if not response:
                return None
            
            if response.status in ["completed", "failed"]:
                return response
            
            # 检查超时
            if time.time() - start_time > timeout:
                return AgentResponse(
                    success=False,
                    text="",
                    error="Wait timeout"
                )
            
            time.sleep(poll_interval)
    
    def _log_interaction(self,
                         agent_id: str,
                         agent_name: str,
                         direction: str,
                         content: str,
                         response: str = None,
                         duration_ms: int = None,
                         success: bool = True,
                         error_message: str = None,
                         metadata: Dict = None):
        """
        记录Agent交互日志
        
        调用日志服务记录交互详情
        """
        try:
            from services.agent_interaction_log_service_v2 import AgentInteractionLogService
            
            AgentInteractionLogService.log(
                agent_id=agent_id,
                agent_name=agent_name,
                interaction_type="message",
                direction=direction,
                content=content,
                response=response,
                metadata=metadata,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message
            )
        except Exception as e:
            # 日志记录失败不应影响主流程
            logger.warning(f"Failed to log interaction: {e}")


# ============ 便捷函数 ============

async def send_to_agent(agent_id: str,
                       message: str,
                       async_mode: bool = False,
                       timeout: int = 300) -> AgentResponse:
    """
    便捷函数：发送消息给 Agent
    
    Args:
        agent_id: Agent ID
        message: 消息文本
        async_mode: 是否异步执行
        timeout: 超时时间
    """
    client = OpenClawClient()
    mode = ExecutionMode.ASYNC if async_mode else ExecutionMode.SYNC
    return await client.send_message(agent_id, message, mode, timeout)


async def wake_up_agent(agent_id: str, agent_name: str) -> AgentResponse:
    """
    唤醒 Agent
    
    发送唤醒消息，让 Agent 进入待命状态
    """
    message = f"""# OPC 员工唤醒

你是 {agent_name}，是 OpenClaw OPC 的一名员工。

## 当前状态
你现在处于待命状态，等待任务分配。

## 可用能力
- 你可以通过 opc_* 函数调用 OPC API
- 你可以通过 opc_read_manual(path) 读取手册
- 你可以通过 opc_report_task_result() 报告任务结果

请回复确认你已准备就绪。
"""
    
    client = OpenClawClient()
    return await client.send_message(agent_id, message, ExecutionMode.SYNC, 60)


async def assign_task(agent_id: str,
                     agent_name: str,
                     task_id: str,
                     task_title: str,
                     task_description: str,
                     manual_paths: Optional[Dict[str, str]] = None,
                     async_mode: bool = True) -> AgentResponse:
    """
    分配任务给 Agent
    
    发送包含三维度控制的任务消息
    
    Args:
        manual_paths: 手册路径字典，如 {"task": "/path/to/task.md", "position": "/path/to/position.md"}
    """
    if manual_paths is None:
        manual_paths = {}
    
    # 构建消息（只包含路径，不包含内容）
    message_parts = [
        f"# 任务分配",
        f"",
        f"## 任务信息",
        f"- 任务ID: {task_id}",
        f"- 标题: {task_title}",
        f"- 描述: {task_description}",
        f"",
        f"## 参考手册（请主动读取）",
    ]
    
    for manual_type, path in manual_paths.items():
        message_parts.append(f"- {manual_type}: {path}")
    
    message_parts.extend([
        f"",
        f"## 执行要求",
        f"1. 先通过 opc_read_manual(path) 读取相关手册",
        f"2. 根据手册规范和任务描述执行",
        f"3. 如需查询预算，调用 opc_get_budget()",
        f"4. 完成后调用 opc_report_task_result(task_id='{task_id}', result='结果', tokens_used=数量)",
        f"5. 如果无法完成，报告失败状态和原因",
    ])
    
    message = "\n".join(message_parts)
    
    client = OpenClawClient()
    mode = ExecutionMode.ASYNC if async_mode else ExecutionMode.SYNC
    return await client.send_message(agent_id, message, mode, timeout=300)
