"""
WebSocket Router

实时推送 WebSocket 连接
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.websocket_manager import manager
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 连接端点
    
    客户端连接后可以通过发送消息订阅特定事件：
    - {"action": "subscribe_agent", "agent_id": "emp_xxx"}
    - {"action": "subscribe_task", "task_id": "task_xxx"}
    """
    await manager.connect(websocket)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully"
        })
        
        # 监听客户端消息
        while True:
            try:
                data = await websocket.receive_json()
                
                action = data.get("action")
                
                if action == "subscribe_agent":
                    agent_id = data.get("agent_id")
                    if agent_id:
                        manager.subscribe_agent(websocket, agent_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "target": "agent",
                            "agent_id": agent_id
                        })
                
                elif action == "subscribe_task":
                    task_id = data.get("task_id")
                    if task_id:
                        manager.subscribe_task(websocket, task_id)
                        await websocket.send_json({
                            "type": "subscribed",
                            "target": "task",
                            "task_id": task_id
                        })
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
                    
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        manager.disconnect(websocket)