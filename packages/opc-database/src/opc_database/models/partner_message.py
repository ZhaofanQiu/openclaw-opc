"""
opc-database: Partner 消息模型

存储用户与 Partner 员工的对话历史

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.4
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, JSON, DateTime, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

if TYPE_CHECKING:
    pass


class PartnerMessage(Base):
    """
    Partner 聊天记录
    
    存储用户与 Partner 员工的对话历史，支持上下文理解
    
    Attributes:
        id: 消息唯一标识 (主键)
        partner_id: Partner 员工ID
        role: 消息角色 (user/partner/system)
        content: 消息内容
        has_action: 是否包含操作指令
        action_type: 操作类型
        action_params: 操作参数
        action_result: 操作执行结果
        context_snapshot: 对话时的公司状态快照
        created_at: 创建时间
    """
    
    __tablename__ = "partner_messages"
    
    # 主键
    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # Partner 关联
    partner_id: Mapped[str] = mapped_column(
        String, 
        nullable=False, 
        index=True,
        comment="Partner 员工ID"
    )
    
    # 消息内容
    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="消息角色: user/partner/system"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容"
    )
    
    # 操作指令信息
    has_action: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="是否包含操作指令"
    )
    action_type: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="操作类型: create_task/create_workflow/..."
    )
    action_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="操作参数"
    )
    action_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="操作执行结果"
    )
    
    # 上下文快照（用于理解对话背景）
    context_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="对话时的公司状态快照"
    )
    
    # 时间戳（覆盖基类的 created_at 以支持更多控制）
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # 索引
    __table_args__ = (
        Index('idx_partner_created', 'partner_id', 'created_at'),
        Index('idx_partner_role', 'partner_id', 'role'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            包含消息完整信息的字典
        """
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "role": self.role,
            "content": self.content,
            "has_action": self.has_action,
            "action_type": self.action_type,
            "action_params": self.action_params,
            "action_result": self.action_result,
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        action_info = f" [action:{self.action_type}]" if self.has_action else ""
        return f"<PartnerMessage(id={self.id}, role={self.role}{action_info})>"
