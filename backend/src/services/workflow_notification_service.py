"""
Workflow Notification Service v0.5.6

实时通知服务
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from src.models import Agent, WorkflowInstance, WorkflowStep
from src.models.workflow_notification import (
    WorkflowNotification, NotificationSubscription,
    NotificationType, NotificationPriority, NotificationChannel
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowNotificationService:
    """工作流通知服务"""
    
    # WebSocket连接管理（将由WebSocket manager注入）
    _websocket_manager = None
    
    @classmethod
    def set_websocket_manager(cls, manager):
        """设置WebSocket管理器"""
        cls._websocket_manager = manager
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 核心通知方法 ==========
    
    def notify_step_assigned(self, step: WorkflowStep, workflow: WorkflowInstance):
        """通知步骤分配"""
        if not step.assignee_id:
            return
        
        self._create_and_send_notification(
            recipient_id=step.assignee_id,
            notification_type=NotificationType.STEP_ASSIGNED,
            title=f"新任务: {step.name}",
            message=f"你被分配了 '{workflow.title}' 的 '{step.name}' 步骤",
            workflow_id=workflow.id,
            step_id=step.id,
            priority=NotificationPriority.NORMAL,
            data_snapshot={
                "step_name": step.name,
                "step_type": step.step_type,
                "workflow_title": workflow.title,
                "budget": step.base_budget,
                "estimated_hours": step.estimated_hours,
            }
        )
    
    def notify_step_completed(self, step: WorkflowStep, workflow: WorkflowInstance):
        """通知步骤完成（通知Partner）"""
        # 通知Partner
        partner = self._get_partner()
        if partner:
            self._create_and_send_notification(
                recipient_id=partner.id,
                notification_type=NotificationType.STEP_COMPLETED,
                title=f"步骤完成: {step.name}",
                message=f"'{workflow.title}' 的 '{step.name}' 步骤已完成",
                workflow_id=workflow.id,
                step_id=step.id,
                priority=NotificationPriority.NORMAL,
                data_snapshot={
                    "step_name": step.name,
                    "workflow_title": workflow.title,
                    "actual_hours": step.actual_hours,
                    "budget_used": step.used_budget,
                }
            )
    
    def notify_rework_triggered(
        self, 
        from_step: WorkflowStep, 
        to_step: WorkflowStep, 
        workflow: WorkflowInstance,
        reason: str
    ):
        """通知返工触发"""
        # 通知被返工的员工
        self._create_and_send_notification(
            recipient_id=to_step.assignee_id,
            notification_type=NotificationType.REWORK_TRIGGERED,
            title=f"⚠️ 任务返工: {to_step.name}",
            message=f"'{workflow.title}' 的 '{to_step.name}' 需要返工。原因: {reason}",
            workflow_id=workflow.id,
            step_id=to_step.id,
            priority=NotificationPriority.HIGH,
            data_snapshot={
                "rework_step": to_step.name,
                "triggered_by": from_step.name,
                "rework_count": to_step.rework_count,
                "rework_limit": to_step.rework_limit,
                "reason": reason,
            }
        )
        
        # 通知Partner
        partner = self._get_partner()
        if partner:
            self._create_and_send_notification(
                recipient_id=partner.id,
                notification_type=NotificationType.REWORK_TRIGGERED,
                title=f"返工提醒: {workflow.title}",
                message=f"'{to_step.name}' 被 '{from_step.name}' 触发返工，当前第{to_step.rework_count}次",
                workflow_id=workflow.id,
                step_id=to_step.id,
                priority=NotificationPriority.NORMAL,
                data_snapshot={
                    "rework_step": to_step.name,
                    "rework_count": to_step.rework_count,
                    "rework_limit": to_step.rework_limit,
                }
            )
    
    def notify_rework_limit_warning(self, step: WorkflowStep, workflow: WorkflowInstance):
        """通知返工即将超限"""
        warning_threshold = step.rework_limit - 1
        if step.rework_count == warning_threshold:
            self._create_and_send_notification(
                recipient_id=step.assignee_id,
                notification_type=NotificationType.REWORK_LIMIT_WARNING,
                title=f"⚠️ 返工预警: {step.name}",
                message=f"注意: 此任务已返工{step.rework_count}次，再返工{step.rework_limit - step.rework_count}次将触发熔断",
                workflow_id=workflow.id,
                step_id=step.id,
                priority=NotificationPriority.HIGH,
                data_snapshot={
                    "rework_count": step.rework_count,
                    "rework_limit": step.rework_limit,
                    "remaining": step.rework_limit - step.rework_count,
                }
            )
    
    def notify_fused(
        self, 
        workflow: WorkflowInstance, 
        fuse_type: str,  # "budget" or "rework"
        details: Dict
    ):
        """通知熔断"""
        notification_type = (
            NotificationType.BUDGET_FUSED if fuse_type == "budget" 
            else NotificationType.REWORK_FUSED
        )
        
        title = f"🚨 {'返工预算熔断' if fuse_type == 'budget' else '返工次数熔断'}: {workflow.title}"
        
        if fuse_type == "budget":
            message = f"返工预算已耗尽，需要您决策如何处理"
        else:
            message = f"返工次数已达上限({details.get('rework_count', 0)}次)，需要您决策"
        
        # 通知Partner
        partner = self._get_partner()
        if partner:
            self._create_and_send_notification(
                recipient_id=partner.id,
                notification_type=notification_type,
                title=title,
                message=message,
                workflow_id=workflow.id,
                priority=NotificationPriority.URGENT,
                data_snapshot={
                    "fuse_type": fuse_type,
                    "workflow_title": workflow.title,
                    "remaining_budget": workflow.rework_budget - workflow.used_rework_budget,
                    **details
                }
            )
        
        # 也通知当前步骤负责人
        current_step = self._get_current_step(workflow.id)
        if current_step and current_step.assignee_id:
            self._create_and_send_notification(
                recipient_id=current_step.assignee_id,
                notification_type=notification_type,
                title=title,
                message=message,
                workflow_id=workflow.id,
                step_id=current_step.id,
                priority=NotificationPriority.URGENT,
                data_snapshot={"fuse_type": fuse_type}
            )
    
    def notify_workflow_completed(self, workflow: WorkflowInstance):
        """通知工作流完成"""
        # 通知Partner
        partner = self._get_partner()
        if partner:
            self._create_and_send_notification(
                recipient_id=partner.id,
                notification_type=NotificationType.WORKFLOW_COMPLETED,
                title=f"✅ 任务完成: {workflow.title}",
                message=f"工作流已完成，总返工{workflow.total_rework_count}次，预算使用{(workflow.used_base_budget + workflow.used_rework_budget) / workflow.total_budget * 100:.1f}%",
                workflow_id=workflow.id,
                priority=NotificationPriority.NORMAL,
                data_snapshot={
                    "workflow_title": workflow.title,
                    "total_rework": workflow.total_rework_count,
                    "budget_used": workflow.used_base_budget + workflow.used_rework_budget,
                    "total_budget": workflow.total_budget,
                    "completion_time": (workflow.completed_at - workflow.started_at).total_seconds() // 60 if workflow.completed_at and workflow.started_at else 0,
                }
            )
    
    # ========== 内部方法 ==========
    
    def _create_and_send_notification(
        self,
        recipient_id: str,
        notification_type: str,
        title: str,
        message: str,
        workflow_id: str = None,
        step_id: str = None,
        priority: str = NotificationPriority.NORMAL,
        channels: List[str] = None,
        data_snapshot: Dict = None
    ) -> WorkflowNotification:
        """创建并发送通知"""
        # 获取用户的订阅偏好
        subscription = self._get_subscription(recipient_id)
        
        # 确定通知渠道
        if channels is None:
            channels = self._get_channels_for_type(notification_type, subscription)
        
        # 检查免打扰
        if self._is_quiet_hours(subscription):
            # 仅保留高优先级通知
            if priority not in [NotificationPriority.HIGH.value, NotificationPriority.URGENT.value]:
                logger.info("notification_skipped_quiet_hours", recipient=recipient_id, type=notification_type)
                return None
        
        # 创建通知记录
        notification = WorkflowNotification(
            recipient_id=recipient_id,
            type=notification_type,
            title=title,
            message=message,
            workflow_id=workflow_id,
            step_id=step_id,
            priority=priority,
            channels=channels,
            data_snapshot=data_snapshot or {},
        )
        self.db.add(notification)
        self.db.flush()
        
        # WebSocket实时推送
        if NotificationChannel.WEBSOCKET.value in channels:
            self._send_websocket_notification(notification)
        
        self.db.commit()
        
        logger.info("notification_sent", 
                   recipient=recipient_id, 
                   type=notification_type,
                   priority=priority)
        
        return notification
    
    def _send_websocket_notification(self, notification: WorkflowNotification):
        """通过WebSocket发送通知"""
        if not self._websocket_manager:
            logger.warning("websocket_manager_not_set")
            return
        
        try:
            message = {
                "type": "notification",
                "data": {
                    "id": notification.id,
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "priority": notification.priority,
                    "workflow_id": notification.workflow_id,
                    "step_id": notification.step_id,
                    "data": notification.data_snapshot,
                    "created_at": notification.created_at.isoformat(),
                }
            }
            
            # 发送给特定用户
            self._websocket_manager.send_to_user(
                user_id=notification.recipient_id,
                message=message
            )
            
            notification.websocket_delivered = "true"
            notification.delivered_at = datetime.utcnow()
            
        except Exception as e:
            logger.error("websocket_send_failed", error=str(e))
    
    def _get_subscription(self, agent_id: str) -> Optional[NotificationSubscription]:
        """获取用户的订阅配置"""
        return self.db.query(NotificationSubscription).filter(
            NotificationSubscription.agent_id == agent_id
        ).first()
    
    def _get_channels_for_type(
        self, 
        notification_type: str, 
        subscription: NotificationSubscription
    ) -> List[str]:
        """根据订阅配置获取通知渠道"""
        if subscription and subscription.channel_preferences:
            channels = subscription.channel_preferences.get(notification_type)
            if channels:
                return channels
        
        # 默认渠道
        default_channels = {
            NotificationType.REWORK_TRIGGERED.value: [NotificationChannel.WEBSOCKET.value, NotificationChannel.IN_APP.value],
            NotificationType.BUDGET_FUSED.value: [NotificationChannel.WEBSOCKET.value, NotificationChannel.IN_APP.value],
            NotificationType.REWORK_FUSED.value: [NotificationChannel.WEBSOCKET.value, NotificationChannel.IN_APP.value],
            NotificationType.REWORK_LIMIT_WARNING.value: [NotificationChannel.WEBSOCKET.value, NotificationChannel.IN_APP.value],
        }
        
        return default_channels.get(notification_type, [NotificationChannel.WEBSOCKET.value])
    
    def _is_quiet_hours(self, subscription: NotificationSubscription) -> bool:
        """检查是否在免打扰时间"""
        if not subscription or not subscription.quiet_hours.get("enabled"):
            return False
        
        from datetime import datetime
        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")
        
        start = subscription.quiet_hours.get("start", "22:00")
        end = subscription.quiet_hours.get("end", "08:00")
        
        if start < end:
            return start <= current_time <= end
        else:
            return current_time >= start or current_time <= end
    
    def _get_partner(self) -> Optional[Agent]:
        """获取Partner"""
        from src.models.agent import PositionLevel
        return self.db.query(Agent).filter(
            Agent.position_level == PositionLevel.PARTNER.value
        ).first()
    
    def _get_current_step(self, workflow_id: str) -> Optional[WorkflowStep]:
        """获取当前步骤"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow or workflow.current_step_index < 0:
            return None
        
        return self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.sequence == workflow.current_step_index
        ).first()
    
    # ========== 查询方法 ==========
    
    def get_unread_notifications(
        self, 
        agent_id: str, 
        limit: int = 50
    ) -> List[WorkflowNotification]:
        """获取未读通知"""
        return self.db.query(WorkflowNotification).filter(
            WorkflowNotification.recipient_id == agent_id,
            WorkflowNotification.is_read == "false"
        ).order_by(
            WorkflowNotification.created_at.desc()
        ).limit(limit).all()
    
    def mark_as_read(self, notification_id: int, agent_id: str) -> bool:
        """标记通知为已读"""
        notification = self.db.query(WorkflowNotification).filter(
            WorkflowNotification.id == notification_id,
            WorkflowNotification.recipient_id == agent_id
        ).first()
        
        if not notification:
            return False
        
        notification.is_read = "true"
        notification.read_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def mark_all_as_read(self, agent_id: str) -> int:
        """标记所有通知为已读"""
        notifications = self.db.query(WorkflowNotification).filter(
            WorkflowNotification.recipient_id == agent_id,
            WorkflowNotification.is_read == "false"
        ).all()
        
        for n in notifications:
            n.is_read = "true"
            n.read_at = datetime.utcnow()
        
        self.db.commit()
        return len(notifications)
