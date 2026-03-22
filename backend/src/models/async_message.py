"""
异步消息模型

支持长时间运行的Agent通信，30分钟超时容忍
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class AsyncMessageStatus(str, PyEnum):
    """异步消息状态"""
    PENDING = "pending"       # 待发送
    SENDING = "sending"       # 发送中
    SENT = "sent"            # 已发送
    DELIVERED = "delivered"  # 已送达（Agent已接收）
    RESPONDED = "responded"  # 已回复
    FAILED = "failed"        # 发送失败
    TIMEOUT = "timeout"      # 超时（30分钟）


class AsyncMessageType(str, PyEnum):
    """消息类型"""
    CHAT = "chat"           # 普通聊天
    TASK = "task"           # 任务分配
    SYSTEM = "system"       # 系统消息


class AsyncMessage(Base):
    """异步消息模型
    
    支持长时间运行的Agent通信，用户可关闭UI稍后查看回复
    """
    __tablename__ = "async_messages"
    
    id = Column(String, primary_key=True)
    
    # 消息类型
    message_type = Column(String, default=AsyncMessageType.CHAT.value)
    
    # 发送者（用户或Agent）
    sender_id = Column(String, nullable=False)  # 用户ID或Agent ID
    sender_type = Column(String, default="user")  # user/agent/system
    sender_name = Column(String, nullable=True)
    
    # 接收者（必须是Agent）
    recipient_id = Column(String, nullable=False)  # Agent内部ID
    recipient_agent_id = Column(String, nullable=False)  # OpenClaw Agent ID
    recipient_name = Column(String, nullable=True)
    
    # 消息内容
    content = Column(Text, nullable=False)
    subject = Column(String, default="")  # 主题（可选）
    
    # OpenClaw集成
    openclaw_session_id = Column(String, nullable=True)  # 会话ID
    
    # 状态跟踪
    status = Column(String, default=AsyncMessageStatus.PENDING.value)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    
    # 超时设置（默认30分钟）
    timeout_seconds = Column(Integer, default=1800)
    
    # 回复内容
    response_content = Column(Text, nullable=True)
    response_tokens_input = Column(Integer, default=0)
    response_tokens_output = Column(Integer, default=0)
    
    # 错误信息
    error_message = Column(String, nullable=True)
    
    # 关联任务（如果是任务消息）
    related_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    
    # 通知状态
    notification_sent = Column(String, default="false")  # 是否已通知用户
    notification_sent_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<AsyncMessage(id={self.id}, type={self.message_type}, status={self.status})>"
    
    @property
    def elapsed_seconds(self) -> float:
        """计算已过去的时间"""
        now = datetime.utcnow()
        return (now - self.created_at).total_seconds()
    
    @property
    def is_expired(self) -> bool:
        """检查是否已超时"""
        return self.elapsed_seconds > self.timeout_seconds
    
    @property
    def response_summary(self) -> str:
        """回复摘要（前100字符）"""
        if not self.response_content:
            return ""
        return self.response_content[:100] + "..." if len(self.response_content) > 100 else self.response_content
