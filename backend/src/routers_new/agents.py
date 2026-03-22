"""
Agents Router (重构后)
合并: agents + avatars + skills + skill_growth + agent_skill_paths + agent_interaction_logs

核心原则: 简化接口，保留必要功能
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database import get_db
from src.utils.rate_limit import limiter
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/agents", tags=["Agents"])

# ============ 数据模型 ============

class AgentCreate(BaseModel):
    """创建员工请求"""
    name: str = Field(..., min_length=1, max_length=50)
    emoji: str = Field(default="🤖")
    position_level: int = Field(default=1, ge=1, le=5)
    skills: List[str] = Field(default=[])
    monthly_budget: int = Field(default=1000)

class AgentUpdate(BaseModel):
    """更新员工请求"""
    name: Optional[str] = None
    emoji: Optional[str] = None
    skills: Optional[List[str]] = None
    monthly_budget: Optional[int] = None

class AgentResponse(BaseModel):
    """员工响应"""
    id: str
    name: str
    emoji: str
    status: str
    position_level: int
    skills: List[dict]
    monthly_budget: int
    used_budget: int
    avatar_url: Optional[str] = None

class SkillAssign(BaseModel):
    """分配技能请求"""
    skill_id: str

# ============ 员工管理 ============

@router.get("", response_model=dict)
@limiter.limit("100/minute")
def list_agents(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取员工列表"""
    # TODO: 从 agent_service 获取
    return {"agents": [], "total": 0}

@router.post("", response_model=dict)
@limiter.limit("20/minute")
def create_agent(
    request: Request,
    data: AgentCreate,
    db: Session = Depends(get_db)
):
    """创建新员工"""
    # TODO: 调用 agent_service.create_agent
    return {"id": "", "message": "Agent created"}

@router.get("/{agent_id}", response_model=dict)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """获取员工详情"""
    # TODO: 从 agent_service 获取
    return {}

@router.put("/{agent_id}", response_model=dict)
def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: Session = Depends(get_db)
):
    """更新员工信息"""
    return {"message": "Agent updated"}

@router.delete("/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """删除员工"""
    return {"message": "Agent deleted"}

# ============ 头像管理 ============

@router.post("/{agent_id}/avatar")
def upload_avatar(
    agent_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传头像"""
    return {"avatar_url": ""}

@router.post("/{agent_id}/avatar/generate")
def generate_avatar(agent_id: str, db: Session = Depends(get_db)):
    """生成随机头像"""
    return {"avatar_url": ""}

# ============ 技能管理 ============

@router.get("/{agent_id}/skills")
def get_agent_skills(agent_id: str, db: Session = Depends(get_db)):
    """获取员工技能"""
    return {"skills": []}

@router.post("/{agent_id}/skills")
def assign_skill(
    agent_id: str,
    data: SkillAssign,
    db: Session = Depends(get_db)
):
    """分配技能给员工"""
    return {"message": "Skill assigned"}

@router.delete("/{agent_id}/skills/{skill_id}")
def remove_skill(agent_id: str, skill_id: str, db: Session = Depends(get_db)):
    """移除员工技能"""
    return {"message": "Skill removed"}

# ============ OpenClaw 绑定 ============

@router.post("/{agent_id}/bind")
def bind_openclaw_agent(
    agent_id: str,
    openclaw_agent_id: str,
    db: Session = Depends(get_db)
):
    """绑定 OpenClaw Agent"""
    return {"message": "Agent bound"}

@router.post("/{agent_id}/unbind")
def unbind_openclaw_agent(agent_id: str, db: Session = Depends(get_db)):
    """解绑 OpenClaw Agent"""
    return {"message": "Agent unbound"}

# ============ 预算管理 ============

@router.get("/{agent_id}/budget")
def get_agent_budget(agent_id: str, db: Session = Depends(get_db)):
    """获取员工预算信息"""
    return {
        "monthly_budget": 0,
        "used_budget": 0,
        "remaining": 0
    }

# ============ 交互日志 ============

@router.get("/{agent_id}/logs")
def get_agent_logs(
    agent_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取员工交互日志"""
    return {"logs": [], "total": 0}
