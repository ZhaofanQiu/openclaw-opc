"""
Shared Memory models for v0.4.0

公司级共享记忆，所有Agent可以读写
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class MemoryScope(str, PyEnum):
    """Memory scope/visibility."""
    COMPANY = "company"      # 全公司可见
    TEAM = "team"            # 团队可见（预留）
    PRIVATE = "private"      # 个人私有


class MemoryCategory(str, PyEnum):
    """Memory category."""
    GENERAL = "general"      # 通用知识
    PROJECT = "project"      # 项目信息
    DECISION = "decision"    # 决策记录
    LESSON = "lesson"        # 经验教训
    PREFERENCE = "preference"  # 偏好设置
    CONTACT = "contact"      # 联系人信息
    TODO = "todo"            # 待办事项
    NOTE = "note"            # 笔记


class SharedMemory(Base):
    """
    Shared company memory for v0.4.0
    
    公司级共享记忆，所有Agent可以读写
    """
    
    __tablename__ = "shared_memories"
    
    id = Column(String, primary_key=True)
    
    # 创建者
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # 内容
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    # 分类
    category = Column(String, default=MemoryCategory.GENERAL.value)
    scope = Column(String, default=MemoryScope.COMPANY.value)
    
    # 标签（逗号分隔）
    tags = Column(String, default="")
    
    # 重要性 (1-5)
    importance = Column(Integer, default=3)
    
    # 访问统计
    access_count = Column(Integer, default=0)
    
    # 过期时间（可选）
    expires_at = Column(DateTime, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    agent = relationship("Agent", back_populates="shared_memories")
    
    def __repr__(self):
        return f"<SharedMemory(id={self.id}, title={self.title}, category={self.category})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def tag_list(self) -> list:
        """Get tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]


class MemoryAccessLog(Base):
    """
    Memory access log for tracking usage
    
    记录记忆的访问历史
    """
    
    __tablename__ = "memory_access_logs"
    
    id = Column(Integer, primary_key=True)
    
    memory_id = Column(String, ForeignKey("shared_memories.id"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    
    # 访问类型
    access_type = Column(String, default="read")  # read, write, search
    
    # 访问时间
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    memory = relationship("SharedMemory", back_populates="access_logs")
    agent = relationship("Agent", back_populates="memory_access_logs")


# 更新关系
SharedMemory.access_logs = relationship("MemoryAccessLog", back_populates="memory", cascade="all, delete-orphan")
