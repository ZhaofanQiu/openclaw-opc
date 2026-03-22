"""
Avatar Service

Manages employee avatar generation with three modes:
1. AI-generated (via external skill)
2. User uploaded
3. System-generated pixel art (default)
"""

import os
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import Session

from database import Base


class AvatarSource(str, PyEnum):
    """Avatar source types."""
    SYSTEM = "system"      # Auto-generated pixel art
    AI_GENERATED = "ai"    # AI-generated via skill
    UPLOADED = "uploaded"  # User uploaded


class EmployeeAvatar(Base):
    """Employee avatar metadata."""
    __tablename__ = "employee_avatars"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False, index=True, unique=True)
    
    # Avatar source
    source = Column(String, default=AvatarSource.SYSTEM.value)
    
    # Storage path or URL
    storage_path = Column(String, nullable=True)  # Local path for uploaded/system
    external_url = Column(String, nullable=True)  # URL for AI-generated
    
    # For system-generated: store generation parameters
    style_params = Column(Text, nullable=True)  # JSON: colors, features, etc.
    
    # For AI-generated: store prompt and skill used
    generation_prompt = Column(Text, nullable=True)
    skill_used = Column(String, nullable=True)
    
    # For uploaded: store original filename
    original_filename = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AvatarService:
    """Service for managing employee avatars."""
    
    # Upload directory - should be accessible from web
    # Try absolute path first (for Docker), then relative from project root
    UPLOAD_DIR = Path("/usr/share/nginx/html/avatars") if Path("/usr/share/nginx/html/avatars").exists() else Path(__file__).parent.parent.parent.parent / "web" / "avatars"
    
    # Pixel art templates (8x8 grid characters) - Human-like designs
    PIXEL_TEMPLATES = {
        "humanoid": [
            "..XXXX..",  # Head
            ".XX..XX.",  # Face/ears
            "..XXXX..",  # Neck/collar
            ".XXXXXX.",  # Shoulders
            "XXXXXXXX",  # Body
            "XXXXXXXX",  # Body
            "..XXXX..",  # Legs start
            ".XX..XX.",  # Feet
        ],
        "robot": [
            ".XXXXXX.",  # Head
            "XX.XX.XX",  # Eyes/antenna
            ".XXXXXX.",  # Face plate
            "XXXXXXXX",  # Shoulders
            "X.XXXX.X",  # Body with panel
            "XXXXXXXX",  # Body
            ".XX.XX..",  # Legs
            ".XX.XX..",  # Feet
        ],
        "alien": [
            "...XX...",  # Small head
            "..XXXX..",  # Big eyes area
            ".XXXXXX.",  # Face
            "..XXXX..",  # Neck
            ".XXXXXX.",  # Shoulders
            "XXXXXXXX",  # Body
            ".XX.XX..",  # Thin legs
            ".XX.....",  # Feet
        ],
        "spirit": [
            "........",
            "...XX...",  # Head
            "..XXXX..",  # Face
            ".XX..XX.",  # Shoulders
            ".XX..XX.",  # Body
            "..XXXX..",  # Lower body
            "...XX...",  # Ghost tail start
            "...XX...",  # Ghost tail
        ],
        # New human-like templates
        "person1": [
            "...XX...",  # Head
            "..XXXX..",  # Face
            "...XX...",  # Neck
            ".XXXXXX.",  # Shoulders
            "XXXXXXXX",  # Body
            "XXXXXXXX",  # Body
            ".XX..XX.",  # Legs
            ".XX..XX.",  # Feet
        ],
        "person2": [
            "..XXXX..",  # Head
            ".X.XX.X.",  # Face with hair
            "..XXXX..",  # Neck
            ".XXXXXX.",  # Shoulders
            "XXXXXXXX",  # Body
            ".XXXXXX.",  # Waist
            ".XX..XX.",  # Legs
            "XX....XX",  # Feet
        ],
        "person3": [
            "...XX...",  # Head
            "..XXXX..",  # Face wide
            "...XX...",  # Neck
            "XXXXXXXX",  # Wide shoulders
            "XXXXXXXX",  # Body
            "XXXXXXXX",  # Body
            ".XX..XX.",  # Legs
            ".XX..XX.",  # Feet
        ],
    }
    
    # Color palettes for different positions
    COLOR_PALETTES = {
        "CEO": ["#FFD700", "#FFA500", "#FF6347"],      # Gold/Orange
        "CTO": ["#4169E1", "#00BFFF", "#1E90FF"],      # Blue
        "Developer": ["#32CD32", "#00FF00", "#228B22"], # Green
        "Designer": ["#FF69B4", "#DA70D6", "#9370DB"],  # Pink/Purple
        "Manager": ["#708090", "#A9A9A9", "#D3D3D3"],   # Gray
        "Intern": ["#87CEEB", "#ADD8E6", "#B0E0E6"],    # Light Blue
        "Partner": ["#DC143C", "#B22222", "#8B0000"],   # Red (special)
        "default": ["#667eea", "#764ba2", "#f093fb"],    # Purple gradient
    }
    
    def __init__(self, db: Session, upload_dir: Optional[Path] = None):
        self.db = db
        self.UPLOAD_DIR = upload_dir or self.__class__.UPLOAD_DIR
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    def get_avatar(self, agent_id: str) -> Optional[EmployeeAvatar]:
        """Get avatar for an employee."""
        return self.db.query(EmployeeAvatar).filter(
            EmployeeAvatar.agent_id == agent_id
        ).first()
    
    def generate_system_avatar(
        self,
        agent_id: str,
        style: str = "humanoid",
        position: str = "default",
    ) -> EmployeeAvatar:
        """
        Generate a system pixel art avatar.
        
        Args:
            agent_id: Employee ID
            style: Template style (humanoid, robot, alien, spirit)
            position: Position for color palette
        
        Returns:
            Created avatar record
        
        Raises:
            Exception: If avatar generation fails
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"Generating system avatar for agent_id={agent_id}, style={style}, position={position}")
            
            # For random generation, prefer person-like templates
            if style == "humanoid":
                import random
                person_styles = ["humanoid", "person1", "person2", "person3"]
                style = random.choice(person_styles)
                logger.info(f"Selected random person style: {style}")
            
            # Check if avatar exists
            avatar = self.get_avatar(agent_id)
            if not avatar:
                logger.info(f"Creating new avatar record for agent_id={agent_id}")
                avatar = EmployeeAvatar(
                    id=str(uuid.uuid4())[:8],
                    agent_id=agent_id,
                )
                self.db.add(avatar)
            else:
                logger.info(f"Updating existing avatar record for agent_id={agent_id}")
            
            # Select template and colors
            template = self.PIXEL_TEMPLATES.get(style, self.PIXEL_TEMPLATES["humanoid"])
            colors = self.COLOR_PALETTES.get(position, self.COLOR_PALETTES["default"])
            logger.debug(f"Using template={style}, colors={colors}")
            
            # Generate SVG
            try:
                svg_content = self._generate_svg_avatar(template, colors)
                logger.debug(f"Generated SVG content length={len(svg_content)}")
            except Exception as svg_error:
                logger.error(f"Failed to generate SVG: {svg_error}")
                raise ValueError(f"SVG generation failed: {svg_error}") from svg_error
            
            # Save to file with unique filename including style and timestamp
            import time
            timestamp = int(time.time()) % 10000  # Short timestamp for uniqueness
            filename = f"{agent_id}_{style}_{timestamp}.svg"
            filepath = self.UPLOAD_DIR / filename
            
            # Ensure upload directory exists and is writable
            try:
                self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                logger.info(f"Upload directory ensured: {self.UPLOAD_DIR}")
            except Exception as dir_error:
                logger.error(f"Failed to create upload directory {self.UPLOAD_DIR}: {dir_error}")
                raise IOError(f"Cannot create upload directory: {dir_error}") from dir_error
            
            # Check if directory is writable
            if not os.access(self.UPLOAD_DIR, os.W_OK):
                logger.error(f"Upload directory is not writable: {self.UPLOAD_DIR}")
                raise IOError(f"Upload directory is not writable: {self.UPLOAD_DIR}")
            
            # Write file
            try:
                filepath.write_text(svg_content)
                logger.info(f"Avatar saved to: {filepath}")
            except Exception as write_error:
                logger.error(f"Failed to write avatar file {filepath}: {write_error}")
                raise IOError(f"Cannot write avatar file: {write_error}") from write_error
            
            # Update record
            avatar.source = AvatarSource.SYSTEM.value
            avatar.storage_path = str(filepath)
            avatar.style_params = f'{{"template": "{style}", "colors": {colors}}}'
            avatar.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(avatar)
            
            # Update Agent's avatar URL
            try:
                from models.agent import Agent
                agent_record = self.db.query(Agent).filter(Agent.id == agent_id).first()
                if agent_record:
                    avatar_url = self.get_avatar_url(avatar)
                    agent_record.avatar_url = avatar_url
                    agent_record.avatar_source = "system"
                    self.db.commit()
                    logger.info(f"Updated Agent {agent_id} avatar_url to {avatar_url}")
            except Exception as e:
                logger.error(f"Failed to update agent avatar_url: {e}")
            
            logger.info(f"Avatar record saved successfully for agent_id={agent_id}")
            
            return avatar
            
        except Exception as e:
            logger.error(f"Failed to generate system avatar for agent_id={agent_id}: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def _generate_svg_avatar(self, template: list, colors: list) -> str:
        """
        Generate SVG pixel art from template.
        
        Args:
            template: 8x8 character grid
            colors: List of hex colors
        
        Returns:
            SVG string
        """
        pixel_size = 10
        grid_size = 8
        
        # Build rectangles
        rects = []
        color_idx = 0
        
        for row_idx, row in enumerate(template):
            for col_idx, char in enumerate(row):
                if char == 'X':
                    x = col_idx * pixel_size
                    y = row_idx * pixel_size
                    # Cycle through colors
                    color = colors[color_idx % len(colors)]
                    rects.append(
                        f'    <rect x="{x}" y="{y}" width="{pixel_size}" height="{pixel_size}" '
                        f'fill="{color}"/>'
                    )
                    color_idx += 1
        
        svg_width = grid_size * pixel_size
        svg_height = grid_size * pixel_size
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" 
     xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="#1a1a2e"/>
{chr(10).join(rects)}
</svg>'''
        
        return svg
    
    def request_ai_avatar(
        self,
        agent_id: str,
        prompt: str,
        skill_name: str = "vivago-ai",
    ) -> Dict[str, Any]:
        """
        Request AI-generated avatar via skill.
        
        Two modes:
        1. If skill is available: Partner will call skill to generate immediately
        2. If skill not available: Record pending request for manual generation
        
        Args:
            agent_id: Employee ID
            prompt: Generation prompt
            skill_name: Skill to use for generation
        
        Returns:
            Status dict with pending flag or immediate result
        """
        from services.agent_service import AgentService
        
        # Check if avatar exists
        avatar = self.get_avatar(agent_id)
        if not avatar:
            avatar = EmployeeAvatar(
                id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
            )
            self.db.add(avatar)
        
        # Mark as pending AI generation
        avatar.source = AvatarSource.AI_GENERATED.value
        avatar.generation_prompt = prompt
        avatar.skill_used = skill_name
        avatar.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Try to trigger generation via Partner Agent
        try:
            agent_service = AgentService(self.db)
            result = agent_service.trigger_avatar_generation(
                agent_id=agent_id,
                prompt=prompt,
                skill_name=skill_name,
            )
            
            if result.get("success"):
                return {
                    "status": "generating",
                    "agent_id": agent_id,
                    "prompt": prompt,
                    "skill": skill_name,
                    "message": "头像生成任务已发送给Partner，请稍后刷新查看结果",
                    "task_id": result.get("task_id"),
                }
        except Exception as e:
            # Skill not available or generation failed, keep as pending
            pass
        
        return {
            "status": "pending",
            "agent_id": agent_id,
            "prompt": prompt,
            "skill": skill_name,
            "message": f"头像生成请求已记录。请确保已配置 {skill_name} skill，然后让Partner执行生成任务。",
        }
    
    def save_uploaded_avatar(
        self,
        agent_id: str,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> EmployeeAvatar:
        """
        Save user-uploaded avatar.
        
        Args:
            agent_id: Employee ID
            file_data: Raw file bytes
            filename: Original filename
            content_type: MIME type
        
        Returns:
            Created avatar record
        """
        # Validate file size (max 5MB)
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
        if len(file_data) > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds 5MB limit. Got {len(file_data) / 1024 / 1024:.2f}MB")
        
        # Validate file signature (magic bytes)
        self._validate_file_signature(file_data, content_type)
        
        # Validate content type
        allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
        if content_type not in allowed_types:
            raise ValueError(f"Invalid content type: {content_type}. Allowed: {', '.join(allowed_types)}")
        
        # Generate safe filename
        ext = Path(filename).suffix.lower()
        if ext not in [".png", ".jpg", ".jpeg", ".svg"]:
            # Infer from content type
            ext_map = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/svg+xml": ".svg",
            }
            ext = ext_map.get(content_type, ".png")
        
        safe_filename = f"{agent_id}_upload{ext}"
        filepath = self.UPLOAD_DIR / safe_filename
        
        # Save file
        filepath.write_bytes(file_data)
        
        # Check if avatar exists
        avatar = self.get_avatar(agent_id)
        if not avatar:
            avatar = EmployeeAvatar(
                id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
            )
            self.db.add(avatar)
        
        # Update record
        avatar.source = AvatarSource.UPLOADED.value
        avatar.storage_path = str(filepath)
        avatar.original_filename = filename
        avatar.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(avatar)
        
        # Update Agent's avatar URL
        try:
            from models.agent import Agent
            agent_record = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent_record:
                avatar_url = self.get_avatar_url(avatar)
                agent_record.avatar_url = avatar_url
                agent_record.avatar_source = "uploaded"
                self.db.commit()
                logger.info(f"Updated Agent {agent_id} avatar_url to {avatar_url}")
        except Exception as e:
            logger.error(f"Failed to update agent avatar_url: {e}")
            # Don't fail the upload if this fails
        
        return avatar
    
    def get_avatar_url(self, avatar: EmployeeAvatar) -> str:
        """
        Get avatar URL for display.
        
        Args:
            avatar: Avatar record
        
        Returns:
            URL string
        """
        if not avatar:
            return "/avatars/default.svg"
        
        if avatar.source == AvatarSource.AI_GENERATED.value and avatar.external_url:
            return avatar.external_url
        
        if avatar.storage_path:
            # Convert to relative URL
            path = Path(avatar.storage_path)
            return f"/avatars/{path.name}"
        
        return "/avatars/default.svg"
    
    def update_ai_avatar_url(
        self,
        agent_id: str,
        external_url: str,
    ) -> Optional[EmployeeAvatar]:
        """
        Update avatar with AI-generated URL.
        
        Called by skill callback or manual update.
        
        Args:
            agent_id: Employee ID
            external_url: Generated image URL
        
        Returns:
            Updated avatar or None
        """
        avatar = self.get_avatar(agent_id)
        if not avatar:
            return None
        
        avatar.external_url = external_url
        avatar.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(avatar)
        
        # Update Agent's avatar URL
        try:
            from models.agent import Agent
            agent_record = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent_record:
                agent_record.avatar_url = external_url
                agent_record.avatar_source = "ai"
                self.db.commit()
                logger.info(f"Updated Agent {agent_id} avatar_url to AI avatar: {external_url}")
        except Exception as e:
            logger.error(f"Failed to update agent avatar_url for AI avatar: {e}")
        
        return avatar
        
        return avatar
    
    def regenerate_system_avatar(
        self,
        agent_id: str,
    ) -> EmployeeAvatar:
        """
        Regenerate system avatar with random variations.

        Args:
            agent_id: Employee ID

        Returns:
            Updated avatar

        Raises:
            Exception: If avatar regeneration fails
        """
        import logging
        import random

        logger = logging.getLogger(__name__)

        try:
            logger.info(f"Regenerating system avatar for agent_id={agent_id}")

            # Pick random style
            available_styles = list(self.PIXEL_TEMPLATES.keys())
            style = random.choice(available_styles)
            logger.debug(f"Randomly selected style: {style}")

            # Get agent position for colors
            from models.agent import Agent
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()

            if agent:
                position = agent.position_title if agent.position_title else "default"
                logger.debug(f"Using agent position_title: {position}")
            else:
                position = "default"
                logger.warning(f"Agent {agent_id} not found, using default position")

            # Check if position exists in COLOR_PALETTES
            if position not in self.COLOR_PALETTES:
                logger.debug(f"Position '{position}' not found in COLOR_PALETTES, using default")
                position = "default"

            return self.generate_system_avatar(agent_id, style=style, position=position)

        except Exception as e:
            logger.error(f"Failed to regenerate system avatar for agent_id={agent_id}: {e}", exc_info=True)
            # Re-raise with more context for better error handling
            raise Exception(f"头像生成失败: {str(e)}") from e
    
    def _validate_file_signature(self, file_data: bytes, content_type: str) -> None:
        """
        Validate file signature (magic bytes) matches content type.
        
        Args:
            file_data: Raw file bytes
            content_type: Declared MIME type
        
        Raises:
            ValueError: If signature doesn't match
        """
        # File signatures (magic bytes)
        SIGNATURES = {
            "image/png": [b'\x89PNG\r\n\x1a\n'],
            "image/jpeg": [b'\xff\xd8\xff'],
            "image/jpg": [b'\xff\xd8\xff'],
            "image/svg+xml": [b'<?xml', b'<svg'],  # SVG can start with either
        }
        
        expected_signatures = SIGNATURES.get(content_type)
        if not expected_signatures:
            return  # Unknown type, skip validation
        
        # Check if file starts with any valid signature
        is_valid = False
        for sig in expected_signatures:
            if file_data.startswith(sig):
                is_valid = True
                break
        
        if not is_valid:
            actual_start = file_data[:20] if len(file_data) >= 20 else file_data
            raise ValueError(
                f"File signature mismatch. Expected {content_type} signature, "
                f"got bytes: {actual_start[:10]}..."
            )
    
    def get_avatar_options(self, agent_id: str) -> Dict[str, Any]:
        """
        Get available avatar options for an employee.
        
        Returns:
            Dict with current avatar and available options
        """
        avatar = self.get_avatar(agent_id)
        
        return {
            "agent_id": agent_id,
            "current": {
                "source": avatar.source if avatar else None,
                "url": self.get_avatar_url(avatar),
            } if avatar else None,
            "options": [
                {
                    "type": "system",
                    "label": "系统生成",
                    "description": "自动生成像素风格头像",
                    "available": True,
                },
                {
                    "type": "upload",
                    "label": "上传头像",
                    "description": "上传自己的图片 (PNG/JPG/SVG)",
                    "available": True,
                },
                {
                    "type": "ai",
                    "label": "AI生成",
                    "description": "使用AI技能生成个性化头像 (需要配置skill)",
                    "available": False,  # Requires skill configuration
                    "note": "需要配置 vivago-ai 或其他图像生成skill",
                },
            ],
            "pixel_styles": list(self.PIXEL_TEMPLATES.keys()),
        }

    def delete_avatar(self, agent_id: str) -> bool:
        """
        Delete avatar for an employee.

        Args:
            agent_id: Employee ID

        Returns:
            True if deleted, False if no avatar exists
        """
        avatar = self.get_avatar(agent_id)
        if not avatar:
            return False

        # Delete file from storage if exists
        if avatar.storage_path:
            try:
                Path(avatar.storage_path).unlink(missing_ok=True)
            except Exception:
                pass  # File may not exist

        # Delete from database
        self.db.query(EmployeeAvatar).filter(EmployeeAvatar.agent_id == agent_id).delete()
        self.db.commit()

        return True
