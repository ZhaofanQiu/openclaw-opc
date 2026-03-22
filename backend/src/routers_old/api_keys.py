"""
API Key management router for external access control.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import get_db
from services.api_key_service import APIKeyService
from utils.api_auth import require_admin_permission
from utils.rate_limit import RATE_LIMITS


router = APIRouter(prefix="/api/keys", tags=["API Keys"])
limiter = Limiter(key_func=get_remote_address)


# Schemas

class APIKeyCreate(BaseModel):
    """Create API key request."""
    name: str = Field(..., min_length=1, max_length=100, description="Key name/description")
    permissions: List[str] = Field(default=["read"], description="Permissions: read, write, admin")
    allowed_ips: Optional[List[str]] = Field(default=None, description="Allowed IPs (null = any)")
    allowed_origins: Optional[List[str]] = Field(default=None, description="Allowed CORS origins")
    rate_limit: Optional[int] = Field(default=None, ge=1, le=10000, description="Rate limit per minute")
    expires_days: Optional[int] = Field(default=None, ge=1, le=365, description="Expiration in days")


class APIKeyResponse(BaseModel):
    """API key response (never includes full key)."""
    id: str
    name: str
    key_prefix: str
    permissions: List[str]
    is_active: bool
    use_count: int
    last_used_at: Optional[str]
    expires_at: Optional[str]
    created_at: str


class APIKeyCreateResponse(BaseModel):
    """API key creation response (includes full key - shown only once!)."""
    id: str
    name: str
    key: str  # ⚠️ Full key - save this immediately!
    key_prefix: str
    permissions: List[str]
    expires_at: Optional[str]
    created_at: str
    message: str


class APIKeyStats(BaseModel):
    """API key statistics."""
    total_keys: int
    active_keys: int
    expired_keys: int
    keys_with_usage: int


# Routes

@router.post("", response_model=APIKeyCreateResponse)
@limiter.limit(RATE_LIMITS["create"])
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new API key for external access.
    
    ⚠️ **IMPORTANT**: The full API key is returned only once!
    Save it immediately - it cannot be retrieved later.
    
    Permissions:
    - `read`: View data (agents, tasks, budget, reports)
    - `write`: Modify data (create tasks, update status)
    - `admin`: Full access including key management
    """
    service = APIKeyService(db)
    
    try:
        api_key, plain_key = service.create_key(
            name=key_data.name,
            permissions=key_data.permissions,
            allowed_ips=key_data.allowed_ips,
            allowed_origins=key_data.allowed_origins,
            rate_limit=key_data.rate_limit,
            expires_days=key_data.expires_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=plain_key,  # ⚠️ Only shown once!
        key_prefix=api_key.key_prefix,
        permissions=api_key.permissions.split(","),
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        created_at=api_key.created_at.isoformat(),
        message="⚠️ Save this API key immediately - it will not be shown again!",
    )


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    include_expired: bool = False,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """List all API keys (admin only)."""
    service = APIKeyService(db)
    keys = service.list_keys(include_expired=include_expired)
    
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            permissions=k.permissions.split(","),
            is_active=k.is_active,
            use_count=k.use_count,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.get("/stats", response_model=APIKeyStats)
async def get_api_key_stats(
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """Get API key usage statistics (admin only)."""
    service = APIKeyService(db)
    return APIKeyStats(**service.get_stats())


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """Get API key details (admin only)."""
    service = APIKeyService(db)
    key = service.get_key(key_id)
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return APIKeyResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        permissions=key.permissions.split(","),
        is_active=key.is_active,
        use_count=key.use_count,
        last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        expires_at=key.expires_at.isoformat() if key.expires_at else None,
        created_at=key.created_at.isoformat(),
    )


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """
    Revoke (deactivate) an API key.
    
    Revoked keys remain in the database for audit purposes
    but cannot be used for authentication.
    """
    service = APIKeyService(db)
    
    if not service.revoke_key(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {
        "success": True,
        "message": f"API key '{key_id}' has been revoked",
    }


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """
    Permanently delete an API key.
    
    ⚠️ This action cannot be undone!
    Consider revoking instead of deleting for audit purposes.
    """
    service = APIKeyService(db)
    
    if not service.delete_key(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {
        "success": True,
        "message": f"API key '{key_id}' has been permanently deleted",
    }


@router.post("/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """
    Rotate (regenerate) an API key.
    
    The old key immediately stops working.
    The new key is returned - save it immediately!
    """
    service = APIKeyService(db)
    
    new_key, success = service.rotate_key(key_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {
        "success": True,
        "new_key": new_key,
        "message": "⚠️ Save this new API key immediately - the old key no longer works!",
    }
