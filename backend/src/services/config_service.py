"""
System configuration service.
"""

from typing import Dict, Any

from sqlalchemy.orm import Session

from models import SystemConfig


class ConfigService:
    """System configuration service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_config(self) -> SystemConfig:
        """Get current system configuration."""
        config = self.db.query(SystemConfig).first()
        if not config:
            # Create default config
            config = SystemConfig()
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get config as dictionary."""
        config = self.get_config()
        return {
            "task_timeout_minutes": config.task_timeout_minutes,
            "token_to_oc_rate": config.token_to_oc_rate,
            "warning_threshold": config.warning_threshold,
            "fuse_threshold": config.fuse_threshold,
            "auto_assign_enabled": config.auto_assign_enabled == "true",
            "default_strategy": config.default_strategy,
            "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
            "heartbeat_timeout_seconds": config.heartbeat_timeout_seconds,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "updated_by": config.updated_by,
        }
    
    def update_config(self, updates: Dict[str, Any], updated_by: str = "system") -> SystemConfig:
        """Update system configuration."""
        config = self.get_config()
        
        # Map of allowed fields
        field_mapping = {
            "task_timeout_minutes": ("task_timeout_minutes", int),
            "token_to_oc_rate": ("token_to_oc_rate", int),
            "warning_threshold": ("warning_threshold", float),
            "fuse_threshold": ("fuse_threshold", float),
            "auto_assign_enabled": ("auto_assign_enabled", lambda x: "true" if x else "false"),
            "default_strategy": ("default_strategy", str),
            "heartbeat_interval_seconds": ("heartbeat_interval_seconds", int),
            "heartbeat_timeout_seconds": ("heartbeat_timeout_seconds", int),
        }
        
        for key, value in updates.items():
            if key in field_mapping:
                field_name, converter = field_mapping[key]
                setattr(config, field_name, converter(value))
        
        config.updated_by = updated_by
        self.db.commit()
        self.db.refresh(config)
        return config
    
    def get_task_timeout_minutes(self) -> int:
        """Get task timeout in minutes."""
        config = self.get_config()
        return config.task_timeout_minutes
    
    def get_token_to_oc_rate(self) -> int:
        """Get token to OC币 conversion rate."""
        config = self.get_config()
        return config.token_to_oc_rate
    
    def is_auto_assign_enabled(self) -> bool:
        """Check if auto-assignment is enabled."""
        config = self.get_config()
        return config.auto_assign_enabled == "true"
    
    def get_default_strategy(self) -> str:
        """Get default assignment strategy."""
        config = self.get_config()
        return config.default_strategy
    
    def get_heartbeat_timeout(self) -> int:
        """Get heartbeat timeout in seconds."""
        config = self.get_config()
        return config.heartbeat_timeout_seconds