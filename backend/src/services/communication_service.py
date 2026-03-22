"""
Agent Communication Service

Enables communication between agents via Partner coordination.
Uses OpenClaw sessions_send for message delivery.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from src.models import AgentMessage, MessagePriority, MessageStatus


class CommunicationService:
    """Service for managing agent-to-agent communication."""
    
    # Maximum retry attempts
    MAX_RETRIES = 3
    
    def __init__(self, db: Session):
        self.db = db
    
    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        subject: Optional[str] = None,
        priority: str = MessagePriority.NORMAL.value,
        related_task_id: Optional[str] = None,
        related_type: Optional[str] = None,
    ) -> AgentMessage:
        """
        Create and queue a message between agents.
        
        Args:
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID
            content: Message content
            subject: Optional subject line
            priority: Message priority
            related_task_id: Optional related task
            related_type: Type of message
        
        Returns:
            Created message record
        """
        message = AgentMessage(
            id=str(uuid.uuid4())[:8],
            sender_id=sender_id,
            recipient_id=recipient_id,
            subject=subject or "",
            content=content,
            priority=priority,
            status=MessageStatus.PENDING.value,
            related_task_id=related_task_id,
            related_type=related_type,
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        return message
    
    def deliver_message(
        self,
        message_id: str,
        use_sessions_send: bool = True,
    ) -> Dict[str, Any]:
        """
        Deliver a pending message to the recipient.
        
        Args:
            message_id: Message ID to deliver
            use_sessions_send: Whether to use OpenClaw sessions_send
        
        Returns:
            Delivery result
        """
        from src.models import Agent
        
        message = self.db.query(AgentMessage).filter(
            AgentMessage.id == message_id
        ).first()
        
        if not message:
            return {"success": False, "error": "Message not found"}
        
        if message.status != MessageStatus.PENDING.value:
            return {"success": False, "error": f"Message already {message.status}"}
        
        # Get sender and recipient info
        sender = self.db.query(Agent).filter(Agent.id == message.sender_id).first()
        recipient = self.db.query(Agent).filter(Agent.id == message.recipient_id).first()
        
        if not recipient:
            message.status = MessageStatus.FAILED.value
            message.error_message = "Recipient not found"
            self.db.commit()
            return {"success": False, "error": "Recipient not found"}
        
        # Build message content for delivery
        delivery_content = self._format_message(message, sender, recipient)
        
        if use_sessions_send and recipient.agent_id:
            # Try to deliver via OpenClaw sessions_send
            try:
                result = self._send_via_sessions(
                    recipient_agent_id=recipient.agent_id,
                    content=delivery_content,
                )
                
                if result.get("success"):
                    message.status = MessageStatus.SENT.value
                    message.sent_at = datetime.utcnow()
                    self.db.commit()
                    return {
                        "success": True,
                        "message_id": message.id,
                        "status": "sent",
                        "method": "sessions_send",
                    }
                else:
                    # Mark for retry
                    message.retry_count += 1
                    if message.retry_count >= self.MAX_RETRIES:
                        message.status = MessageStatus.FAILED.value
                        message.error_message = result.get("error", "Max retries exceeded")
                    self.db.commit()
                    return {
                        "success": False,
                        "error": result.get("error", "Delivery failed"),
                        "retry_count": message.retry_count,
                    }
            except Exception as e:
                message.retry_count += 1
                if message.retry_count >= self.MAX_RETRIES:
                    message.status = MessageStatus.FAILED.value
                    message.error_message = str(e)
                self.db.commit()
                return {
                    "success": False,
                    "error": str(e),
                    "retry_count": message.retry_count,
                }
        else:
            # No agent_id or sessions_send disabled, mark as delivered internally
            message.status = MessageStatus.DELIVERED.value
            message.delivered_at = datetime.utcnow()
            self.db.commit()
            return {
                "success": True,
                "message_id": message.id,
                "status": "delivered",
                "method": "internal",
            }
    
    def _format_message(
        self,
        message: AgentMessage,
        sender: Optional["Agent"],
        recipient: Optional["Agent"],
    ) -> str:
        """Format message for delivery."""
        sender_name = sender.name if sender else "Unknown"
        
        lines = [
            f"📨 来自 {sender_name} 的消息",
            "",
        ]
        
        if message.subject:
            lines.append(f"📌 主题: {message.subject}")
        
        if message.related_type:
            lines.append(f"🏷️ 类型: {message.related_type}")
        
        lines.extend([
            "",
            message.content,
            "",
        ])
        
        # v0.4.0 - Add shared memory context
        if recipient and message.related_type == "task_assignment":
            try:
                from src.services.shared_memory_service import SharedMemoryService
                memory_service = SharedMemoryService(self.db)
                
                # Get relevant memories for this agent
                memories = memory_service.get_memories_for_agent_context(
                    agent_id=recipient.id,
                    task_type=message.subject or "",
                    limit=3,
                )
                
                if memories:
                    lines.append("📚 相关记忆:")
                    lines.append("-" * 30)
                    for m in memories:
                        lines.append(f"[{m['category']}] {m['title']}:")
                        # Truncate content if too long
                        content = m['content'][:200] + "..." if len(m['content']) > 200 else m['content']
                        lines.append(f"  {content}")
                        lines.append("")
            except Exception as e:
                # Don't fail message formatting if memory lookup fails
                pass
        
        lines.extend([
            "---",
            f"发送时间: {message.created_at.strftime('%Y-%m-%d %H:%M')}",
        ])
        
        return "\n".join(lines)
    
    def _send_via_sessions(self, recipient_agent_id: str, content: str) -> Dict[str, Any]:
        """
        Send message via OpenClaw sessions_send.
        
        Note: This is a placeholder. In production, this would:
        1. Call OpenClaw Gateway API
        2. Or use opc-bridge skill to send
        
        Args:
            recipient_agent_id: Target OpenClaw agent ID
            content: Message content
        
        Returns:
            Send result
        """
        # In a real implementation, this would:
        # return opc_bridge_send_message(recipient_agent_id, content)
        
        # For now, simulate success
        return {
            "success": True,
            "method": "sessions_send",
            "recipient": recipient_agent_id,
        }
    
    def get_messages(
        self,
        agent_id: Optional[str] = None,
        recipient_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentMessage]:
        """
        Get messages with optional filters.
        
        Args:
            agent_id: Filter messages involving this agent (as sender or recipient)
            recipient_id: Filter by recipient
            sender_id: Filter by sender
            status: Filter by status
            limit: Maximum results
        
        Returns:
            List of messages
        """
        query = self.db.query(AgentMessage)
        
        if agent_id:
            query = query.filter(
                (AgentMessage.sender_id == agent_id) |
                (AgentMessage.recipient_id == agent_id)
            )
        
        if recipient_id:
            query = query.filter(AgentMessage.recipient_id == recipient_id)
        
        if sender_id:
            query = query.filter(AgentMessage.sender_id == sender_id)
        
        if status:
            query = query.filter(AgentMessage.status == status)
        
        return query.order_by(AgentMessage.created_at.desc()).limit(limit).all()
    
    def get_conversation(
        self,
        agent1_id: str,
        agent2_id: str,
        limit: int = 50,
    ) -> List[AgentMessage]:
        """
        Get conversation between two agents.
        
        Args:
            agent1_id: First agent ID
            agent2_id: Second agent ID
            limit: Maximum results
        
        Returns:
            List of messages between the two agents
        """
        return self.db.query(AgentMessage).filter(
            ((AgentMessage.sender_id == agent1_id) & (AgentMessage.recipient_id == agent2_id)) |
            ((AgentMessage.sender_id == agent2_id) & (AgentMessage.recipient_id == agent1_id))
        ).order_by(AgentMessage.created_at.desc()).limit(limit).all()
    
    def mark_delivered(self, message_id: str) -> Optional[AgentMessage]:
        """
        Mark a message as delivered.
        
        Called when recipient confirms receipt.
        
        Args:
            message_id: Message ID
        
        Returns:
            Updated message or None
        """
        message = self.db.query(AgentMessage).filter(
            AgentMessage.id == message_id
        ).first()
        
        if not message:
            return None
        
        message.status = MessageStatus.DELIVERED.value
        message.delivered_at = datetime.utcnow()
        self.db.commit()
        
        return message
    
    def get_pending_messages(self, limit: int = 100) -> List[AgentMessage]:
        """Get all pending messages for batch delivery."""
        return self.db.query(AgentMessage).filter(
            AgentMessage.status == MessageStatus.PENDING.value,
            AgentMessage.retry_count < self.MAX_RETRIES
        ).limit(limit).all()
    
    def broadcast_message(
        self,
        sender_id: str,
        recipient_ids: List[str],
        content: str,
        subject: Optional[str] = None,
        priority: str = MessagePriority.NORMAL.value,
    ) -> List[AgentMessage]:
        """
        Send a message to multiple recipients.
        
        Args:
            sender_id: Sender agent ID
            recipient_ids: List of recipient agent IDs
            content: Message content
            subject: Optional subject
            priority: Message priority
        
        Returns:
            List of created messages
        """
        messages = []
        for recipient_id in recipient_ids:
            message = self.send_message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                content=content,
                subject=subject,
                priority=priority,
            )
            messages.append(message)
        
        return messages
    
    def notify_task_assignment(
        self,
        agent_id: str,
        task_id: str,
        task_title: str,
        task_description: str,
    ) -> AgentMessage:
        """
        Send task assignment notification to an agent.
        
        Args:
            agent_id: Agent to notify
            task_id: Task ID
            task_title: Task title
            task_description: Task description
        
        Returns:
            Created message
        """
        from src.models import Agent
        
        # Get Partner as sender
        partner = self.db.query(Agent).filter(
            Agent.position_level == "PARTNER"
        ).first()
        
        sender_id = partner.id if partner else "system"
        
        content = f"""你有新任务待处理：

📋 任务: {task_title}
📝 描述: {task_description}

请尽快开始处理，完成后记得提交工作报告。"""
        
        return self.send_message(
            sender_id=sender_id,
            recipient_id=agent_id,
            content=content,
            subject=f"新任务: {task_title}",
            priority=MessagePriority.HIGH.value,
            related_task_id=task_id,
            related_type="task_assignment",
        )
    
    def get_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get communication statistics.
        
        Args:
            agent_id: Optional agent ID to filter
        
        Returns:
            Statistics dict
        """
        query = self.db.query(AgentMessage)
        
        if agent_id:
            query = query.filter(
                (AgentMessage.sender_id == agent_id) |
                (AgentMessage.recipient_id == agent_id)
            )
        
        total = query.count()
        pending = query.filter(AgentMessage.status == MessageStatus.PENDING.value).count()
        sent = query.filter(AgentMessage.status == MessageStatus.SENT.value).count()
        delivered = query.filter(AgentMessage.status == MessageStatus.DELIVERED.value).count()
        failed = query.filter(AgentMessage.status == MessageStatus.FAILED.value).count()
        
        return {
            "total": total,
            "pending": pending,
            "sent": sent,
            "delivered": delivered,
            "failed": failed,
            "delivery_rate": (delivered / total * 100) if total > 0 else 0,
        }
