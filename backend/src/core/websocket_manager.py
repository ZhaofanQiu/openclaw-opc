"""
WebSocket Manager

实时推送系统 - 向客户端推送事件
"""

import json
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 所有活跃连接
        self.active_connections: Set[WebSocket] = set()
        # 按Agent ID分组的连接
        self.agent_connections: Dict[str, Set[WebSocket]] = {}
        # 按任务ID分组的连接
        self.task_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        
        # 从分组中移除
        for agent_id, connections in self.agent_connections.items():
            connections.discard(websocket)
        
        for task_id, connections in self.task_connections.items():
            connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    def subscribe_agent(self, websocket: WebSocket, agent_id: str):
        """订阅Agent相关事件"""
        if agent_id not in self.agent_connections:
            self.agent_connections[agent_id] = set()
        self.agent_connections[agent_id].add(websocket)
        logger.debug(f"Subscribed to agent {agent_id}")
    
    def subscribe_task(self, websocket: WebSocket, task_id: str):
        """订阅任务相关事件"""
        if task_id not in self.task_connections:
            self.task_connections[task_id] = set()
        self.task_connections[task_id].add(websocket)
        logger.debug(f"Subscribed to task {task_id}")
    
    async def broadcast(self, message: dict):
        """广播给所有连接"""
        if not self.active_connections:
            return
        
        message["timestamp"] = datetime.utcnow().isoformat()
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_agent(self, agent_id: str, message: dict):
        """发送给关注特定Agent的连接"""
        connections = self.agent_connections.get(agent_id, set())
        if not connections:
            return
        
        message["timestamp"] = datetime.utcnow().isoformat()
        disconnected = set()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_task(self, task_id: str, message: dict):
        """发送给关注特定任务的连接"""
        connections = self.task_connections.get(task_id, set())
        if not connections:
            return
        
        message["timestamp"] = datetime.utcnow().isoformat()
        disconnected = set()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        for conn in disconnected:
            self.disconnect(conn)


# 全局连接管理器
manager = ConnectionManager()


# ============ 事件推送函数 ============

async def notify_task_assigned(task_id: str, agent_id: str, agent_name: str, task_title: str):
    """任务分配通知"""
    await manager.broadcast({
        "type": "task_assigned",
        "task_id": task_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "task_title": task_title
    })
    await manager.send_to_task(task_id, {
        "type": "task_update",
        "task_id": task_id,
        "status": "assigned",
        "agent_id": agent_id
    })


async def notify_task_started(task_id: str, agent_id: str):
    """任务开始通知"""
    await manager.broadcast({
        "type": "task_started",
        "task_id": task_id,
        "agent_id": agent_id
    })
    await manager.send_to_task(task_id, {
        "type": "task_update",
        "task_id": task_id,
        "status": "in_progress"
    })


async def notify_task_completed(task_id: str, agent_id: str, success: bool, cost: float):
    """任务完成通知"""
    await manager.broadcast({
        "type": "task_completed",
        "task_id": task_id,
        "agent_id": agent_id,
        "success": success,
        "cost": cost
    })
    await manager.send_to_task(task_id, {
        "type": "task_update",
        "task_id": task_id,
        "status": "completed" if success else "failed",
        "cost": cost
    })
    await manager.send_to_agent(agent_id, {
        "type": "agent_status_change",
        "agent_id": agent_id,
        "status": "idle"
    })


async def notify_agent_status_change(agent_id: str, status: str, current_task_id: str = None):
    """Agent状态变更通知"""
    await manager.broadcast({
        "type": "agent_status_change",
        "agent_id": agent_id,
        "status": status,
        "current_task_id": current_task_id
    })


async def notify_budget_update(agent_id: str, used_budget: float, monthly_budget: float):
    """预算更新通知"""
    await manager.broadcast({
        "type": "budget_update",
        "agent_id": agent_id,
        "used_budget": used_budget,
        "monthly_budget": monthly_budget,
        "remaining": monthly_budget - used_budget
    })


async def notify_log_created(log_data: dict):
    """新日志创建通知"""
    await manager.broadcast({
        "type": "log_created",
        "log": log_data
    })
