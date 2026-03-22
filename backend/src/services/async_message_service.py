"""
异步消息服务

支持长时间运行的Agent通信
- 30分钟超时容忍
- 后台处理，UI不阻塞
- 支持查询状态和接收回调
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import AsyncMessage, AsyncMessageStatus, AsyncMessageType, Agent
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AsyncMessageService:
    """异步消息服务"""
    
    # 默认超时时间：30分钟
    DEFAULT_TIMEOUT = 1800
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_message(
        self,
        sender_id: str,
        sender_type: str,
        sender_name: str,
        recipient_id: str,
        content: str,
        message_type: str = AsyncMessageType.CHAT.value,
        subject: str = "",
        related_task_id: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT,
    ) -> AsyncMessage:
        """
        创建异步消息
        
        Args:
            sender_id: 发送者ID（用户ID或Agent ID）
            sender_type: 发送者类型（user/agent/system）
            sender_name: 发送者名称
            recipient_id: 接收者Agent内部ID
            content: 消息内容
            message_type: 消息类型
            subject: 主题
            related_task_id: 关联任务ID
            timeout_seconds: 超时时间（默认30分钟）
        
        Returns:
            创建的消息记录
        """
        # 获取接收者的OpenClaw Agent ID
        recipient = self.db.query(Agent).filter(Agent.id == recipient_id).first()
        if not recipient:
            raise ValueError(f"Recipient agent not found: {recipient_id}")
        
        if not recipient.agent_id:
            raise ValueError(f"Recipient agent not bound to OpenClaw: {recipient_id}")
        
        message = AsyncMessage(
            id=str(uuid.uuid4())[:8],
            message_type=message_type,
            sender_id=sender_id,
            sender_type=sender_type,
            sender_name=sender_name,
            recipient_id=recipient_id,
            recipient_agent_id=recipient.agent_id,
            recipient_name=recipient.name,
            content=content,
            subject=subject,
            related_task_id=related_task_id,
            timeout_seconds=timeout_seconds,
            status=AsyncMessageStatus.PENDING.value,
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        logger.info(f"Created async message: {message.id} from {sender_name} to {recipient.name}")
        
        return message
    
    def get_message(self, message_id: str) -> Optional[AsyncMessage]:
        """获取消息详情"""
        return self.db.query(AsyncMessage).filter(AsyncMessage.id == message_id).first()
    
    def get_pending_messages(self, recipient_id: Optional[str] = None) -> List[AsyncMessage]:
        """
        获取待处理的消息
        
        Args:
            recipient_id: 可选，筛选特定接收者
        
        Returns:
            待处理消息列表
        """
        query = self.db.query(AsyncMessage).filter(
            AsyncMessage.status.in_([
                AsyncMessageStatus.PENDING.value,
                AsyncMessageStatus.SENDING.value,
                AsyncMessageStatus.SENT.value,
            ])
        )
        
        if recipient_id:
            query = query.filter(AsyncMessage.recipient_id == recipient_id)
        
        return query.order_by(AsyncMessage.created_at.desc()).all()
    
    def get_messages_for_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[AsyncMessage]:
        """
        获取用户的消息历史
        
        Args:
            user_id: 用户ID
            status: 可选，按状态筛选
            limit: 返回数量限制
        
        Returns:
            消息列表
        """
        query = self.db.query(AsyncMessage).filter(
            AsyncMessage.sender_id == user_id
        )
        
        if status:
            query = query.filter(AsyncMessage.status == status)
        
        return query.order_by(AsyncMessage.created_at.desc()).limit(limit).all()
    
    def update_status(
        self,
        message_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> Optional[AsyncMessage]:
        """
        更新消息状态
        
        Args:
            message_id: 消息ID
            status: 新状态
            error_message: 错误信息（失败时）
        
        Returns:
            更新后的消息
        """
        message = self.get_message(message_id)
        if not message:
            return None
        
        message.status = status
        
        if status == AsyncMessageStatus.SENT.value:
            message.sent_at = datetime.utcnow()
        elif status == AsyncMessageStatus.DELIVERED.value:
            message.delivered_at = datetime.utcnow()
        elif status == AsyncMessageStatus.RESPONDED.value:
            message.responded_at = datetime.utcnow()
        elif status == AsyncMessageStatus.FAILED.value:
            message.failed_at = datetime.utcnow()
            message.error_message = error_message
        elif status == AsyncMessageStatus.TIMEOUT.value:
            message.failed_at = datetime.utcnow()
            message.error_message = "Timeout after 30 minutes"
        
        self.db.commit()
        
        logger.info(f"Updated message {message_id} status to {status}")
        
        return message
    
    def save_response(
        self,
        message_id: str,
        response_content: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> Optional[AsyncMessage]:
        """
        保存Agent回复
        
        Args:
            message_id: 消息ID
            response_content: 回复内容
            tokens_input: 输入token数
            tokens_output: 输出token数
        
        Returns:
            更新后的消息
        """
        message = self.get_message(message_id)
        if not message:
            return None
        
        message.response_content = response_content
        message.response_tokens_input = tokens_input
        message.response_tokens_output = tokens_output
        message.status = AsyncMessageStatus.RESPONDED.value
        message.responded_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Saved response for message {message_id}")
        
        return message
    
    def mark_notified(self, message_id: str) -> bool:
        """标记已通知用户"""
        message = self.get_message(message_id)
        if not message:
            return False
        
        message.notification_sent = "true"
        message.notification_sent_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def check_expired_messages(self) -> List[AsyncMessage]:
        """
        检查并返回已超时的消息
        
        Returns:
            超时消息列表
        """
        pending_messages = self.get_pending_messages()
        expired = []
        
        for msg in pending_messages:
            if msg.is_expired:
                self.update_status(msg.id, AsyncMessageStatus.TIMEOUT.value)
                expired.append(msg)
        
        if expired:
            logger.info(f"Marked {len(expired)} messages as timeout")
        
        return expired
    
    def delete_message(self, message_id: str) -> bool:
        """删除消息"""
        message = self.get_message(message_id)
        if not message:
            return False
        
        self.db.delete(message)
        self.db.commit()
        
        logger.info(f"Deleted message {message_id}")
        
        return True
    
    def to_dict(self, message: AsyncMessage) -> Dict:
        """将消息转换为字典"""
        return {
            "id": message.id,
            "message_type": message.message_type,
            "sender_id": message.sender_id,
            "sender_type": message.sender_type,
            "sender_name": message.sender_name,
            "recipient_id": message.recipient_id,
            "recipient_name": message.recipient_name,
            "content": message.content,
            "subject": message.subject,
            "status": message.status,
            "created_at": message.created_at.isoformat() if message.created_at else None,
            "sent_at": message.sent_at.isoformat() if message.sent_at else None,
            "delivered_at": message.delivered_at.isoformat() if message.delivered_at else None,
            "responded_at": message.responded_at.isoformat() if message.responded_at else None,
            "elapsed_seconds": message.elapsed_seconds,
            "timeout_seconds": message.timeout_seconds,
            "response_content": message.response_content,
            "response_summary": message.response_summary,
            "response_tokens_input": message.response_tokens_input,
            "response_tokens_output": message.response_tokens_output,
            "error_message": message.error_message,
            "related_task_id": message.related_task_id,
            "notification_sent": message.notification_sent,
        }
