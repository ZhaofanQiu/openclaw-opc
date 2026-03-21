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

from src.database import Base


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
    
    # Upload directory
    UPLOAD_DIR = Path("./data/avatars")
    
    # Pixel art templates (8x8 grid characters)
    PIXEL_TEMPLATES = {
        "humanoid": [
            "........",
            "...XX...",
            "..XXXX..",
            ".XXXXXX.",
            ".XXXXXX.",
            "..XXXX..",
            "...XX...",
            "........",
        ],
        "robot": [
            "..XXXX..",
            ".X....X.",
            "X.XXXX.X",
            "X.X..X.X",
            "X.X..X.X",
            "X.XXXX.X",
            ".X....X.",
            "..XXXX..",
        ],
        "alien": [
            "...XX...",
            "..XXXX..",
            ".XXXXXX.",
            "XX.XX.XX",
            "XXXXXXXX",
            ".XXXXXX.",
            "..XXXX..",
            "...XX...",
        ],
        "spirit": [
            "........",
            "...XX...",
            "..XXXX..",
            ".XX..XX.",
            ".XX..XX.",
            ".XX..XX.",
            "..XXXX..",
            "...XX...",
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
    
    def __init__(self, db: Session):
        self.db = db
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
        """
        # Check if avatar exists
        avatar = self.get_avatar(agent_id)
        if not avatar:
            avatar = EmployeeAvatar(
                id=str(uuid.uuid4())[:8],
                agent_id=agent_id,
            )
            self.db.add(avatar)
        
        # Select template and colors
        template = self.PIXEL_TEMPLATES.get(style, self.PIXEL_TEMPLATES["humanoid"])
        colors = self.COLOR_PALETTES.get(position, self.COLOR_PALETTES["default"])
        
        # Generate SVG
        svg_content = self._generate_svg_avatar(template, colors)
        
        # Save to file
        filename = f"{agent_id}_system.svg"
        filepath = self.UPLOAD_DIR / filename
        filepath.write_text(svg_content)
        
        # Update record
        avatar.source = AvatarSource.SYSTEM.value
        avatar.storage_path = str(filepath)
        avatar.style_params = f'{{"template": "{style}", "colors": {colors}}}'
        avatar.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(avatar)
        
        return avatar
    
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
        
        svg = f'''"""?xml version="1.0" encoding="UTF-8"?>
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
        from src.services.agent_service import AgentService
        
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
        """
        import random
        
        # Pick random style
        style = random.choice(list(self.PIXEL_TEMPLATES.keys()))
        
        # Get agent position for colors
        from src.models import Agent
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        position = agent.position_title if agent else "default"
        
        return self.generate_system_avatar(agent_id, style=style, position=position)
    
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
