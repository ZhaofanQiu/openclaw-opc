"""
Avatar API routes.

Endpoints for employee avatar management with three modes:
- System-generated pixel art
- User uploaded
- AI-generated (via skill)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.avatar_service import AvatarService, AvatarSource
from utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter(prefix="/api/avatars", tags=["Avatars"])


# Schemas

class AvatarResponse(BaseModel):
    """Avatar response."""
    agent_id: str
    source: str
    url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AvatarOptionsResponse(BaseModel):
    """Avatar options response."""
    agent_id: str
    current: Optional[dict] = None
    options: list
    pixel_styles: list


class GenerateAvatarRequest(BaseModel):
    """Request to generate system avatar."""
    style: str = Field(default="humanoid", description="Pixel style: humanoid, robot, alien, spirit")


class AIAvatarRequest(BaseModel):
    """Request to generate AI avatar."""
    prompt: str = Field(..., min_length=1, description="Generation prompt")
    skill_name: str = Field(default="vivago-ai", description="Skill to use")


# Routes

@router.get("/{agent_id}", response_model=AvatarResponse)
async def get_avatar(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    Get employee avatar.
    
    Returns avatar metadata and URL.
    """
    service = AvatarService(db)
    avatar = service.get_avatar(agent_id)
    
    if not avatar:
        # Generate default system avatar
        avatar = service.generate_system_avatar(agent_id)
    
    return AvatarResponse(
        agent_id=agent_id,
        source=avatar.source,
        url=service.get_avatar_url(avatar),
        created_at=avatar.created_at.isoformat() if avatar.created_at else None,
        updated_at=avatar.updated_at.isoformat() if avatar.updated_at else None,
    )


@router.get("/{agent_id}/options", response_model=AvatarOptionsResponse)
async def get_avatar_options(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    Get available avatar options for an employee.
    
    Returns current avatar and list of available options.
    """
    service = AvatarService(db)
    options = service.get_avatar_options(agent_id)
    return AvatarOptionsResponse(**options)


@router.post("/{agent_id}/generate")
@limiter.limit(RATE_LIMITS["create"])
async def generate_system_avatar(
    request: Request,
    agent_id: str,
    data: GenerateAvatarRequest,
    db: Session = Depends(get_db),
):
    """
    Generate system pixel art avatar.
    
    Creates an SVG pixel art avatar based on style and position.
    """
    from models import Agent
    
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    service = AvatarService(db)
    avatar = service.generate_system_avatar(
        agent_id=agent_id,
        style=data.style,
        position=agent.position_title,
    )
    
    return {
        "success": True,
        "message": "Avatar generated successfully",
        "agent_id": agent_id,
        "source": avatar.source,
        "url": service.get_avatar_url(avatar),
        "style": data.style,
    }


@router.post("/{agent_id}/upload")
@limiter.limit(RATE_LIMITS["create"])
async def upload_avatar(
    request: Request,
    agent_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload custom avatar image.
    
    Supports PNG, JPG, JPEG, SVG formats.
    Max file size: 5MB.
    """
    from models import Agent
    
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check file size (5MB limit)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
    
    service = AvatarService(db)
    
    try:
        avatar = service.save_uploaded_avatar(
            agent_id=agent_id,
            file_data=content,
            filename=file.filename,
            content_type=file.content_type,
        )
        
        return {
            "success": True,
            "message": "Avatar uploaded successfully",
            "agent_id": agent_id,
            "source": avatar.source,
            "url": service.get_avatar_url(avatar),
            "filename": file.filename,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/ai-generate")
@limiter.limit(RATE_LIMITS["create"])
async def request_ai_avatar(
    request: Request,
    agent_id: str,
    data: AIAvatarRequest,
    db: Session = Depends(get_db),
):
    """
    Request AI-generated avatar.
    
    Creates a pending request for AI avatar generation.
    User must have configured the specified skill.
    
    Note: This only records the request. Actual generation must be
    triggered manually or via skill integration.
    """
    from models import Agent
    
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    service = AvatarService(db)
    result = service.request_ai_avatar(
        agent_id=agent_id,
        prompt=data.prompt,
        skill_name=data.skill_name,
    )
    
    return result


@router.post("/{agent_id}/ai-update")
async def update_ai_avatar_url(
    agent_id: str,
    external_url: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Update AI avatar with generated URL.
    
    Called by skill callback or manual update after AI generation completes.
    """
    service = AvatarService(db)
    avatar = service.update_ai_avatar_url(agent_id, external_url)
    
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    
    return {
        "success": True,
        "message": "AI avatar URL updated",
        "agent_id": agent_id,
        "url": external_url,
    }


@router.post("/{agent_id}/regenerate")
@limiter.limit(RATE_LIMITS["create"])
async def regenerate_avatar(
    request: Request,
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    Regenerate system avatar with random variations.
    
    Picks a random pixel style and generates a new avatar.
    """
    from models import Agent
    
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    service = AvatarService(db)
    avatar = service.regenerate_system_avatar(agent_id)
    
    return {
        "success": True,
        "message": "Avatar regenerated with random style",
        "agent_id": agent_id,
        "source": avatar.source,
        "url": service.get_avatar_url(avatar),
    }


@router.delete("/{agent_id}")
async def delete_avatar(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete employee avatar.
    
    Removes avatar record and associated file. Employee will get default avatar.
    """
    service = AvatarService(db)
    avatar = service.get_avatar(agent_id)
    
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    
    # Delete file if exists
    if avatar.storage_path:
        from pathlib import Path
        path = Path(avatar.storage_path)
        if path.exists():
            path.unlink()
    
    # Delete record
    db.delete(avatar)
    db.commit()
    
    return {
        "success": True,
        "message": "Avatar deleted",
        "agent_id": agent_id,
    }
