"""
Workflow Notification Service v0.5.6

实时通知系统：
- WebSocket推送工作流状态变化
- 通知订阅管理
- 多渠道通知（WebSocket/邮件/站内信）
- 通知历史查询
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship

from database import Base


class NotificationChannel(str, PyEnum):
    """通知渠道"""
    WEBSOCKET = "websocket"  # 实时推送
    IN_APP = "in_app"        # 站内信
    EMAIL = "email"          # 邮件（预留）


class NotificationPriority(str, PyEnum):
    """通知优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(str, PyEnum):
    """通知类型"""
    # 工作流相关
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    
    # 步骤相关
    STEP_ASSIGNED = "step_assigned"
    STEP_COMPLETED = "step_completed"
    
    # 返工相关
    REWORK_TRIGGERED = "rework_triggered"
    REWORK_LIMIT_WARNING = "rework_limit_warning"
    
    # 熔断相关
    BUDGET_FUSED = "budget_fused"
    REWORK_FUSED = "rework_fused"
    
    # 系统相关
    SYSTEM_NOTICE = "system_notice"


class WorkflowNotification(Base):
    """工作流通知"""
    
    __tablename__ = "workflow_notifications"
    
    id = Column(Integer, primary_key=True)
    
    # 接收者
    recipient_id = Column(String, ForeignKey("agents.id"), nullable=False)
    
    # 通知内容
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # 关联数据
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=True)
    step_id = Column(String, ForeignKey("workflow_steps.id"), nullable=True)
    
    # 优先级
    priority = Column(String, default=NotificationPriority.NORMAL.value)
    
    # 渠道
    channels = Column(JSON, default=list)  # ["websocket", "in_app"]
    
    # 状态
    is_read = Column(String, default="false")
    read_at = Column(DateTime, nullable=True)
    
    # WebSocket发送状态
    websocket_delivered = Column(String, default="false")
    delivered_at = Column(DateTime, nullable=True)
    
    # 数据快照
    data_snapshot = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    recipient = relationship("Agent")


class NotificationSubscription(Base):
    """通知订阅配置"""
    
    __tablename__ = "notification_subscriptions"
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=False, unique=True)
    
    # 订阅配置
    subscribed_types = Column(JSON, default=list)  # 订阅的通知类型
    
    # 渠道偏好
    channel_preferences = Column(JSON, default=dict)
    # {
    #   "workflow_started": ["websocket", "in_app"],
    #   "rework_triggered": ["websocket", "in_app", "email"],
    #   ...
    # }
    
    # 免打扰设置
    quiet_hours = Column(JSON, default=dict)
    # {
    #   "enabled": false,
    #   "start": "22:00",
    #   "end": "08:00",
    # }
    
    # 批量通知设置
    batch_notifications = Column(String, default="false")  # 是否批量发送
    batch_interval_minutes = Column(Integer, default=15)   # 批量间隔
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
