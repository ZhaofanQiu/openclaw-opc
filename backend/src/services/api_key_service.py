"""
API Key authentication for external access.
Provides secure access to OPC via API Keys with scoped permissions.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.orm import Session

from src.database import Base


class APIKey(Base):
    """API Key model for external access authentication."""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Key name/description
    key_hash = Column(String, nullable=False, index=True)  # Hashed key
    key_prefix = Column(String(8), nullable=False, index=True)  # First 8 chars for display
    
    # Permissions (bitmask or comma-separated)
    permissions = Column(String, default="read")  # read, write, admin
    
    # Scoping
    allowed_ips = Column(String, nullable=True)  # Comma-separated IPs, NULL = any
    allowed_origins = Column(String, nullable=True)  # CORS origins
    
    # Rate limiting (overrides default)
    rate_limit_per_minute = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)  # NULL = never
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)  # Employee ID who created


class APIKeyService:
    """Service for managing API Keys."""
    
    # Permission constants
    PERMISSION_READ = "read"
    PERMISSION_WRITE = "write"
    PERMISSION_ADMIN = "admin"
    
    def __init__(self, db: Session):
        self.db = db
    
    def _hash_key(self, key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _generate_key(self) -> str:
        """Generate a secure random API key."""
        # Format: opc_live_xxxxxxxxxxxx (32 chars after prefix)
        random_part = secrets.token_urlsafe(24)  # ~32 chars
        return f"opc_live_{random_part}"
    
    def create_key(
        self,
        name: str,
        permissions: List[str] = None,
        allowed_ips: List[str] = None,
        allowed_origins: List[str] = None,
        rate_limit: Optional[int] = None,
        expires_days: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> tuple:
        """
        Create a new API key.
        
        Returns:
            tuple: (APIKey object, plain_key) - plain_key is shown only once!
        """
        # Generate key
        plain_key = self._generate_key()
        key_hash = self._hash_key(plain_key)
        key_prefix = plain_key[:8]
        
        # Validate permissions
        if permissions is None:
            permissions = [self.PERMISSION_READ]
        
        valid_perms = {self.PERMISSION_READ, self.PERMISSION_WRITE, self.PERMISSION_ADMIN}
        for perm in permissions:
            if perm not in valid_perms:
                raise ValueError(f"Invalid permission: {perm}")
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Create record
        api_key = APIKey(
            id=str(uuid.uuid4())[:8],
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=",".join(permissions),
            allowed_ips=",".join(allowed_ips) if allowed_ips else None,
            allowed_origins=",".join(allowed_origins) if allowed_origins else None,
            rate_limit_per_minute=rate_limit,
            expires_at=expires_at,
            created_by=created_by,
        )
        
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        
        return api_key, plain_key
    
    def validate_key(self, key: str, required_permission: str = None) -> Optional[APIKey]:
        """
        Validate an API key.
        
        Args:
            key: Plain API key
            required_permission: Required permission level
        
        Returns:
            APIKey if valid, None otherwise
        """
        key_hash = self._hash_key(key)
        
        api_key = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Check permission
        if required_permission:
            perms = set(api_key.permissions.split(","))
            if required_permission not in perms and self.PERMISSION_ADMIN not in perms:
                return None
        
        return api_key
    
    def record_usage(self, key_id: str):
        """Record API key usage."""
        api_key = self.db.query(APIKey).filter(APIKey.id == key_id).first()
        if api_key:
            api_key.last_used_at = datetime.utcnow()
            api_key.use_count += 1
            self.db.commit()
    
    def check_ip_allowed(self, api_key: APIKey, client_ip: str) -> bool:
        """Check if client IP is allowed for this key."""
        if not api_key.allowed_ips:
            return True  # No IP restrictions
        
        allowed = api_key.allowed_ips.split(",")
        return client_ip in allowed
    
    def list_keys(self, include_expired: bool = False) -> List[APIKey]:
        """List all API keys."""
        query = self.db.query(APIKey)
        
        if not include_expired:
            query = query.filter(
                (APIKey.expires_at == None) | (APIKey.expires_at > datetime.utcnow())
            )
        
        return query.order_by(APIKey.created_at.desc()).all()
    
    def get_key(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        return self.db.query(APIKey).filter(APIKey.id == key_id).first()
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke (deactivate) an API key."""
        api_key = self.get_key(key_id)
        if not api_key:
            return False
        
        api_key.is_active = False
        self.db.commit()
        return True
    
    def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key."""
        api_key = self.get_key(key_id)
        if not api_key:
            return False
        
        self.db.delete(api_key)
        self.db.commit()
        return True
    
    def rotate_key(self, key_id: str) -> tuple:
        """
        Rotate (regenerate) an API key.
        
        Returns:
            tuple: (new_plain_key, success)
        """
        api_key = self.get_key(key_id)
        if not api_key:
            return None, False
        
        # Generate new key
        new_plain = self._generate_key()
        api_key.key_hash = self._hash_key(new_plain)
        api_key.key_prefix = new_plain[:8]
        api_key.use_count = 0
        api_key.last_used_at = None
        
        self.db.commit()
        
        return new_plain, True
    
    def get_stats(self) -> Dict:
        """Get API key usage statistics."""
        total = self.db.query(APIKey).count()
        active = self.db.query(APIKey).filter(APIKey.is_active == True).count()
        expired = self.db.query(APIKey).filter(
            APIKey.expires_at < datetime.utcnow()
        ).count()
        
        total_uses = self.db.query(APIKey).filter(
            APIKey.use_count > 0
        ).count()
        
        return {
            "total_keys": total,
            "active_keys": active,
            "expired_keys": expired,
            "keys_with_usage": total_uses,
        }
