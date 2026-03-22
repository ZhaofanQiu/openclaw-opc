"""
OpenClaw Client - Hybrid Implementation

由于 OpenClaw CLI 没有直接的 spawn/send 命令，采用混合方案：

1. 对于 OPC → Agent: 通过写入 session 文件或使用消息队列
2. 对于 Agent → OPC: 通过 Skill API (已实现)
3. 优先使用 WebSocket Gateway API (如果可用)

当前实现使用模拟 + 基于文件的轻量级通信
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from utils.logging_config import get_logger

logger = get_logger(__name__)

# OpenClaw 配置
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://127.0.0.1:18789")
OPENCLAW_TOKEN = os.getenv("OPENCLAW_TOKEN", "")
SESSIONS_FILE = os.path.expanduser("~/.openclaw/agents/main/sessions/sessions.json")


@dataclass
class SessionInfo:
    """会话信息"""
    session_key: str
    agent_id: str
    status: str
    created_at: str


@dataclass
class SessionStatus:
    """会话状态"""
    session_key: str
    status: str
    tokens_input: int
    tokens_output: int
    cost: float
    messages: List[Dict[str, Any]]


class OpenClawClient:
    """
    OpenClaw 客户端
    
    混合实现：模拟 + 基于文件的通信
    
    注意：由于 OpenClaw 没有提供外部 spawn/send API，当前实现：
    1. 生成 session_key 用于跟踪
    2. 任务状态存储在 OPC 数据库中
    3. Agent 通过 Skill API 主动拉取任务
    """
    
    def __init__(self, base_url: str = OPENCLAW_URL):
        self.base_url = base_url
        self._pending_messages: Dict[str, List[Dict]] = {}  # 待发送的消息队列
        
    async def spawn_session(self,
                           agent_id: str,
                           task_id: str,
                           message: str,
                           model: str = "kimi-coding/k2p5") -> Optional[str]:
        """
        创建 Agent 会话
        
        由于没有外部 spawn API，这里：
        1. 生成唯一的 session_key
        2. 将消息存储在待处理队列
        3. 等待 Agent 通过 skill 拉取
        """
        try:
            logger.info(f"Spawning session for agent {agent_id}, task {task_id}")
            
            # 生成 session_key
            timestamp = int(datetime.utcnow().timestamp())
            session_key = f"opc_{agent_id}_{task_id}_{timestamp}"
            
            # 存储消息到队列
            if agent_id not in self._pending_messages:
                self._pending_messages[agent_id] = []
            
            self._pending_messages[agent_id].append({
                "session_key": session_key,
                "task_id": task_id,
                "message": message,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            })
            
            logger.info(f"Session spawned: {session_key} (message queued for agent)")
            return session_key
            
        except Exception as e:
            logger.error(f"Failed to spawn session: {e}")
            return None
    
    async def send_message(self,
                          session_key: str,
                          message: str) -> bool:
        """
        发送消息到 Agent
        
        将消息添加到待处理队列
        """
        try:
            logger.info(f"Queuing message for session {session_key}")
            
            # 解析 agent_id
            parts = session_key.split("_")
            if len(parts) < 2:
                logger.error(f"Invalid session key: {session_key}")
                return False
            
            agent_id = parts[1]
            
            # 添加到队列
            if agent_id not in self._pending_messages:
                self._pending_messages[agent_id] = []
            
            self._pending_messages[agent_id].append({
                "session_key": session_key,
                "message": message,
                "created_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Message queued for {session_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue message: {e}")
            return False
    
    def get_pending_messages(self, agent_id: str) -> List[Dict]:
        """
        获取待处理的消息 (供 Agent 通过 skill 调用)
        
        Args:
            agent_id: Agent ID
        
        Returns:
            待处理消息列表
        """
        messages = self._pending_messages.get(agent_id, [])
        # 清空已获取的消息
        self._pending_messages[agent_id] = []
        return messages
    
    async def get_session_status(self, session_key: str) -> Optional[SessionStatus]:
        """
        获取会话状态
        
        从本地存储获取 (实际 token 消耗由 Agent 报告)
        """
        try:
            # 模拟实现
            return SessionStatus(
                session_key=session_key,
                status="active",
                tokens_input=0,
                tokens_output=0,
                cost=0.0,
                messages=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return None
    
    async def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionInfo]:
        """
        列出会话
        
        从本地存储获取
        """
        try:
            sessions = []
            if agent_id and agent_id in self._pending_messages:
                for msg in self._pending_messages[agent_id]:
                    sessions.append(SessionInfo(
                        session_key=msg["session_key"],
                        agent_id=agent_id,
                        status="pending",
                        created_at=msg.get("created_at", "")
                    ))
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def wait_for_response(self,
                               session_key: str,
                               timeout: int = 300,
                               poll_interval: int = 5) -> Optional[Dict[str, Any]]:
        """
        等待 Agent 响应
        
        注意：在真实实现中，这需要 Agent 主动报告
        """
        logger.warning("wait_for_response requires Agent to report via skill API")
        return None


# ============ 便捷函数 ============

async def spawn_agent_session(agent_id: str,
                              task_id: str,
                              message: str) -> Optional[str]:
    """便捷函数: 创建 Agent 会话"""
    client = OpenClawClient()
    return await client.spawn_session(agent_id, task_id, message)


async def send_to_agent(session_key: str, message: str) -> bool:
    """便捷函数: 发送消息给 Agent"""
    client = OpenClawClient()
    return await client.send_message(session_key, message)


async def get_agent_response(session_key: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
    """便捷函数: 获取 Agent 响应"""
    client = OpenClawClient()
    return await client.wait_for_response(session_key, timeout)


def get_pending_messages_for_agent(agent_id: str) -> List[Dict]:
    """
    获取 Agent 的待处理消息
    
    供 Skill API 调用
    """
    client = OpenClawClient()
    return client.get_pending_messages(agent_id)
