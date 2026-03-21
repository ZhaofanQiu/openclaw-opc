"""
API Key authentication middleware for external access.
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.api_key_service import APIKeyService


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
    
    return {
        "key_id": key_obj.id,
        "name": key_obj.name,
        "permissions": key_obj.permissions.split(","),
    }


# Permission-based dependencies (async versions)
async def require_read_permission(
    request: Request,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
):
    """Require read permission."""
    return await require_api_key(request, api_key, db, "read")


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
