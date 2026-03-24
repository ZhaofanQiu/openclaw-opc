"""
opc-database: 基础模型模块

提供所有模型的基类和通用功能

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    
    # 通用字段：创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    
    # 通用字段：更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将模型转换为字典
        
        子类应重写此方法以包含特定字段
        
        Returns:
            包含模型数据的字典
        """
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'N/A')})>"
