"""
System configuration models.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from src.database import Base


class SystemConfig(Base):
    """System-wide configuration."""
    
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True)
    
    # Task timeout settings
    task_timeout_minutes = Column(Integer, default=30)  # 任务超时时间（分钟）
    
    # Budget settings
    token_to_oc_rate = Column(Integer, default=100)  # 100 tokens = 1 OC币
    warning_threshold = Column(Float, default=80.0)  # 预算警告阈值（%）
    fuse_threshold = Column(Float, default=100.0)  # 预算熔断阈值（%）
    
    # Auto-assignment settings
    auto_assign_enabled = Column(String, default="true")  # 是否启用自动分配
    default_strategy = Column(String, default="budget")  # 默认分配策略
    
    # Partner heartbeat
    heartbeat_interval_seconds = Column(Integer, default=30)  # 心跳间隔
    heartbeat_timeout_seconds = Column(Integer, default=60)  # 心跳超时
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, default="system")  # 最后更新者
    
    @classmethod
    def get_default_config(cls):
        """Get default configuration values."""
        return {
            "task_timeout_minutes": 30,
            "token_to_oc_rate": 100,
            "warning_threshold": 80.0,
            "fuse_threshold": 100.0,
            "auto_assign_enabled": True,
            "default_strategy": "budget",
            "heartbeat_interval_seconds": 30,
            "heartbeat_timeout_seconds": 60,
        }