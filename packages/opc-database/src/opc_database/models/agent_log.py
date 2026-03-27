"""
opc-database: Agent 交互日志模型

记录与 OpenClaw Agent 的所有原始文本交互

作者: OpenClaw OPC Team
创建日期: 2026-03-27
版本: 0.4.5
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Index

from .base import Base


class AgentLog(Base):
    """
    Agent 交互日志
    
    记录 OPC 与 OpenClaw Agent 之间的所有原始文本交互
    """
    __tablename__ = "agent_logs"
    
    # 主键
    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    
    # Agent 信息
    agent_id = Column(String(100), nullable=False, index=True)
    agent_name = Column(String(100), nullable=True)
    
    # 交互类型
    # - partner_chat: Partner 聊天
    # - task_assignment: 任务分配
    # - assist_employee: 辅助创建员工
    # - assist_task: 辅助创建任务
    # - assist_workflow: 辅助创建工作流
    # - assist_manual: 辅助更新手册
    interaction_type = Column(String(30), nullable=False, index=True)
    
    # 方向: outgoing(发送给Agent), incoming(接收自Agent)
    direction = Column(String(10), nullable=False)
    
    # 核心内容 - 原始文本（限制在合理范围内）
    content = Column(Text, nullable=False)  # 发送/接收的内容
    response = Column(Text, nullable=True)  # 如果是outgoing，这里存储Agent的回复
    
    # 关联信息
    task_id = Column(String(32), nullable=True, index=True)
    meta_info = Column(JSON, nullable=True, default=dict)  # tokens, duration_ms, success等 (注意：不能用metadata，这是SQLAlchemy保留字)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "interaction_type": self.interaction_type,
            "direction": self.direction,
            "content": self.content,
            "response": self.response,
            "task_id": self.task_id,
            "metadata": self.meta_info or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        if self.meta_info:
            return self.meta_info.get("success", True)
        return True
    
    @property
    def duration_ms(self) -> Optional[int]:
        """耗时（毫秒）"""
        if self.meta_info:
            return self.meta_info.get("duration_ms")
        return None
    
    @property
    def tokens_input(self) -> int:
        """输入token数"""
        if self.meta_info:
            return self.meta_info.get("tokens_input", 0)
        return 0
    
    @property
    def tokens_output(self) -> int:
        """输出token数"""
        if self.meta_info:
            return self.meta_info.get("tokens_output", 0)
        return 0
    
    @property
    def total_tokens(self) -> int:
        """总token数"""
        return self.tokens_input + self.tokens_output
