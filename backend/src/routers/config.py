"""
Configuration API routes.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.config_service import ConfigService

router = APIRouter()


class ConfigUpdate(BaseModel):
    """Configuration update request."""
    task_timeout_minutes: int = Field(None, ge=1, le=480)  # 1 min to 8 hours
    token_to_oc_rate: int = Field(None, ge=1)
    warning_threshold: float = Field(None, ge=0, le=100)
    fuse_threshold: float = Field(None, ge=0, le=100)
    auto_assign_enabled: bool = None
    default_strategy: str = Field(None, regex="^(budget|workload|combined)$")
    heartbeat_interval_seconds: int = Field(None, ge=10, le=300)
    heartbeat_timeout_seconds: int = Field(None, ge=30, le=600)


@router.get("")
async def get_config(
    db: Session = Depends(get_db),
):
    """Get current system configuration."""
    service = ConfigService(db)
    return service.get_config_dict()


@router.patch("")
async def update_config(
    config_update: ConfigUpdate,
    db: Session = Depends(get_db),
):
    """
    Update system configuration.
    
    Only provided fields will be updated.
    """
    service = ConfigService(db)
    
    # Convert to dict, excluding None values
    updates = config_update.dict(exclude_unset=True)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    config = service.update_config(updates, updated_by="admin")
    
    return {
        "success": True,
        "message": "Configuration updated",
        "config": service.get_config_dict()
    }


@router.get("/defaults")
async def get_default_config():
    """Get default configuration values."""
    from src.models import SystemConfig
    return SystemConfig.get_default_config()


@router.post("/reset")
async def reset_config(
    db: Session = Depends(get_db),
):
    """Reset configuration to defaults."""
    service = ConfigService(db)
    
    defaults = SystemConfig.get_default_config()
    config = service.update_config(defaults, updated_by="admin")
    
    return {
        "success": True,
        "message": "Configuration reset to defaults",
        "config": service.get_config_dict()
    }