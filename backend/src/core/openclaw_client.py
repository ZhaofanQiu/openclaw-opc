"""
OpenClaw Client

实现与 OpenClaw 的实际交互：
- sessions_spawn: 创建 Agent 会话
- sessions_send: 发送消息
- sessions_list: 列出会话
- session_status: 获取会话状态
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from utils.logging_config import get_logger

logger = get_logger(__name__)

# OpenClaw Gateway URL
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://localhost:8000")

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
    
    封装 OpenClaw API 调用
    """
    
    def __init__(self, base_url: str = OPENCLAW_URL):
        self.base_url = base_url
        self.timeout = 30
        
    async def spawn_session(self,
                           agent_id: str,
                           task_id: str,
                           message: str,
                           model: str = "kimi-coding/k2p5") -> Optional[str]:
        """
        创建 Agent 会话
        
        调用 OpenClaw sessions_spawn
        
        Returns:
            session_key: 会话密钥，用于后续交互
        """
        try:
            logger.info(f"Spawning session for agent {agent_id}, task {task_id}")
            
            # TODO: 实际调用 OpenClaw API
            # 这里先用模拟实现
            # from openclaw import sessions_spawn
            # result = await sessions_spawn(
            #     agent_id=agent_id,
            #     task=message,
            #     model=model
            # )
            # return result.get("session_key")
            
            # 模拟实现
            session_key = f"session_{agent_id}_{task_id}_{asyncio.get_event_loop().time()}"
            logger.info(f"Session spawned: {session_key}")
            return session_key
            
        except Exception as e:
            logger.error(f"Failed to spawn session: {e}")
            return None
    
    async def send_message(self,
                          session_key: str,
                          message: str) -> bool:
        """
        发送消息到 Agent
        
        调用 OpenClaw sessions_send
        """
        try:
            logger.info(f"Sending message to session {session_key}")
            
            # TODO: 实际调用 OpenClaw API
            # from openclaw import sessions_send
            # await sessions_send(
            #     session_key=session_key,
            #     message=message
            # )
            
            logger.info(f"Message sent to {session_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def get_session_status(self, session_key: str) -> Optional[SessionStatus]:
        """
        获取会话状态
        
        调用 OpenClaw session_status
        """
        try:
            logger.debug(f"Getting status for session {session_key}")
            
            # TODO: 实际调用 OpenClaw API
            # from openclaw import session_status
            # status = await session_status(session_key=session_key)
            
            # 模拟实现
            return SessionStatus(
                session_key=session_key,
                status="active",
                tokens_input=100,
                tokens_output=50,
                cost=0.001,
                messages=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return None
    
    async def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionInfo]:
        """
        列出会话
        
        调用 OpenClaw sessions_list
        """
        try:
            logger.debug(f"Listing sessions for agent {agent_id}")
            
            # TODO: 实际调用 OpenClaw API
            # from openclaw import sessions_list
            # sessions = await sessions_list(agent_id=agent_id)
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
    
    async def wait_for_response(self,
                               session_key: str,
                               timeout: int = 300,
                               poll_interval: int = 5) -> Optional[Dict[str, Any]]:
        """
        等待 Agent 响应
        
        轮询等待 Agent 回复
        
        Args:
            session_key: 会话密钥
            timeout: 超时时间（秒）
            poll_interval: 轮询间隔（秒）
        
        Returns:
            包含响应内容的字典，超时返回 None
        """
        try:
            logger.info(f"Waiting for response from session {session_key}")
            
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # 检查超时
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Timeout waiting for response from {session_key}")
                    return None
                
                # 获取会话状态
                status = await self.get_session_status(session_key)
                if status and status.messages:
                    # 有新消息
                    last_message = status.messages[-1]
                    logger.info(f"Received response from {session_key}")
                    return {
                        "content": last_message.get("content", ""),
                        "tokens_input": status.tokens_input,
                        "tokens_output": status.tokens_output,
                        "cost": status.cost
                    }
                
                # 等待后重试
                await asyncio.sleep(poll_interval)
                
        except Exception as e:
            logger.error(f"Error waiting for response: {e}")
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
