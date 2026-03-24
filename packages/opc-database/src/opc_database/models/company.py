"""
opc-database: 公司模型

定义公司配置和预算相关的数据模型

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0
"""

from typing import Any, Dict, Optional

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CompanyConfig(Base):
    """
    公司配置模型
    
    存储全局配置项
    """
    
    __tablename__ = "company_config"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
        })
        return base


class CompanyBudget(Base):
    """
    公司预算模型
    
    记录公司整体预算使用情况
    """
    
    __tablename__ = "company_budget"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    
    # 总预算
    total_budget: Mapped[float] = mapped_column(Float, default=10000.0)
    used_budget: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 月度统计
    month: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM
    
    # 熔断设置
    fuse_enabled: Mapped[bool] = mapped_column(default=True)
    fuse_threshold: Mapped[float] = mapped_column(Float, default=0.9)  # 90%
    
    @property
    def remaining_budget(self) -> float:
        """剩余预算"""
        return self.total_budget - self.used_budget
    
    @property
    def usage_percentage(self) -> float:
        """使用百分比"""
        if self.total_budget <= 0:
            return 0.0
        return (self.used_budget / self.total_budget) * 100
    
    def is_fuse_triggered(self) -> bool:
        """检查是否触发熔断"""
        if not self.fuse_enabled:
            return False
        return self.usage_percentage >= (self.fuse_threshold * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "id": self.id,
            "total_budget": self.total_budget,
            "used_budget": self.used_budget,
            "remaining_budget": self.remaining_budget,
            "usage_percentage": self.usage_percentage,
            "month": self.month,
            "fuse_enabled": self.fuse_enabled,
            "fuse_threshold": self.fuse_threshold,
            "fuse_triggered": self.is_fuse_triggered(),
        })
        return base
