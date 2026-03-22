"""
Share Link Router

API endpoints for generating and managing share links.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.share_link_service import ShareLinkService
from src.utils.api_auth import require_admin_permission, get_current_permission
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/share", tags=["Share Links"])


# Schemas

class ShareLinkCreate(BaseModel):
    """Create share link request."""
    resource_type: str = Field(..., description="Resource type: dashboard, report, pixel_office")
    resource_id: Optional[str] = Field(None, description="Optional specific resource ID")
    permissions: str = Field(default="read", description="Permissions: read, write")
    expires_hours: int = Field(default=24, ge=1, le=168, description="Expiration time in hours (max 7 days)")
    max_uses: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of uses (null = unlimited)")
    password: Optional[str] = Field(None, min_length=4, max_length=50, description="Optional password protection")
    description: Optional[str] = Field(None, max_length=200, description="Description for this share link")


class ShareLinkResponse(BaseModel):
    """Share link creation response."""
    success: bool
    link_id: str
    share_url: str
    resource_type: str
    permissions: str
    expires_at: str
    max_uses: Optional[int]
    has_password: bool
    description: Optional[str]


class ShareLinkInfo(BaseModel):
    """Share link information."""
    id: str
    resource_type: str
    resource_id: Optional[str]
    permissions: str
    use_count: int
    max_uses: Optional[int]
    is_active: bool
    is_expired: bool
    expires_at: str
    created_at: str
    last_used_at: Optional[str]
    has_password: bool
    description: Optional[str]


class ValidateLinkResponse(BaseModel):
    """Link validation response."""
    valid: bool
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    permissions: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None


# Routes

@router.post("/generate", response_model=ShareLinkResponse)
@limiter.limit(RATE_LIMITS["create"])
async def generate_share_link(
    request: Request,
    link_data: ShareLinkCreate,
    db: Session = Depends(get_db),
    auth: dict = Depends(get_current_permission),
):
    """
    Generate a new share link for temporary access.
    
    Share links allow external access to OPC resources without requiring an API key.
    Links are signed with JWT and expire after a specified time.
    
    **Resource Types:**
    - `dashboard` - Main dashboard view
    - `report` - Reports page
    - `pixel_office` - Pixel office visualization
    - `task` - Specific task details (requires resource_id)
    - `agent` - Specific agent details (requires resource_id)
    
    **Permissions:**
    - `read` - View-only access
    - `write` - View and modify (requires higher privileges)
    """
    service = ShareLinkService(db)
    
    # Check permissions for write access
    if link_data.permissions == "write":
        if auth.get("permission") not in ["write", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Write permissions required to create write-enabled share links"
            )
    
    try:
        share_link, full_url = service.create_link(
            resource_type=link_data.resource_type,
            resource_id=link_data.resource_id,
            permissions=link_data.permissions,
            expires_hours=link_data.expires_hours,
            max_uses=link_data.max_uses,
            password=link_data.password,
            created_by=auth.get("employee_id"),
            description=link_data.description,
        )
        
        return ShareLinkResponse(
            success=True,
            link_id=share_link.id,
            share_url=full_url,
            resource_type=share_link.resource_type,
            permissions=share_link.permissions,
            expires_at=share_link.expires_at.isoformat(),
            max_uses=share_link.max_uses,
            has_password=share_link.password_hash is not None,
            description=share_link.description,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/validate")
async def validate_share_link(
    token: str = Query(..., description="Share link JWT token"),
    password: Optional[str] = Query(None, description="Password for protected links"),
    db: Session = Depends(get_db),
):
    """
    Validate a share link token.
    
    Returns link details if valid, or error information if invalid.
    """
    service = ShareLinkService(db)
    result = service.validate_link(token, password)
    
    if not result:
        return ValidateLinkResponse(valid=False, error="invalid_token")
    
    if "error" in result:
        return ValidateLinkResponse(valid=False, error=result["error"])
    
    return ValidateLinkResponse(
        valid=True,
        resource_type=result["resource_type"],
        resource_id=result["resource_id"],
        permissions=result["permissions"],
        expires_at=result["expires_at"],
    )


@router.get("/links", response_model=list)
async def list_share_links(
    resource_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """
    List all share links (admin only).
    
    Filter by resource type and active status.
    """
    service = ShareLinkService(db)
    links = service.list_links(
        resource_type=resource_type,
        active_only=active_only,
    )
    
    return [
        {
            "id": link.id,
            "resource_type": link.resource_type,
            "resource_id": link.resource_id,
            "permissions": link.permissions,
            "use_count": link.use_count,
            "max_uses": link.max_uses,
            "is_active": link.is_active,
            "is_expired": link.expires_at < __import__('datetime').datetime.utcnow(),
            "expires_at": link.expires_at.isoformat(),
            "created_at": link.created_at.isoformat(),
            "has_password": link.password_hash is not None,
            "description": link.description,
        }
        for link in links
    ]


@router.get("/my-links", response_model=list)
async def list_my_share_links(
    db: Session = Depends(get_db),
    auth: dict = Depends(get_current_permission),
):
    """
    List share links created by the current user.
    """
    service = ShareLinkService(db)
    links = service.list_links(
        created_by=auth.get("employee_id"),
        active_only=False,  # Show all user's links
    )
    
    return [
        {
            "id": link.id,
            "resource_type": link.resource_type,
            "permissions": link.permissions,
            "use_count": link.use_count,
            "max_uses": link.max_uses,
            "is_active": link.is_active,
            "is_expired": link.expires_at < __import__('datetime').datetime.utcnow(),
            "expires_at": link.expires_at.isoformat(),
            "created_at": link.created_at.isoformat(),
            "has_password": link.password_hash is not None,
            "description": link.description,
        }
        for link in links
    ]


@router.get("/stats/{link_id}")
async def get_share_link_stats(
    link_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(get_current_permission),
):
    """
    Get detailed statistics for a share link.
    
    Users can only view stats for their own links.
    Admins can view all links.
    """
    service = ShareLinkService(db)
    stats = service.get_link_stats(link_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    # Check permissions
    link = service.db.query(service.db.query(ShareLink).filter(ShareLink.id == link_id).exists()).scalar()
    if not auth.get("is_admin"):
        link_obj = service.db.query(ShareLink).filter(ShareLink.id == link_id).first()
        if link_obj and link_obj.created_by != auth.get("employee_id"):
            raise HTTPException(status_code=403, detail="Can only view your own share links")
    
    return stats


@router.post("/revoke/{link_id}")
async def revoke_share_link(
    link_id: str,
    db: Session = Depends(get_db),
    auth: dict = Depends(get_current_permission),
):
    """
    Revoke a share link.
    
    Users can only revoke their own links.
    Admins can revoke any link.
    """
    service = ShareLinkService(db)
    
    # Check permissions
    link = service.db.query(ShareLink).filter(ShareLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")
    
    if not auth.get("is_admin") and link.created_by != auth.get("employee_id"):
        raise HTTPException(status_code=403, detail="Can only revoke your own share links")
    
    success = service.revoke_link(link_id, revoked_by=auth.get("employee_id"))
    
    if success:
        return {
            "success": True,
            "message": f"Share link '{link_id}' has been revoked",
        }
    else:
        raise HTTPException(status_code=404, detail="Share link not found")


@router.post("/cleanup")
async def cleanup_expired_links(
    db: Session = Depends(get_db),
    auth: dict = Depends(require_admin_permission),
):
    """
    Clean up expired share links older than 7 days (admin only).
    """
    service = ShareLinkService(db)
    count = service.cleanup_expired()
    
    return {
        "success": True,
        "deleted_count": count,
        "message": f"Cleaned up {count} expired share links",
    }
