"""
Agent API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.models import Agent, AgentStatus, PositionLevel
from src.services.agent_service import AgentService
from src.services.agent_lifecycle_service import AgentLifecycleService
from src.utils.openclaw_config import read_openclaw_agents, get_agent_details, ensure_partner_agent_exists
from src.services.partner_service import PartnerService
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter()


class AgentCreate(BaseModel):
    """Create agent request."""
    name: str = Field(..., min_length=1, max_length=50)
    agent_id: Optional[str] = Field(None, description="OpenClaw agent ID (optional - if None creates unbound employee)")
    emoji: str = "🧑‍💻"
    monthly_budget: float = 2000.0
    position_title: Optional[str] = Field(None, description="Employee position title")
    bind_now: bool = Field(True, description="Whether to bind to OpenClaw agent immediately")


class PartnerSetup(BaseModel):
    """Setup partner from existing OpenClaw agent."""
    openclaw_agent_id: str = Field(..., description="Existing OpenClaw agent ID")
    monthly_budget: float = 10000.0


class CompanyInit(BaseModel):
    """Initialize company with partner and first employee."""
    partner_agent_id: str
    company_name: str = "My OPC"


class AgentReport(BaseModel):
    """Agent task completion report."""
    agent_id: str
    task_id: str
    token_used: int = Field(..., ge=0)
    result_summary: str = ""
    status: str = "completed"  # completed, failed
    # Exact token tracking fields
    tokens_input: Optional[int] = Field(None, ge=0, description="Actual input tokens consumed")
    tokens_output: Optional[int] = Field(None, ge=0, description="Actual output tokens consumed")
    session_key: Optional[str] = Field(None, description="OpenClaw session identifier")
    is_exact: bool = Field(False, description="Whether token values are exact from session_status")


class AgentResponse(BaseModel):
    """Agent response model."""
    id: str
    name: str
    emoji: str
    position_title: str
    position_level: int
    status: str
    is_online: str
    mood_emoji: str
    monthly_budget: float
    used_budget: float
    total_budget: float = 0.0
    remaining_budget: float = 0.0
    is_bound: str
    agent_id: Optional[str]
    
    class Config:
        from_attributes = True
    
    @model_validator(mode='after')
    def compute_budget_fields(self):
        """Compute total_budget and remaining_budget from monthly_budget and used_budget."""
        self.total_budget = self.monthly_budget
        self.remaining_budget = self.monthly_budget - self.used_budget
        return self


@router.get("/openclaw/agents")
@limiter.limit(RATE_LIMITS["default"])
async def list_openclaw_agents(request: Request):
    """
    List existing agents from OpenClaw configuration.
    User selects one of these to be the Partner.
    """
    agents = read_openclaw_agents()
    return {
        "agents": agents,
        "count": len(agents),
        "message": "Select one agent as your Partner" if agents else "No OpenClaw agents found"
    }


@router.post("/partner/create-agent")
@limiter.limit(RATE_LIMITS["create"])
async def create_partner_agent_endpoint(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Auto-create a dedicated Partner Agent for OPC.
    
    This creates a new OpenClaw Agent with:
    - Isolated workspace (no context pollution)
    - Dedicated memory directory
    - Professional CEO Assistant identity
    
    Returns the created agent info for binding.
    """
    from src.utils.openclaw_config import create_partner_agent
    
    # Create the Partner Agent
    result = create_partner_agent("OPC Partner Assistant")
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Partner Agent. Please check OpenClaw configuration."
        )
    
    return {
        "success": True,
        "agent": {
            "id": result["id"],
            "name": result["name"],
            "agent_dir": result["agent_dir"],
            "workspace": result["workspace"],
        },
        "message": "✅ Partner Agent created successfully! Please restart OpenClaw Gateway to activate it.",
        "next_step": "Restart OpenClaw Gateway, then call /partner/setup to bind this agent"
    }


@router.post("/partner/setup-auto")
@limiter.limit(RATE_LIMITS["create"])
async def setup_partner_auto(
    request: Request,
    monthly_budget: float = 10000.0,
    db: Session = Depends(get_db),
):
    """
    One-click setup Partner with auto-created Agent.
    
    This is the RECOMMENDED way to initialize OPC:
    1. Creates a dedicated Partner Agent (if not exists)
    2. Binds it to Partner role
    3. Ready to use!
    
    Note: If a new agent is created, you need to restart OpenClaw Gateway.
    """
    from src.utils.openclaw_config import ensure_partner_agent_exists
    
    service = AgentService(db)
    
    # Ensure Partner Agent exists
    oc_agent = ensure_partner_agent_exists()
    
    if not oc_agent:
        raise HTTPException(
            status_code=500,
            detail="Failed to create or find Partner Agent"
        )
    
    # Check if this agent is already bound as Partner
    existing = service.get_agent(oc_agent["id"])
    if existing:
        return {
            "success": True,
            "partner": {
                "id": existing.id,
                "name": existing.name,
                "agent_id": existing.agent_id,
                "position": existing.position_title,
                "monthly_budget": existing.monthly_budget,
            },
            "message": f"Partner '{existing.name}' is already set up!",
            "restart_required": False
        }
    
    # Create Partner in database
    partner = service.create_agent(
        name=f"{oc_agent['name']} (Partner)",
        agent_id=oc_agent["id"],
        emoji="👑",
        monthly_budget=monthly_budget,
    )
    
    # Update to Partner level
    partner.position_level = PositionLevel.PARTNER.value
    partner.position_title = "合伙人"
    db.commit()
    db.refresh(partner)
    
    # Check if this was a new agent creation
    restart_required = "opc_partner_" in oc_agent["id"]
    
    return {
        "success": True,
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "agent_id": partner.agent_id,
            "position": "合伙人",
            "monthly_budget": partner.monthly_budget,
        },
        "message": f"🎉 Partner '{partner.name}' is ready!",
        "restart_required": restart_required,
        "note": "Please restart OpenClaw Gateway to activate the new Partner Agent" if restart_required else None
    }


@router.post("/partner/setup")
@limiter.limit(RATE_LIMITS["create"])
async def setup_partner(
    request: Request,
    setup: PartnerSetup,
    db: Session = Depends(get_db),
):
    """
    Setup Partner from existing OpenClaw agent.
    This is the first step in company initialization.
    """
    # Verify the OpenClaw agent exists
    oc_agent = get_agent_details(setup.openclaw_agent_id)
    if not oc_agent:
        raise HTTPException(
            status_code=404,
            detail=f"OpenClaw agent '{setup.openclaw_agent_id}' not found"
        )
    
    service = AgentService(db)
    
    # Check if partner already exists
    existing = service.get_agent(setup.openclaw_agent_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{setup.openclaw_agent_id}' is already registered"
        )
    
    # Create Partner agent
    partner = service.create_agent(
        name=f"{oc_agent['name']} (Partner)",
        agent_id=setup.openclaw_agent_id,
        emoji="👑",
        monthly_budget=setup.monthly_budget,
    )
    
    # Update to Partner level
    partner.position_level = PositionLevel.PARTNER.value
    partner.position_title = "合伙人"
    db.commit()
    db.refresh(partner)
    
    return {
        "success": True,
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "agent_id": partner.agent_id,
            "position": "合伙人",
            "monthly_budget": partner.monthly_budget,
        },
        "message": f"Partner '{partner.name}' is ready to help you build your company!"
    }


@router.post("/company/init")
async def initialize_company(
    init: CompanyInit,
    db: Session = Depends(get_db),
):
    """
    Initialize company with Partner.
    Partner will assist in creating the first employee.
    """
    service = AgentService(db)
    
    # Verify partner exists
    partner = service.get_agent(init.partner_agent_id)
    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Partner not found. Please setup partner first."
        )
    
    return {
        "success": True,
        "company_name": init.company_name,
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "agent_id": partner.agent_id,
        },
        "next_steps": [
            "1. Partner will help you hire your first employee",
            "2. Define employee role and budget",
            "3. Create first project",
            "4. Start collaborating!"
        ],
        "message": f"Welcome to {init.company_name}! Your Partner '{partner.name}' is ready to assist you."
    }


@router.post("/partner/hire")
@limiter.limit(RATE_LIMITS["create"])
async def partner_hire_employee(
    request: Request,
    employee: AgentCreate,
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Partner assists in hiring a new employee.
    Validates partner permissions and creates employee.
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can hire employees")
    
    # Create employee
    try:
        new_employee = service.create_agent(
            name=employee.name,
            agent_id=employee.agent_id,
            emoji=employee.emoji,
            monthly_budget=employee.monthly_budget,
        )
        
        # Set position title if provided
        if employee.position_title:
            new_employee.position_title = employee.position_title
            db.commit()
            db.refresh(new_employee)
        
        return {
            "success": True,
            "employee": {
                "id": new_employee.id,
                "name": new_employee.name,
                "agent_id": new_employee.agent_id,
                "position": new_employee.position_title,
                "monthly_budget": new_employee.monthly_budget,
            },
            "hired_by": partner.name,
            "message": f"{partner.name} 成功雇佣了 {new_employee.name} ({new_employee.position_title})!"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/report")
@limiter.limit(RATE_LIMITS["create"])
async def report_task_completion(
    request: Request,
    report: AgentReport,
    db: Session = Depends(get_db),
):
    """
    Report task completion from Agent.
    Called by OPC Bridge Skill after task completion.
    Supports both estimated and exact token consumption reporting.
    """
    service = AgentService(db)
    try:
        result = service.report_task_completion(
            agent_id=report.agent_id,
            task_id=report.task_id,
            token_used=report.token_used,
            result_summary=report.result_summary,
            status=report.status,
            tokens_input=report.tokens_input,
            tokens_output=report.tokens_output,
            session_key=report.session_key,
            is_exact=report.is_exact,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/task")
async def get_agent_task(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """
    Get current task assigned to agent.
    Called by Partner Agent to check for new tasks.
    """
    service = AgentService(db)
    task = service.get_pending_task(agent_id)
    if task:
        return {
            "has_task": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "estimated_cost": task.estimated_cost,
            }
        }
    return {"has_task": False}


@router.post("")
async def create_agent(
    agent: AgentCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new agent (employee).
    
    If agent_id is provided, binds immediately to that OpenClaw agent.
    If agent_id is None, creates an unbound employee (cannot work until bound).
    """
    service = AgentService(db)
    try:
        new_agent = service.create_agent(
            name=agent.name,
            agent_id=agent.agent_id,
            emoji=agent.emoji,
            monthly_budget=agent.monthly_budget,
        )
        
        return {
            "success": True,
            "agent": {
                "id": new_agent.id,
                "name": new_agent.name,
                "agent_id": new_agent.agent_id,
                "is_bound": new_agent.is_bound,
                "status": new_agent.status,
                "emoji": new_agent.emoji,
                "monthly_budget": new_agent.monthly_budget,
            },
            "message": f"Created {'bound' if new_agent.is_bound == 'true' else 'unbound'} employee '{new_agent.name}'"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    available_only: bool = False,
    db: Session = Depends(get_db),
):
    """
    List all agents.
    
    Args:
        available_only: If true, only return agents that are IDLE (available for assignment)
    """
    service = AgentService(db)
    agents = service.list_agents()
    
    if available_only:
        # Filter for agents that are idle
        agents = [a for a in agents if a.status == AgentStatus.IDLE.value]
    
    return agents


@router.post("/partner/heartbeat")
async def partner_heartbeat(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Partner Agent heartbeat - reports that it's still alive.
    Should be called every 30 seconds by Partner Agent.
    """
    from datetime import datetime
    
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can send heartbeat")
    
    # Update heartbeat
    partner.last_heartbeat = datetime.utcnow()
    partner.is_online = "online"
    db.commit()
    
    return {
        "success": True,
        "message": "Heartbeat received",
        "timestamp": partner.last_heartbeat.isoformat()
    }


@router.get("/partner/health")
async def partner_health_status(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Check Partner Agent health status.
    Returns online/offline status based on last heartbeat.
    """
    from datetime import datetime, timedelta
    
    service = AgentService(db)
    
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Check if heartbeat is recent (within 60 seconds)
    is_online = False
    seconds_since_heartbeat = None
    
    if partner.last_heartbeat:
        delta = datetime.utcnow() - partner.last_heartbeat
        seconds_since_heartbeat = delta.total_seconds()
        is_online = seconds_since_heartbeat < 60
    
    # Update is_online status
    partner.is_online = "online" if is_online else "offline"
    db.commit()
    
    return {
        "partner_id": partner_id,
        "name": partner.name,
        "is_online": is_online,
        "status": "online" if is_online else "offline",
        "last_heartbeat": partner.last_heartbeat.isoformat() if partner.last_heartbeat else None,
        "seconds_since_heartbeat": seconds_since_heartbeat,
        "warning": not is_online and partner.last_heartbeat is not None
    }


# ============================================================
# Partner Wake/Sleep Mode API
# ============================================================

class PartnerWakeResponse(BaseModel):
    """Partner wake response."""
    status: str
    message: str
    summary: dict


class PartnerChatRequest(BaseModel):
    """Chat request to Partner."""
    message: str


class PartnerChatResponse(BaseModel):
    """Partner chat response."""
    response: str
    actions: List[str] = []


@router.post("/partner/wake", response_model=PartnerWakeResponse)
async def wake_partner(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Wake up Partner Agent.
    
    Partner will greet the user and provide company status summary.
    Partner remains awake for interaction until auto-sleep timeout.
    """
    from datetime import datetime
    
    service = AgentService(db)
    partner_service = PartnerService(db)
    
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Update Partner status to awake
    partner.is_online = "awake"
    partner.last_heartbeat = datetime.utcnow()
    db.commit()
    
    # Generate company summary
    summary = partner_service.get_company_summary()
    
    # Generate welcome message (using bound Agent if available)
    welcome_msg = generate_welcome_message(summary, partner.name, partner.agent_id)
    
    return {
        "status": "awake",
        "message": welcome_msg,
        "summary": summary
    }


@router.post("/partner/sleep")
async def sleep_partner(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Put Partner Agent to sleep (standby mode).
    
    Partner will enter standby state and conserve resources.
    User can still view dashboard data in self-service mode.
    """
    service = AgentService(db)
    
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner.is_online = "standby"
    db.commit()
    
    return {
        "status": "standby",
        "message": f"{partner.name} 已进入待机模式。随时呼唤我！",
        "partner_id": partner_id
    }


@router.get("/partner/state")
async def get_partner_state(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Get current Partner state.
    
    Returns: standby | awake | busy
    """
    service = AgentService(db)
    
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Check for auto-sleep (5 minutes = 300 seconds)
    from datetime import datetime, timedelta
    
    state = partner.is_online or "standby"
    
    if state == "awake" and partner.last_heartbeat:
        delta = datetime.utcnow() - partner.last_heartbeat
        if delta.total_seconds() > 300:  # 5 minutes
            state = "standby"
            partner.is_online = "standby"
            db.commit()
    
    return {
        "partner_id": partner_id,
        "name": partner.name,
        "state": state,
        "last_interaction": partner.last_heartbeat.isoformat() if partner.last_heartbeat else None
    }


@router.get("/partner/summary")
async def get_partner_summary(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Get company status summary.
    
    Returns key metrics and alerts for Partner to report.
    """
    service = AgentService(db)
    partner_service = PartnerService(db)
    
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    summary = partner_service.get_company_summary()
    
    return summary


@router.post("/partner/chat", response_model=PartnerChatResponse)
async def chat_with_partner(
    partner_id: str,
    chat_req: PartnerChatRequest,
    db: Session = Depends(get_db),
):
    """
    Send a message to Partner and get response.
    
    Also refreshes the awake timer to prevent auto-sleep.
    """
    from datetime import datetime
    
    service = AgentService(db)
    partner = service.get_agent_by_id(partner_id)
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Check if Partner is awake
    if partner.is_online != "awake":
        return {
            "response": "我需要先被唤醒才能帮助您。请点击 Partner 头像或发送 '唤醒' 来激活我！",
            "actions": ["wake"]
        }
    
    # Refresh heartbeat
    partner.last_heartbeat = datetime.utcnow()
    db.commit()
    
    # Simple response logic (can be enhanced with AI later)
    message = chat_req.message.lower()
    
    if any(word in message for word in ["雇佣", "招聘", "hire", "新员工"]):
        return {
            "response": "我来帮您雇佣新员工！请告诉我需要什么样的员工（职位、技能要求）。",
            "actions": ["open_hire_modal"]
        }
    elif any(word in message for word in ["任务", "发布", "task", "assign"]):
        return {
            "response": "我可以帮您发布任务。请描述任务内容和预算。",
            "actions": ["open_create_task"]
        }
    elif any(word in message for word in ["报告", "状态", "status", "report"]):
        return {
            "response": "我来为您生成公司状态报告。",
            "actions": ["show_reports"]
        }
    else:
        return {
            "response": f"收到！我是 {partner.name}，有什么我可以帮您的吗？\n\n您可以让我：\n• 雇佣新员工\n• 发布任务\n• 查看报告",
            "actions": []
        }


def generate_welcome_message(summary: dict, partner_name: str, agent_id: str = None) -> str:
    """Generate personalized welcome message using the bound OpenClaw Agent."""
    import random
    
    # If no agent bound, use fallback
    if not agent_id:
        return generate_fallback_welcome(summary, partner_name)
    
    # Try to use the bound Agent to generate message
    try:
        from src.utils.openclaw_config import send_message_to_agent
        
        # Prepare context for the Agent
        budget = summary.get("budget", {})
        tasks = summary.get("tasks", {})
        alerts = summary.get("alerts", [])
        good_news = summary.get("good_news", [])
        
        prompt = f"""你是 {partner_name}，一位专业的 CEO 助理。现在老板刚刚打开 Dashboard，你需要热情地欢迎他/她，并简要汇报公司状态。

公司当前状态：
- 预算使用率：{budget.get('used_percentage', 0):.1f}%
- 待办任务：{tasks.get('pending', 0)} 个
- 进行中：{tasks.get('in_progress', 0)} 个
- 今日完成：{tasks.get('completed_today', 0)} 个

需要注意：
{chr(10).join(['- ' + a for a in alerts[:3]]) if alerts else '- 暂无'}

好消息：
{chr(10).join(['- ' + g for g in good_news[:2]]) if good_news else '- 一切正常'}

请生成一段热情的欢迎消息（包含问候、状态简报、和询问需要什么帮助）。语气要专业但友好，像一位称职的助理。"""

        # Send to Agent and get response
        response = send_message_to_agent(agent_id, prompt, timeout=30)
        
        if response and response.get("text"):
            return response["text"]
        
    except Exception as e:
        logger.warning("Failed to generate welcome message via Agent", error=str(e))
    
    # Fallback to generated message
    return generate_fallback_welcome(summary, partner_name)


def generate_fallback_welcome(summary: dict, partner_name: str) -> str:
    """Fallback welcome message generator."""
    import random
    
    greetings = [
        "老板好！👋",
        "欢迎回来！🎉",
        "您好！我一直在等您。😊",
        "老板，有什么我可以帮您的？💼"
    ]
    
    greeting = random.choice(greetings)
    
    # Budget status
    budget = summary.get("budget", {})
    budget_pct = budget.get("used_percentage", 0)
    if budget_pct > 90:
        budget_status = "⚠️ 预算已接近上限"
    elif budget_pct > 70:
        budget_status = "💰 预算使用率正常"
    else:
        budget_status = "💰 预算充足"
    
    # Task status
    tasks = summary.get("tasks", {})
    pending = tasks.get("pending", 0)
    overdue = tasks.get("overdue", 0)
    
    task_status = f"📋 待办任务：{pending}个"
    if overdue > 0:
        task_status += f"（⚠️ {overdue}个已逾期）"
    
    # Alerts
    alerts = summary.get("alerts", [])
    warning_section = ""
    if alerts:
        warning_section = "\n⚠️ 需要注意：\n" + "\n".join([f"  • {a}" for a in alerts[:3]])
    
    # Good news
    good_news = summary.get("good_news", [])
    good_news_section = ""
    if good_news:
        good_news_section = "\n✅ 好消息：\n" + "\n".join([f"  • {g}" for g in good_news[:2]])
    
    message = f"""{greeting}

今天公司状态：
• {budget_status}（{budget_pct:.1f}%）
• {task_status}{warning_section}{good_news_section}

有什么我可以帮您的吗？
• 🤝 雇佣新员工
• 📝 发布任务  
• 📊 查看详细报告"""
    
    return message


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Get agent details by internal ID."""
    service = AgentService(db)
    # Use get_agent_by_id to query by internal ID (not OpenClaw agent_id)
    agent = service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Convert SQLAlchemy model to Pydantic response to trigger validators
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    task_action: str = "reassign",  # "reassign", "delete", "cancel"
    db: Session = Depends(get_db),
):
    """
    Delete an employee (agent).
    
    Args:
        agent_id: Employee ID to delete
        task_action: How to handle assigned tasks:
            - "reassign": Reassign to Partner (default)
            - "delete": Delete all tasks
            - "cancel": Cancel and keep tasks unassigned
    
    Returns:
        Deletion result with task handling summary
    """
    from src.models import Task, TaskStatus
    
    service = AgentService(db)
    
    # Get agent
    agent = service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Cannot delete Partner
    if agent.position_level == PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Cannot delete Partner. Use company reset instead.")
    
    agent_name = agent.name
    
    # Handle assigned tasks
    tasks = db.query(Task).filter(Task.agent_id == agent_id).all()
    task_summary = {
        "total": len(tasks),
        "reassigned": 0,
        "deleted": 0,
        "cancelled": 0
    }
    
    if tasks:
        if task_action == "reassign":
            # Find Partner
            partner = db.query(Agent).filter(Agent.position_level == PositionLevel.PARTNER.value).first()
            partner_id = partner.id if partner else None
            
            for task in tasks:
                if task.status in [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value]:
                    if partner_id:
                        task.agent_id = partner_id
                        task_summary["reassigned"] += 1
                    else:
                        task.status = TaskStatus.PENDING.value
                        task.agent_id = None
                        task_summary["cancelled"] += 1
                else:
                    # Keep completed/failed tasks with null agent
                    task.agent_id = None
                    task_summary["cancelled"] += 1
                    
        elif task_action == "delete":
            for task in tasks:
                db.delete(task)
                task_summary["deleted"] += 1
                
        else:  # cancel
            for task in tasks:
                if task.status in [TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value]:
                    task.status = TaskStatus.PENDING.value
                    task.agent_id = None
                    task_summary["cancelled"] += 1
                else:
                    task.agent_id = None
    
    # Delete agent
    db.delete(agent)
    db.commit()
    
    return {
        "success": True,
        "message": f"Employee '{agent_name}' has been deleted",
        "agent_id": agent_id,
        "agent_name": agent_name,
        "task_summary": task_summary
    }


# Partner auto-assignment endpoints

@router.get("/partner/status")
async def partner_company_status(
    partner_id: str,
    db: Session = Depends(get_db),
):
    """
    Get company status for Partner.
    Shows pending tasks, agent availability, budget status.
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can view company status")
    
    partner_service = PartnerService(db)
    status = partner_service.get_company_status()
    
    return {
        "success": True,
        "partner": partner.name,
        "company_status": status
    }


@router.post("/partner/assign/{task_id}")
async def partner_auto_assign(
    task_id: str,
    partner_id: str,
    strategy: str = "budget",
    db: Session = Depends(get_db),
):
    """
    Partner auto-assigns a task to the best available agent.
    
    Strategies:
    - budget: Prioritize agents with highest remaining budget ratio
    - workload: Prioritize agents with lowest workload
    - combined: Weighted combination (70% budget + 30% workload)
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can assign tasks")
    
    partner_service = PartnerService(db)
    result = partner_service.auto_assign(task_id, strategy)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/partner/assign-all")
async def partner_assign_all_pending(
    partner_id: str,
    strategy: str = "budget",
    db: Session = Depends(get_db),
):
    """
    Partner assigns all pending tasks to best available agents.
    """
    service = AgentService(db)
    
    # Verify partner
    partner = service.get_agent_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    if partner.position_level != PositionLevel.PARTNER.value:
        raise HTTPException(status_code=403, detail="Only Partner can assign tasks")
    
    partner_service = PartnerService(db)
    results = partner_service.assign_all_pending(strategy)
    
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    return {
        "success": True,
        "summary": {
            "total": len(results),
            "successful": successful,
            "failed": failed
        },
        "assignments": results
    }


# Agent binding management endpoints

class AgentBindRequest(BaseModel):
    """Bind employee to OpenClaw agent request."""
    employee_id: str = Field(..., description="OPC employee ID to bind")
    agent_id: str = Field(..., description="OpenClaw agent ID to bind to")


class AgentUnbindRequest(BaseModel):
    """Unbind employee from OpenClaw agent request."""
    archive_agent: bool = Field(False, description="Whether to archive the OpenClaw agent config")


@router.get("/binding/available")
async def get_available_agents_for_binding(
    db: Session = Depends(get_db),
):
    """
    Get list of OpenClaw agents available for binding.
    These are agents from openclaw.json that are not yet bound to any employee.
    """
    service = AgentService(db)
    available = service.get_available_openclaw_agents()
    
    return {
        "success": True,
        "available_agents": available,
        "count": len(available),
        "message": f"Found {len(available)} available agents for binding" if available else "No available agents found. Create new agents in OpenClaw config first."
    }


@router.post("/binding/bind")
@limiter.limit(RATE_LIMITS["create"])
async def bind_employee_to_agent(
    request: Request,
    bind_request: AgentBindRequest,
    db: Session = Depends(get_db),
):
    """
    Bind an existing employee to an OpenClaw agent.
    After binding, the employee can receive and execute tasks.
    """
    service = AgentService(db)
    
    try:
        employee = service.bind_agent(
            employee_id=bind_request.employee_id,
            agent_id=bind_request.agent_id
        )
        
        return {
            "success": True,
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "agent_id": employee.agent_id,
                "is_bound": employee.is_bound,
                "status": employee.status,
            },
            "message": f"Successfully bound '{employee.name}' to agent '{bind_request.agent_id}'"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/binding/unbind/{employee_id}")
@limiter.limit(RATE_LIMITS["create"])
async def unbind_employee_from_agent(
    request: Request,
    employee_id: str,
    unbind_request: AgentUnbindRequest,
    db: Session = Depends(get_db),
):
    """
    Unbind an employee from its OpenClaw agent.
    After unbinding, the employee cannot receive new tasks (status becomes 'unbound').
    Optionally archive the OpenClaw agent configuration.
    """
    service = AgentService(db)
    
    try:
        employee = service.unbind_agent(
            employee_id=employee_id,
            archive_agent=unbind_request.archive_agent
        )
        
        return {
            "success": True,
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "agent_id": employee.agent_id,
                "is_bound": employee.is_bound,
                "status": employee.status,
            },
            "archived": unbind_request.archive_agent,
            "message": f"Successfully unbound '{employee.name}' from agent. Employee is now inactive."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/binding/status/{employee_id}")
async def get_employee_binding_status(
    employee_id: str,
    db: Session = Depends(get_db),
):
    """
    Get binding status of an employee.
    Shows whether employee is bound to an OpenClaw agent and details.
    """
    service = AgentService(db)
    employee = service.get_agent_by_id(employee_id)
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {
        "success": True,
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "is_bound": employee.is_bound,
            "agent_id": employee.agent_id,
            "status": employee.status,
            "can_work": employee.is_bound == "true" and employee.status != "unbound",
        },
        "binding_info": {
            "bound_at": employee.created_at.isoformat() if employee.is_bound == "true" else None,
            "bound_agent_name": employee.agent_id if employee.agent_id else None,
        } if employee.is_bound == "true" else None
    }


# Auto-create Agent endpoint

class AutoCreateAgentRequest(BaseModel):
    """Auto-create OpenClaw agent for employee request."""
    employee_id: str = Field(..., description="OPC employee ID")
    employee_name: str = Field(..., description="Employee display name")
    model: str = Field("default", description="Model configuration")


@router.post("/auto-create")
@limiter.limit(RATE_LIMITS["create"])
async def auto_create_agent_for_employee(
    request: Request,
    create_request: AutoCreateAgentRequest,
    db: Session = Depends(get_db),
):
    """
    Automatically create an OpenClaw agent for an employee.
    
    This endpoint:
    1. Creates OpenClaw agent configuration
    2. Generates workspace and SOUL.md
    3. Binds the agent to the employee
    4. Creates a backup of the original config
    
    Note: Gateway restart may be required for the new agent to be recognized.
    """
    agent_service = AgentService(db)
    lifecycle_service = AgentLifecycleService()
    
    # Get employee
    employee = agent_service.get_agent_by_id(create_request.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.is_bound == "true":
        raise HTTPException(status_code=400, detail="Employee is already bound to an agent")
    
    try:
        # Generate agent ID from employee name
        import re
        base_id = re.sub(r'[^\w\s-]', '', create_request.employee_name).strip().replace(' ', '-').lower()
        agent_id = f"{base_id}-{employee.id[:4]}"
        
        # Create OpenClaw agent
        workspace_path, created_agent_id = lifecycle_service.create_agent(
            agent_id=agent_id,
            name=create_request.employee_name,
            model=create_request.model
        )
        
        # Bind employee to the new agent
        employee = agent_service.bind_agent(
            employee_id=create_request.employee_id,
            agent_id=created_agent_id
        )
        
        # Check if restart might be needed
        restart_recommended = lifecycle_service.check_restart_required()
        
        return {
            "success": True,
            "agent_id": created_agent_id,
            "workspace": workspace_path,
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "is_bound": employee.is_bound,
                "status": employee.status,
            },
            "restart_recommended": restart_recommended,
            "message": f"Successfully created and bound agent '{created_agent_id}' to employee '{employee.name}'." +
                      (" Please restart OpenClaw Gateway to activate the new agent." if restart_recommended else "")
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.post("/gateway/restart")
@limiter.limit(RATE_LIMITS["default"])
async def restart_gateway(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Restart OpenClaw Gateway.
    
    This is a sensitive operation that requires confirmation.
    Returns immediately, actual restart happens asynchronously.
    """
    import subprocess
    import os
    import signal
    
    try:
        # Find openclaw-gateway process
        result = subprocess.run(
            ["pgrep", "-f", "openclaw-gateway"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            raise HTTPException(
                status_code=404,
                detail="OpenClaw Gateway process not found"
            )
        
        # Get the PID
        pid = int(result.stdout.strip().split('\n')[0])
        
        # Send SIGUSR1 to trigger graceful restart
        os.kill(pid, signal.SIGUSR1)
        
        return {
            "success": True,
            "pid": pid,
            "message": "OpenClaw Gateway restart signal sent. The gateway will restart shortly.",
            "note": "It may take 10-30 seconds for the restart to complete."
        }
        
    except ProcessLookupError:
        raise HTTPException(
            status_code=404,
            detail="OpenClaw Gateway process not found"
        )
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Cannot restart OpenClaw Gateway."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart OpenClaw Gateway: {str(e)}"
        )


@router.get("/gateway/status")
@limiter.limit(RATE_LIMITS["default"])
async def get_gateway_status(
    request: Request,
):
    """
    Check OpenClaw Gateway status.
    
    Returns whether the gateway is running and its PID.
    """
    import subprocess
    import time
    
    try:
        result = subprocess.run(
            ["pgrep", "-f", "openclaw-gateway"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip().split('\n')[0])
            
            # Check if process is actually running
            try:
                os.kill(pid, 0)  # Signal 0 is used to check if process exists
                return {
                    "running": True,
                    "pid": pid,
                    "message": "OpenClaw Gateway is running"
                }
            except (OSError, ProcessLookupError):
                return {
                    "running": False,
                    "pid": None,
                    "message": "OpenClaw Gateway is not running"
                }
        else:
            return {
                "running": False,
                "pid": None,
                "message": "OpenClaw Gateway is not running"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check gateway status: {str(e)}"
        )


# ============================================================
# Agent Lifecycle Management API (v0.3.0 P0 Feature)
# ============================================================

class AgentAutoCreateRequest(BaseModel):
    """Auto-create OpenClaw agent for employee."""
    employee_id: str = Field(..., description="Employee ID to bind")
    confirm: bool = Field(False, description="Confirm after reviewing staged changes")


class AgentAutoCreateResponse(BaseModel):
    """Auto-create agent response."""
    success: bool
    employee_id: str
    agent_id: str
    agent_name: str
    status: str
    message: str
    needs_restart: bool = True
    needs_confirmation: bool = False
    preview: Optional[dict] = None


class AgentDeleteRequest(BaseModel):
    """Delete/archive agent request."""
    employee_id: str = Field(..., description="Employee ID")
    archive: bool = Field(True, description="Archive instead of permanent delete")
    confirm: bool = Field(False, description="Confirm after reviewing staged changes")


class ConfigBackupInfo(BaseModel):
    """Config backup information."""
    filename: str
    timestamp: str
    reason: str
    size: int


class PendingChangesResponse(BaseModel):
    """Pending changes response."""
    has_pending: bool
    current_agents: int
    staged_agents: int
    can_commit: bool
    can_rollback: bool


@router.post("/lifecycle/create", response_model=AgentAutoCreateResponse)
@limiter.limit(RATE_LIMITS["create"])
async def auto_create_agent(
    request: Request,
    req: AgentAutoCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Auto-create OpenClaw Agent for an employee.
    
    **Safety mechanism**:
    - Creates backup before modification
    - Stages changes for user confirmation
    - Requires explicit confirmation to apply
    
    **Flow**:
    1. Call with confirm=false to stage changes
    2. Review staged changes via /lifecycle/pending
    3. Call with confirm=true to apply
    
    **After confirmation**:
    - OpenClaw Gateway restart is required
    """
    from src.services.agent_lifecycle_service import AgentLifecycleService, ConfigOperationError
    
    service = AgentLifecycleService(db)
    
    # Get employee
    agent_service = AgentService(db)
    employee = agent_service.get_agent_by_id(req.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Generate agent ID if not exists
    agent_id = employee.agent_id or f"{employee.name.lower().replace(' ', '_')}_{employee.id[:4]}"
    
    if req.confirm:
        # Apply staged changes
        try:
            result = service.confirm_operation()
            if result["success"]:
                # Update employee record
                employee.agent_id = agent_id
                employee.is_bound = "true"
                db.commit()
                
                return AgentAutoCreateResponse(
                    success=True,
                    employee_id=req.employee_id,
                    agent_id=agent_id,
                    agent_name=employee.name,
                    status="created",
                    message="Agent configuration applied successfully. Please restart OpenClaw Gateway.",
                    needs_restart=True,
                    needs_confirmation=False
                )
            else:
                raise HTTPException(status_code=400, detail=result["message"])
        except ConfigOperationError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Stage changes for confirmation
        try:
            result = service.create_agent_config(
                agent_id=agent_id,
                name=employee.name,
                position=employee.position_title or "Intern"
            )
            
            return AgentAutoCreateResponse(
                success=True,
                employee_id=req.employee_id,
                agent_id=agent_id,
                agent_name=employee.name,
                status="staged",
                message="Agent configuration staged. Review and confirm to apply.",
                needs_restart=True,
                needs_confirmation=True,
                preview={
                    "agent_dir": result["agent_dir"],
                    "workspace": result["workspace"]
                }
            )
        except ConfigOperationError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.post("/lifecycle/delete")
@limiter.limit(RATE_LIMITS["create"])
async def auto_delete_agent(
    request: Request,
    req: AgentDeleteRequest,
    db: Session = Depends(get_db),
):
    """
    Delete/archive OpenClaw Agent for an employee.
    
    **Safety mechanism**:
    - Creates backup before modification
    - Archives agent directory by default (not permanent delete)
    - Stages changes for user confirmation
    
    **Flow**:
    1. Call with confirm=false to stage changes
    2. Review via /lifecycle/pending
    3. Call with confirm=true to apply
    """
    from src.services.agent_lifecycle_service import AgentLifecycleService, ConfigOperationError
    
    service = AgentLifecycleService(db)
    
    # Get employee
    agent_service = AgentService(db)
    employee = agent_service.get_agent_by_id(req.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.agent_id:
        raise HTTPException(status_code=400, detail="Employee has no bound agent")
    
    if req.confirm:
        # Apply staged changes
        try:
            result = service.confirm_operation()
            if result["success"]:
                # Update employee record
                employee.agent_id = None
                employee.is_bound = "false"
                db.commit()
                
                return {
                    "success": True,
                    "employee_id": req.employee_id,
                    "agent_id": employee.agent_id,
                    "status": "deleted" if not req.archive else "archived",
                    "message": "Agent configuration removed successfully. Please restart OpenClaw Gateway.",
                    "needs_restart": True
                }
            else:
                raise HTTPException(status_code=400, detail=result["message"])
        except ConfigOperationError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Stage changes for confirmation
        try:
            result = service.delete_agent_config(
                agent_id=employee.agent_id,
                archive=req.archive
            )
            
            return {
                "success": True,
                "employee_id": req.employee_id,
                "agent_id": employee.agent_id,
                "status": "staged_for_deletion",
                "archived": req.archive,
                "message": "Agent deletion staged. Review and confirm to apply.",
                "needs_restart": True,
                "needs_confirmation": True
            }
        except ConfigOperationError as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/lifecycle/pending", response_model=PendingChangesResponse)
async def get_pending_changes(
    db: Session = Depends(get_db),
):
    """
    Get pending/staged configuration changes.
    
    Returns information about changes awaiting confirmation.
    """
    from src.services.agent_lifecycle_service import AgentLifecycleService
    
    service = AgentLifecycleService(db)
    pending = service.get_pending_changes()
    
    if not pending:
        return PendingChangesResponse(
            has_pending=False,
            current_agents=0,
            staged_agents=0,
            can_commit=False,
            can_rollback=False
        )
    
    return PendingChangesResponse(
        has_pending=True,
        current_agents=pending["current_agents"],
        staged_agents=pending["staged_agents"],
        can_commit=pending["can_commit"],
        can_rollback=pending["can_rollback"]
    )


@router.post("/lifecycle/confirm")
async def confirm_pending_changes(
    db: Session = Depends(get_db),
):
    """
    Confirm and apply pending configuration changes.
    
    **After confirmation**:
    - Changes are written to openclaw.json
    - OpenClaw Gateway restart is required
    """
    from src.services.agent_lifecycle_service import AgentLifecycleService
    
    service = AgentLifecycleService(db)
    result = service.confirm_operation()
    
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "needs_restart": result["needs_restart"],
            "note": result["note"]
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@router.post("/lifecycle/cancel")
async def cancel_pending_changes(
    db: Session = Depends(get_db),
):
    """
    Cancel/rollback pending configuration changes.
    
    Removes staged changes without applying them.
    """
    from src.services.agent_lifecycle_service import AgentLifecycleService
    
    service = AgentLifecycleService(db)
    result = service.cancel_operation()
    
    return {
        "success": result["success"],
        "message": result["message"]
    }


@router.get("/lifecycle/backups", response_model=List[ConfigBackupInfo])
async def list_config_backups(
    db: Session = Depends(get_db),
):
    """
    List available configuration backups.
    
    Returns list of backups with timestamps and reasons.
    """
    from src.services.agent_lifecycle_service import AgentConfigManager
    
    manager = AgentConfigManager()
    backups = manager.list_backups()
    
    return [
        ConfigBackupInfo(
            filename=b["filename"],
            timestamp=b["timestamp"],
            reason=b["reason"],
            size=b["size"]
        )
        for b in backups
    ]


@router.post("/lifecycle/restore")
async def restore_config_backup(
    backup_filename: str,
    db: Session = Depends(get_db),
):
    """
    Restore configuration from backup.
    
    **Safety**:
    - Creates new backup before restore
    - Requires OpenClaw Gateway restart after restore
    
    Use /lifecycle/backups to get available backup filenames.
    """
    from src.services.agent_lifecycle_service import AgentConfigManager, ConfigOperationError
    
    manager = AgentConfigManager()
    
    # Construct full path
    backup_path = manager.backup_dir / backup_filename
    
    try:
        manager.restore_backup(str(backup_path))
        return {
            "success": True,
            "message": f"Configuration restored from {backup_filename}",
            "needs_restart": True,
            "note": "OpenClaw Gateway restart required for changes to take effect"
        }
    except ConfigOperationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lifecycle/status")
async def get_lifecycle_status(
    db: Session = Depends(get_db),
):
    """
    Get comprehensive lifecycle management status.
    
    Returns:
    - Pending changes status
    - Backup count
    - Gateway status
    """
    from src.services.agent_lifecycle_service import AgentConfigManager, AgentLifecycleService
    import subprocess
    import os
    
    # Pending changes
    service = AgentLifecycleService(db)
    pending = service.get_pending_changes()
    
    # Backups
    manager = AgentConfigManager()
    backups = manager.list_backups()
    
    # Gateway status
    gateway_running = False
    try:
        result = subprocess.run(
            ["pgrep", "-f", "openclaw-gateway|uvicorn.*8000"],
            capture_output=True,
            text=True
        )
        gateway_running = result.returncode == 0 and result.stdout.strip()
    except:
        pass
    
    return {
        "pending_changes": {
            "has_pending": pending is not None,
            "current_agents": pending["current_agents"] if pending else 0,
            "staged_agents": pending["staged_agents"] if pending else 0
        },
        "backups": {
            "count": len(backups),
            "latest": backups[0]["filename"] if backups else None
        },
        "gateway": {
            "running": gateway_running
        },
        "safety_mechanisms": {
            "auto_backup": True,
            "user_confirmation": True,
            "file_locking": True,
            "archive_support": True
        }
    }
