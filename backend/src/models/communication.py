"""
Communication Models

Inter-agent communication messages.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Text, DateTime, Integer

from database import Base


class MessageStatus(str, PyEnum):
    """Message delivery status."""
    PENDING = "pending"      # Waiting to be sent
    SENT = "sent"            # Delivered to target agent
    DELIVERED = "delivered"  # Confirmed received
    FAILED = "failed"        # Delivery failed


class MessagePriority(str, PyEnum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentMessage(Base):
    """Inter-agent communication message."""
    __tablename__ = "agent_messages"
    
    id = Column(String, primary_key=True)
    
    # Sender and recipient
    sender_id = Column(String, nullable=False, index=True)  # Agent ID
    recipient_id = Column(String, nullable=False, index=True)  # Agent ID
    
    # Message content
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    
    # Metadata
    priority = Column(String, default=MessagePriority.NORMAL.value)
    status = Column(String, default=MessageStatus.PENDING.value)
    
    # Related entities (optional)
    related_task_id = Column(String, nullable=True)
    related_type = Column(String, nullable=True)  # task_assignment, notification, etc.
    
    # Delivery tracking
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
