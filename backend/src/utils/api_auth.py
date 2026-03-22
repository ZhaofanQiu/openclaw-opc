"""
API Key authentication middleware for external access.
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.api_key_service import APIKeyService
from src.services.share_link_service import ShareLinkService


security = HTTPBearer(auto_error=False)


async def get_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> str:
    """
    Extract and validate API key from request.
    
    Checks in order:
    1. Authorization header (Bearer token)
    2. X-API-Key header
    3. api_key query parameter
    """
    api_key = None
    
    # 1. Check Authorization header
    if credentials:
        api_key = credentials.credentials
    else:
        # 2. Check X-API-Key header
        api_key = request.headers.get("X-API-Key")
    
    # 3. Check query parameter
    if not api_key:
        api_key = request.query_params.get("api_key")
    
    return api_key


async def get_share_token(request: Request) -> str:
    """
    Extract share link token from request.
    
    Checks in order:
    1. share_token query parameter
    2. token query parameter (for backward compatibility)
    """
    # Check query parameters
    share_token = request.query_params.get("share_token")
    if not share_token:
        share_token = request.query_params.get("token")
    
    return share_token


async def require_api_key(
    request: Request,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
    required_permission: str = None,
) -> dict:
    """
    Require valid API key for access.
    
    Raises:
        HTTPException: 401 if key is missing or invalid
        HTTPException: 403 if key lacks required permission
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via Authorization: Bearer <key> or X-API-Key header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    service = APIKeyService(db)
    
    # Validate key
    key_obj = service.validate_key(api_key, required_permission)
    if not key_obj:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
        )
    
    # Check IP restriction
    client_ip = request.client.host
    if not service.check_ip_allowed(key_obj, client_ip):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied from IP: {client_ip}",
        )
    
    # Record usage (async fire-and-forget)
    service.record_usage(key_obj.id)
    
    # Get user info from key (v1.1 - support user association)
    user_id = getattr(key_obj, 'user_id', None) or getattr(key_obj, 'created_by', 'system')
    user_name = getattr(key_obj, 'user_name', None) or key_obj.name
    
    return {
        "key_id": key_obj.id,
        "name": key_obj.name,
        "permissions": key_obj.permissions.split(","),
        "auth_type": "api_key",
        # User context for service layer
        "user_id": user_id,
        "user_name": user_name,
        "user_type": "api_key_user",
    }


async def get_current_permission(
    request: Request,
    api_key: str = Depends(get_api_key),
    share_token: str = Depends(get_share_token),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get current user permissions from API key or share link.
    
    Tries API key first, then falls back to share link.
    """
    # Try API key first
    if api_key:
        service = APIKeyService(db)
        key_obj = service.validate_key(api_key)
        if key_obj:
            service.record_usage(key_obj.id)
            # Get user info from key
            user_id = getattr(key_obj, 'user_id', None) or getattr(key_obj, 'created_by', 'system')
            return {
                "key_id": key_obj.id,
                "name": key_obj.name,
                "permissions": key_obj.permissions.split(","),
                "permission": key_obj.permissions.split(",")[0],
                "employee_id": None,  # API keys don't have employee_id
                "auth_type": "api_key",
                "is_admin": "admin" in key_obj.permissions.split(","),
                # User context
                "user_id": user_id,
                "user_name": getattr(key_obj, 'user_name', None) or key_obj.name,
                "user_type": "api_key_user",
            }
    
    # Try share link
    if share_token:
        service = ShareLinkService(db)
        result = service.validate_link(share_token)
        if result and result.get("valid"):
            service.record_usage(result["link_id"])
            return {
                "link_id": result["link_id"],
                "permissions": [result["permissions"]],
                "permission": result["permissions"],
                "resource_type": result["resource_type"],
                "resource_id": result["resource_id"],
                "employee_id": None,
                "auth_type": "share_link",
                "is_admin": False,
                "user_id": "share_link_user",
                "user_name": "Share Link User",
                "user_type": "share_link",
            }
    
    # No valid auth - return anonymous context
    return {
        "permissions": [],
        "permission": None,
        "employee_id": None,
        "auth_type": None,
        "is_admin": False,
        "user_id": "anonymous",
        "user_name": "Anonymous",
        "user_type": "anonymous",
    }


# Permission-based dependencies (async versions)
async def require_read_permission(
    request: Request,
    api_key: str = Depends(get_api_key),
    share_token: str = Depends(get_share_token),
    db: Session = Depends(get_db),
):
    """Require read permission (via API key or share link)."""
    # Try API key
    if api_key:
        try:
            return await require_api_key(request, api_key, db, "read")
        except HTTPException:
            pass
    
    # Try share link
    if share_token:
        service = ShareLinkService(db)
        result = service.validate_link(share_token)
        if result and result.get("valid"):
            service.record_usage(result["link_id"])
            return {
                "link_id": result["link_id"],
                "permissions": [result["permissions"]],
                "auth_type": "share_link",
            }
    
    # No valid auth
    raise HTTPException(
        status_code=401,
        detail="API key or share link required",
    )


async def require_write_permission(
    request: Request,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    """Require write permission."""
    return await require_api_key(request, api_key, db, "write")


async def require_admin_permission(
    request: Request,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    """Require admin permission."""
    return await require_api_key(request, api_key, db, "admin")


# Optional API key (for mixed public/private endpoints)
async def optional_api_key(
    request: Request,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> dict:
    """
    Optionally validate API key.
    Returns key info if valid, None otherwise (doesn't raise).
    """
    if not api_key:
        return None
    
    service = APIKeyService(db)
    key_obj = service.validate_key(api_key)
    
    if key_obj:
        service.record_usage(key_obj.id)
        return {
            "key_id": key_obj.id,
            "name": key_obj.name,
            "permissions": key_obj.permissions.split(","),
        }
    
    return None
