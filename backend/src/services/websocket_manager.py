"""
WebSocket Manager v0.5.6

WebSocket连接管理和消息推送
"""

import json
from typing import Dict, Set

from starlette.websockets import WebSocket, WebSocketDisconnect

from utils.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 用户ID -> WebSocket连接集合
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> 用户ID
        self.connection_to_user: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        self.connection_to_user[websocket] = user_id
        
        logger.info("websocket_connected", user_id=user_id, connections=len(self.active_connections[user_id]))
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "data": {
                "user_id": user_id,
                "message": "WebSocket connected successfully"
            }
        })
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        user_id = self.connection_to_user.get(websocket)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # 如果没有连接了，清理
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if websocket in self.connection_to_user:
            del self.connection_to_user[websocket]
        
        logger.info("websocket_disconnected", user_id=user_id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """发送消息给特定用户（所有连接）"""
        if user_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("websocket_send_error", user_id=user_id, error=str(e))
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_to_users(self, user_ids: list, message: dict):
        """批量发送消息给多个用户"""
        for user_id in user_ids:
            await self.send_to_user(user_id, message)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = []
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error("websocket_broadcast_error", error=str(e))
                    disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_online_users(self) -> list:
        """获取在线用户列表"""
        return list(self.active_connections.keys())
    
    def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


# 全局实例
websocket_manager = ConnectionManager()
