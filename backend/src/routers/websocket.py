"""
WebSocket Router v0.5.6

WebSocket实时通信
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.websocket_manager import websocket_manager
from src.services.workflow_notification_service import WorkflowNotificationService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str = Query(..., description="用户ID"),
    token: str = Query(..., description="认证令牌"),
):
    """
    WebSocket通知连接
    
    连接后会实时接收：
    - 任务分配通知
    - 步骤完成通知
    - 返工通知
    - 熔断通知
    - 系统公告
    """
    # TODO: 验证token
    
    await websocket_manager.connect(websocket, user_id)
    
    # 注入WebSocket管理器到通知服务
    WorkflowNotificationService.set_websocket_manager(websocket_manager)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            # 处理心跳
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            # 处理标记已读
            elif data.get("type") == "mark_read":
                notification_id = data.get("notification_id")
                # 可以在这里处理标记已读逻辑
                await websocket.send_json({
                    "type": "mark_read_ack",
                    "data": {"notification_id": notification_id, "status": "ok"}
                })
            
            # 处理订阅更新
            elif data.get("type") == "update_subscription":
                # 更新用户的通知订阅偏好
                await websocket.send_json({
                    "type": "subscription_updated",
                    "data": {"status": "ok"}
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error("websocket_error", user_id=user_id, error=str(e))
        websocket_manager.disconnect(websocket)


@router.websocket("/workflow/{workflow_id}")
async def websocket_workflow(
    websocket: WebSocket,
    workflow_id: str,
    user_id: str = Query(...),
):
    """
    特定工作流的实时更新
    
    连接后会实时接收该工作流的所有状态变化
    """
    await websocket_manager.connect(websocket, user_id)
    
    # 发送当前工作流状态
    # TODO: 获取并发送当前工作流状态
    await websocket.send_json({
        "type": "workflow_subscribed",
        "data": {"workflow_id": workflow_id}
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)


# REST API用于通知管理
@router.get("/notifications/unread")
async def get_unread_notifications(
    agent_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取未读通知"""
    service = WorkflowNotificationService(db)
    notifications = service.get_unread_notifications(agent_id, limit)
    
    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "priority": n.priority,
                "workflow_id": n.workflow_id,
                "step_id": n.step_id,
                "data": n.data_snapshot,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
        "count": len(notifications),
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """标记通知为已读"""
    service = WorkflowNotificationService(db)
    success = service.mark_as_read(notification_id, agent_id)
    return {"success": success}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """标记所有通知为已读"""
    service = WorkflowNotificationService(db)
    count = service.mark_all_as_read(agent_id)
    return {"success": True, "marked_count": count}


@router.get("/online-users")
async def get_online_users():
    """获取在线用户列表"""
    return {
        "online_users": websocket_manager.get_online_users(),
        "count": len(websocket_manager.get_online_users()),
    }
