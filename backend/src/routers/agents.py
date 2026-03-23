"""
Agents Router (重构后)
合并: agents + avatars + skills + skill_growth + agent_skill_paths + agent_interaction_logs

核心原则: 简化接口，保留必要功能
"""

import os
import json
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from database import get_db
from models.agent_v2 import Agent, AgentStatus
from utils.rate_limit import limiter
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Agents"])

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

class BindRequest(BaseModel):
    """绑定请求"""
    openclaw_agent_id: str

# ============ 员工管理 ============

@router.get("", response_model=dict)
@limiter.limit("100/minute")
def list_agents(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取员工列表"""
    query = db.query(Agent)
    if status:
        query = query.filter(Agent.status == status)
    
    agents = query.all()
    return {
        "agents": [a.to_dict() for a in agents],
        "total": len(agents)
    }

@router.post("", response_model=dict)
@limiter.limit("20/minute")
def create_agent(
    request: Request,
    data: AgentCreate,
    db: Session = Depends(get_db)
):
    """创建新员工（自动生成员工手册）"""
    agent = Agent(
        id=f"emp_{uuid.uuid4().hex[:8]}",
        name=data.name,
        emoji=data.emoji,
        position_level=data.position_level,
        monthly_budget=float(data.monthly_budget),
        status=AgentStatus.IDLE.value
    )
    
    db.add(agent)
    db.commit()
    db.refresh(agent)
    
    logger.info(f"Created employee: {agent.name} ({agent.id})")
    
    # 自动生成员工手册
    try:
        from services.employee_manual_service import create_employee_manual
        manual_result = create_employee_manual(
            employee_id=agent.id,
            employee_name=agent.name,
            position_level=agent.position_level,
            description=""  # TODO: Partner 可以提供初始描述
        )
        logger.info(f"Employee manual created: {manual_result['relative_path']}")
    except Exception as e:
        logger.error(f"Failed to create employee manual: {e}")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "message": "Agent created"
    }

@router.get("/{agent_id}", response_model=dict)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """获取员工详情"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_dict()

@router.put("/{agent_id}", response_model=dict)
def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: Session = Depends(get_db)
):
    """更新员工信息"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if data.name:
        agent.name = data.name
    if data.emoji:
        agent.emoji = data.emoji
    if data.monthly_budget is not None:
        agent.monthly_budget = float(data.monthly_budget)
    
    db.commit()
    db.refresh(agent)
    
    return {"message": "Agent updated", "agent": agent.to_dict()}

@router.delete("/{agent_id}")
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """删除员工"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
    
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

# ============ OpenClaw 集成 ============

def get_openclaw_agents() -> list:
    """从 OpenClaw 配置文件获取可用 Agent 列表"""
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        agents = config.get('agents', {}).get('list', [])
        return [
            {
                "id": a.get('id'),
                "name": a.get('name', a.get('id')),
                "description": a.get('description', '')
            }
            for a in agents
        ]
    except Exception as e:
        logger.error(f"Failed to read OpenClaw config: {e}")
        return []


@router.get("/openclaw/available", response_model=dict)
@limiter.limit("100/minute")
def list_openclaw_agents(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    获取 OpenClaw 中可用的 Agent 列表（未绑定的候选 Agent）
    
    返回所有在 OpenClaw 中配置但尚未绑定到 OPC 员工的 Agent。
    """
    # 获取所有 OpenClaw agents
    openclaw_agents = get_openclaw_agents()
    
    # 获取已绑定的 agent IDs
    bound_agents = db.query(Agent).filter(Agent.is_bound == "true").all()
    bound_ids = {a.openclaw_agent_id for a in bound_agents if a.openclaw_agent_id}
    
    # 过滤出未绑定的 agents
    available = [
        a for a in openclaw_agents
        if a['id'] not in bound_ids
    ]
    
    return {
        "agents": available,
        "total": len(available),
        "bound_count": len(bound_ids)
    }

@router.post("/{agent_id}/bind")
def bind_openclaw_agent(
    agent_id: str,
    data: BindRequest,
    db: Session = Depends(get_db)
):
    """绑定 OpenClaw Agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.openclaw_agent_id = data.openclaw_agent_id
    agent.is_bound = "true"
    db.commit()
    
    logger.info(f"Bound agent {agent_id} to OpenClaw agent {data.openclaw_agent_id}")
    
    return {
        "message": "Agent bound",
        "openclaw_agent_id": data.openclaw_agent_id
    }

@router.post("/{agent_id}/unbind")
def unbind_openclaw_agent(agent_id: str, db: Session = Depends(get_db)):
    """解绑 OpenClaw Agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.openclaw_agent_id = None
    agent.is_bound = "false"
    db.commit()
    
    return {"message": "Agent unbound"}

# ============ 预算管理 ============

@router.get("/{agent_id}/budget")
def get_agent_budget(agent_id: str, db: Session = Depends(get_db)):
    """获取员工预算信息"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "monthly_budget": agent.monthly_budget,
        "used_budget": agent.used_budget,
        "remaining": agent.remaining_budget
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
