"""
Share Link Service

Generates and validates JWT-signed share links for temporary access.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from jose import JWTError, jwt
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import Session

from database import Base


class ShareLink(Base):
    """Share link model for temporary access."""
    __tablename__ = "share_links"
    
    id = Column(String, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)  # JWT token
    
    # What is being shared
    resource_type = Column(String, nullable=False)  # dashboard, report, task, agent
    resource_id = Column(String, nullable=True)  # Optional specific resource ID
    
    # Permissions granted by this link
    permissions = Column(String, default="read")  # read, write
    
    # Access control
    max_uses = Column(Integer, nullable=True)  # NULL = unlimited
    use_count = Column(Integer, default=0)
    password_hash = Column(String, nullable=True)  # Optional password protection
    
    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)  # Employee ID who created
    description = Column(Text, nullable=True)  # User-provided description
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)


class ShareLinkService:
    """Service for managing share links."""
    
    # Resource types
    RESOURCE_DASHBOARD = "dashboard"
    RESOURCE_REPORT = "report"
    RESOURCE_TASK = "task"
    RESOURCE_AGENT = "agent"
    RESOURCE_PIXEL_OFFICE = "pixel_office"
    
    # Permission levels
    PERMISSION_READ = "read"
    PERMISSION_WRITE = "write"
    
    # JWT settings
    JWT_ALGORITHM = "HS256"
    JWT_ISSUER = "openclaw-opc"
    
    def __init__(self, db: Session, secret_key: Optional[str] = None):
        self.db = db
        self.secret_key = secret_key or self._get_secret_key()
    
    def _get_secret_key(self) -> str:
        """Get or generate JWT secret key."""
        import os
        # In production, this should be set via environment variable
        secret = os.getenv("OPC_JWT_SECRET")
        if not secret:
            # Generate a random secret for development
            # In production, this should fail hard
            secret = secrets.token_hex(32)
        return secret
    
    def create_link(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        permissions: str = "read",
        expires_hours: int = 24,
        max_uses: Optional[int] = None,
        password: Optional[str] = None,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
    ) -> tuple:
        """
        Create a new share link.
        
        Args:
            resource_type: Type of resource (dashboard, report, etc.)
            resource_id: Optional specific resource ID
            permissions: read or write
            expires_hours: Link expiration time in hours
            max_uses: Maximum number of uses (None = unlimited)
            password: Optional password protection
            created_by: Employee ID who created the link
            description: User-provided description
        
        Returns:
            tuple: (ShareLink object, full_url)
        """
        # Validate resource type
        valid_types = {
            self.RESOURCE_DASHBOARD,
            self.RESOURCE_REPORT,
            self.RESOURCE_TASK,
            self.RESOURCE_AGENT,
            self.RESOURCE_PIXEL_OFFICE,
        }
        if resource_type not in valid_types:
            raise ValueError(f"Invalid resource type: {resource_type}")
        
        # Validate permissions
        if permissions not in {self.PERMISSION_READ, self.PERMISSION_WRITE}:
            raise ValueError(f"Invalid permissions: {permissions}")
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        # Generate JWT token
        link_id = str(uuid.uuid4())[:12]
        token = self._generate_jwt(
            link_id=link_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permissions=permissions,
            expires_at=expires_at,
        )
        
        # Hash password if provided
        password_hash = None
        if password:
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create record
        share_link = ShareLink(
            id=link_id,
            token=token,
            resource_type=resource_type,
            resource_id=resource_id,
            permissions=permissions,
            max_uses=max_uses,
            password_hash=password_hash,
            expires_at=expires_at,
            created_by=created_by,
            description=description,
        )
        
        self.db.add(share_link)
        self.db.commit()
        self.db.refresh(share_link)
        
        # Generate full URL
        full_url = self._build_share_url(token)
        
        return share_link, full_url
    
    def _generate_jwt(
        self,
        link_id: str,
        resource_type: str,
        resource_id: Optional[str],
        permissions: str,
        expires_at: datetime,
    ) -> str:
        """Generate JWT token for share link."""
        payload = {
            "jti": link_id,  # JWT ID
            "iss": self.JWT_ISSUER,
            "iat": datetime.utcnow(),
            "exp": expires_at,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "permissions": permissions,
            "type": "share_link",
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.JWT_ALGORITHM)
    
    def _build_share_url(self, token: str) -> str:
        """Build full share URL from token."""
        import os
        base_url = os.getenv("OPC_BASE_URL", "http://localhost:3000")
        return f"{base_url}/share?token={token}"
    
    def validate_link(
        self,
        token: str,
        password: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a share link token.
        
        Args:
            token: JWT token from URL
            password: Optional password for protected links
        
        Returns:
            Dict with link info if valid, None otherwise
        """
        # First, verify JWT
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.JWT_ALGORITHM],
                issuer=self.JWT_ISSUER,
            )
        except JWTError:
            return None
        
        # Get link from database
        link_id = payload.get("jti")
        share_link = self.db.query(ShareLink).filter(ShareLink.id == link_id).first()
        
        if not share_link:
            return None
        
        # Check if active
        if not share_link.is_active:
            return None
        
        # Check if revoked
        if share_link.revoked_at:
            return None
        
        # Check expiration (both JWT and database)
        if datetime.utcnow() > share_link.expires_at:
            return None
        
        # Check max uses
        if share_link.max_uses and share_link.use_count >= share_link.max_uses:
            return None
        
        # Check password if protected
        if share_link.password_hash:
            if not password:
                return {"error": "password_required"}
            import hashlib
            provided_hash = hashlib.sha256(password.encode()).hexdigest()
            if provided_hash != share_link.password_hash:
                return {"error": "invalid_password"}
        
        return {
            "valid": True,
            "link_id": link_id,
            "resource_type": share_link.resource_type,
            "resource_id": share_link.resource_id,
            "permissions": share_link.permissions,
            "expires_at": share_link.expires_at.isoformat(),
        }
    
    def record_usage(self, link_id: str):
        """Record link usage."""
        share_link = self.db.query(ShareLink).filter(ShareLink.id == link_id).first()
        if share_link:
            share_link.use_count += 1
            share_link.last_used_at = datetime.utcnow()
            self.db.commit()
    
    def revoke_link(
        self,
        link_id: str,
        revoked_by: Optional[str] = None,
    ) -> bool:
        """Revoke a share link."""
        share_link = self.db.query(ShareLink).filter(ShareLink.id == link_id).first()
        if not share_link:
            return False
        
        share_link.is_active = False
        share_link.revoked_at = datetime.utcnow()
        share_link.revoked_by = revoked_by
        self.db.commit()
        
        return True
    
    def list_links(
        self,
        resource_type: Optional[str] = None,
        created_by: Optional[str] = None,
        active_only: bool = True,
    ) -> list:
        """List share links with filters."""
        query = self.db.query(ShareLink)
        
        if resource_type:
            query = query.filter(ShareLink.resource_type == resource_type)
        
        if created_by:
            query = query.filter(ShareLink.created_by == created_by)
        
        if active_only:
            query = query.filter(
                ShareLink.is_active == True,
                ShareLink.revoked_at == None,
                ShareLink.expires_at > datetime.utcnow(),
            )
        
        return query.order_by(ShareLink.created_at.desc()).all()
    
    def get_link_stats(self, link_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed stats for a share link."""
        share_link = self.db.query(ShareLink).filter(ShareLink.id == link_id).first()
        if not share_link:
            return None
        
        return {
            "id": share_link.id,
            "resource_type": share_link.resource_type,
            "resource_id": share_link.resource_id,
            "permissions": share_link.permissions,
            "use_count": share_link.use_count,
            "max_uses": share_link.max_uses,
            "is_active": share_link.is_active,
            "is_expired": datetime.utcnow() > share_link.expires_at,
            "expires_at": share_link.expires_at.isoformat(),
            "created_at": share_link.created_at.isoformat(),
            "last_used_at": share_link.last_used_at.isoformat() if share_link.last_used_at else None,
            "has_password": share_link.password_hash is not None,
        }
    
    def cleanup_expired(self) -> int:
        """Clean up expired share links. Returns count deleted."""
        expired = self.db.query(ShareLink).filter(
            ShareLink.expires_at < datetime.utcnow() - timedelta(days=7)
        ).all()
        
        count = len(expired)
        for link in expired:
            self.db.delete(link)
        
        self.db.commit()
        return count
