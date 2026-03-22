"""
Task API routes.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.task_service import TaskService
from src.utils.logging_config import get_logger
from src.utils.rate_limit import limiter, RATE_LIMITS

router = APIRouter()
logger = get_logger(__name__)


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreate(BaseModel):
    """Create task request with validation."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str = Field(default="", max_length=2000, description="Task description")
    priority: Priority = Field(default=Priority.NORMAL, description="Task priority")
    estimated_cost: float = Field(..., gt=0, le=10000, description="Estimated OC coin cost")
    required_skills: List[str] = Field(default=[], max_length=10, description="Required skills")
    due_date: Optional[datetime] = Field(default=None, description="Task deadline")
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('estimated_cost')
    @classmethod
    def cost_reasonable(cls, v: float) -> float:
        """Ensure cost is reasonable."""
        if v > 5000:
            logger.warning("high_estimated_cost", cost=v, title=cls.title)
        return v


class TaskAssign(BaseModel):
    """Assign task request with validation."""
    agent_id: str = Field(..., min_length=1, max_length=50, description="Agent ID to assign")
    
    @field_validator('agent_id')
    @classmethod
    def agent_id_not_empty(cls, v: str) -> str:
        """Ensure agent_id is not empty."""
        if not v.strip():
            raise ValueError('Agent ID cannot be empty')
        return v.strip()


class TaskUpdate(BaseModel):
    """Update task request."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[Priority] = None
    status: Optional[TaskStatus] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip() if v else v


@router.post("")
@limiter.limit(RATE_LIMITS["create"])
async def create_task(
    request: Request,
    task: TaskCreate,
    db: Session = Depends(get_db),
):
    """Create a new task with validation."""
    logger.info("create_task", title=task.title, priority=task.priority)
    
    try:
        service = TaskService(db)
        new_task = service.create_task(
            title=task.title,
            description=task.description,
            priority=task.priority.value,
            estimated_cost=task.estimated_cost,
        )
        logger.info("task_created", task_id=new_task.id, title=task.title)
        return new_task
    except Exception as e:
        logger.error("create_task_failed", error=str(e), title=task.title)
        raise


@router.get("")
@limiter.limit(RATE_LIMITS["default"])
async def list_tasks(
    request: Request,
    status: Optional[TaskStatus] = None,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List tasks with optional filters."""
    service = TaskService(db)
    tasks = service.list_tasks(
        status=status.value if status else None,
        agent_id=agent_id
    )
    
    # Format response with assigned_to name
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "estimated_cost": task.estimated_cost,
            "actual_cost": task.actual_cost,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "assigned_to": None,
        }
        
        # Get agent name if assigned
        if task.agent_id:
            from src.models import Agent
            agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
            if agent:
                task_dict["assigned_to"] = agent.name
        
        result.append(task_dict)
    
    return result


@router.post("/{task_id}/assign")
@limiter.limit(RATE_LIMITS["create"])
async def assign_task(
    request: Request,
    task_id: str,
    assign: TaskAssign,
    db: Session = Depends(get_db),
):
    """
    Assign task to agent with validation.
    
    v0.4.0: 高预算任务需要先获得Partner审批
    """
    logger.info("assign_task", task_id=task_id, agent_id=assign.agent_id)
    
    # v0.4.0 - Check if approval is required
    from src.models import Task, Agent, ApprovalRequest, ApprovalStatus
    from src.services.approval_service import ApprovalService
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    approval_service = ApprovalService(db)
    
    if approval_service.requires_approval(task.estimated_cost, task_id):
        # Check if already approved
        existing_approval = db.query(ApprovalRequest).filter(
            ApprovalRequest.task_id == task_id,
            ApprovalRequest.status == ApprovalStatus.APPROVED.value
        ).first()
        
        if not existing_approval:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Task requires budget approval before assignment",
                    "task_id": task_id,
                    "estimated_cost": task.estimated_cost,
                    "threshold": 1000.0,
                    "action": "Create approval request first",
                }
            )
    
    service = TaskService(db)
    try:
        task = service.assign_task(task_id, assign.agent_id)
        logger.info("task_assigned", task_id=task_id, agent_id=assign.agent_id)
        return task
    except ValueError as e:
        logger.warning("assign_task_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}")
@limiter.limit(RATE_LIMITS["default"])
async def get_task(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get task details."""
    service = TaskService(db)
    task = service.get_task(task_id)
    if not task:
        logger.warning("task_not_found", task_id=task_id)
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}")
@limiter.limit(RATE_LIMITS["create"])
async def update_task(
    request: Request,
    task_id: str,
    update: TaskUpdate,
    db: Session = Depends(get_db),
):
    """Update task details."""
    logger.info("update_task", task_id=task_id)
    
    service = TaskService(db)
    try:
        task = service.update_task(
            task_id=task_id,
            title=update.title,
            description=update.description,
            priority=update.priority.value if update.priority else None,
            status=update.status.value if update.status else None,
        )
        logger.info("task_updated", task_id=task_id)
        return task
    except ValueError as e:
        logger.warning("update_task_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Task Execution API (v0.3.0 P0 - Agent execution loop)
# ============================================================

class TaskReport(BaseModel):
    """Task completion report from Agent."""
    task_id: str = Field(..., description="Task ID")
    agent_id: str = Field(..., description="Agent ID")
    token_used: int = Field(..., ge=0, description="Actual tokens consumed")
    result_summary: str = Field(..., min_length=1, max_length=2000, description="Work summary")
    status: str = Field(default="completed", description="completed or failed")


class TaskReportResponse(BaseModel):
    """Task report response."""
    success: bool
    task_id: str
    status: str
    cost: float
    remaining_budget: float
    fused: bool
    message: str


@router.post("/report", response_model=TaskReportResponse)
@limiter.limit(RATE_LIMITS["create"])
async def report_task_completion(
    request: Request,
    report: TaskReport,
    db: Session = Depends(get_db),
):
    """
    Report task completion from Agent.
    
    This is the callback endpoint for Agents to report task results.
    Called by Agents via opc_report() or directly via HTTP.
    
    **Authentication**: Agents use their agent_id as authentication.
    
    **Process**:
    1. Validate task and agent
    2. Update task status and cost
    3. Update agent budget
    4. Record transaction
    5. Send notification
    
    **Returns**:
    - Updated budget info
    - Fuse status (if budget exceeded)
    """
    from src.services.task_execution_service import TaskExecutionService
    
    logger.info(
        "task_report_received",
        task_id=report.task_id,
        agent_id=report.agent_id,
        status=report.status
    )
    
    service = TaskExecutionService(db)
    result = service.report_task_completion(
        task_id=report.task_id,
        agent_id=report.agent_id,
        token_used=report.token_used,
        result_summary=report.result_summary,
        status=report.status
    )
    
    if not result.get("success"):
        logger.warning(
            "task_report_failed",
            task_id=report.task_id,
            error=result.get("error")
        )
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    logger.info(
        "task_report_processed",
        task_id=report.task_id,
        status=result["status"],
        cost=result["cost"]
    )
    
    return TaskReportResponse(
        success=True,
        task_id=result["task_id"],
        status=result["status"],
        cost=result["cost"],
        remaining_budget=result["remaining_budget"],
        fused=result["fused"],
        message=f"Task {result['status']}. Budget: {result['remaining_budget']:.2f} OC币 remaining."
    )


@router.get("/{task_id}/execution")
async def get_task_execution_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    Get task execution status.
    
    Returns detailed execution information including:
    - Current execution status
    - When task was sent to agent
    - Session ID
    - Completion info (if finished)
    """
    from src.services.task_execution_service import TaskExecutionService
    
    service = TaskExecutionService(db)
    status = service.get_execution_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return status


@router.post("/{task_id}/resend")
@limiter.limit(RATE_LIMITS["create"])
async def resend_task_to_agent(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    Manually resend task to Agent.
    
    Useful when:
    - Initial send failed
    - Agent didn't receive the task
    - Need to retry after timeout
    
    Requires task status to be 'assigned'.
    """
    from src.services.task_execution_service import TaskExecutionService
    from src.models import Task
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.ASSIGNED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resend task with status '{task.status}'. Must be 'assigned'."
        )
    
    if not task.agent_id:
        raise HTTPException(status_code=400, detail="Task has no assigned agent")
    
    # Get agent's openclaw agent_id
    agent = db.query(Agent).filter(Agent.id == task.agent_id).first()
    if not agent or not agent.agent_id:
        raise HTTPException(status_code=400, detail="Agent not bound to OpenClaw")
    
    service = TaskExecutionService(db)
    result = service.send_task_to_agent(task_id, agent.agent_id)
    
    if result.get("success"):
        return {
            "success": True,
            "message": result["message"],
            "session_id": result.get("session_id")
        }
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to resend"))


# ============================================================
# Exact Token Tracking API (v0.3.0 P0 #4)
# ============================================================

class ExactTokenRecord(BaseModel):
    """Record exact token usage for a task."""
    session_key: str = Field(..., description="OpenClaw session key")


class ExactTokenResponse(BaseModel):
    """Exact token recording response."""
    success: bool
    task_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    exact_cost: float
    message: str


@router.post("/{task_id}/exact-tokens", response_model=ExactTokenResponse)
async def record_exact_tokens(
    request: Request,
    task_id: str,
    record: ExactTokenRecord,
    db: Session = Depends(get_db),
):
    """
    Record exact token usage for a completed task.
    
    This endpoint is called to update a task with exact token consumption
    from OpenClaw session_status. Should be called after task completion
    when the exact session data is available.
    
    **Process**:
    1. Fetches exact tokens from OpenClaw session_status
    2. Updates task with exact input/output tokens
    3. Recalculates actual cost if significant difference
    4. Adjusts agent budget if needed
    
    **When to call**:
    - After Agent reports task completion
    - When OpenClaw session has ended
    - For reconciliation of estimated vs actual costs
    """
    from src.services.exact_token_service import ExactTokenService
    
    logger.info(
        "record_exact_tokens_request",
        task_id=task_id,
        session_key=record.session_key
    )
    
    service = ExactTokenService(db)
    result = service.record_exact_tokens(task_id, record.session_key)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to record tokens"))
    
    logger.info(
        "exact_tokens_recorded",
        task_id=task_id,
        total_tokens=result.get("total_tokens"),
        model=result.get("model")
    )
    
    return ExactTokenResponse(
        success=True,
        task_id=result["task_id"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        total_tokens=result["total_tokens"],
        model=result["model"],
        exact_cost=result["exact_cost"],
        message=f"Exact tokens recorded. Cost: {result['exact_cost']:.2f} OC币"
    )


@router.get("/stats/exact-tokens")
async def get_exact_token_summary(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get summary of exact vs estimated token tracking.
    
    Returns statistics showing how many tasks have exact token tracking
    vs estimated tracking.
    
    **Metrics**:
    - Total completed tasks
    - Tasks with exact token tracking
    - Tasks with estimated tracking
    - Exact tracking percentage
    - Total input/output tokens
    """
    from src.services.exact_token_service import ExactTokenService
    
    service = ExactTokenService(db)
    summary = service.get_exact_token_summary(agent_id)
    
    return summary


@router.post("/batch/exact-tokens")
async def batch_record_exact_tokens(
    request: Request,
    session_keys: Dict[str, str] = Body(..., description="Map of task_id -> session_key"),
    db: Session = Depends(get_db),
):
    """
    Batch record exact tokens for multiple tasks.
    
    Useful for reconciling multiple tasks at once after a batch of
    OpenClaw sessions have completed.
    
    **Request body**: Dict mapping task_id to session_key
    
    **Example**:
    ```json
    {
        "task_abc123": "session_xyz789",
        "task_def456": "session_uvw012"
    }
    ```
    
    **Returns**:
    - List of successful updates
    - List of failed updates with errors
    """
    from src.services.exact_token_service import ExactTokenService
    
    if not session_keys:
        raise HTTPException(status_code=400, detail="No session keys provided")
    
    service = ExactTokenService(db)
    results = service.batch_update_exact_tokens(session_keys)
    
    return {
        "success": True,
        "total": results["total"],
        "successful": len(results["success"]),
        "failed": len(results["failed"]),
        "details": results
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a task.
    
    Args:
        task_id: Task ID to delete
    
    Returns:
        Deletion result
    """
    from src.models import Task, Agent, TaskStep, TaskStepMessage
    
    # Get task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_title = task.title
    agent_id = task.agent_id
    
    # Update agent's current_task_id if this was their current task
    if agent_id and task.status in ["assigned", "in_progress"]:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if agent and agent.current_task_id == task_id:
            agent.current_task_id = None
            agent.status = "idle"
    
    # Delete task steps and messages first (cascade delete)
    steps = db.query(TaskStep).filter(TaskStep.task_id == task_id).all()
    for step in steps:
        # Delete messages for this step
        db.query(TaskStepMessage).filter(TaskStepMessage.step_id == step.id).delete()
        # Delete the step
        db.delete(step)
    
    # Delete task
    db.delete(task)
    db.commit()
    
    return {
        "success": True,
        "message": f"Task '{task_title}' has been deleted",
        "task_id": task_id,
        "task_title": task_title
    }


# ============================================================
# Task Report Endpoint (Phase 6) - Agent Callback
# ============================================================

class TaskReport(BaseModel):
    """Task completion report from Agent."""
    agent_id: str = Field(..., description="OpenClaw Agent ID reporting the task")
    status: str = Field(..., description="Task status: completed or failed")
    result_summary: str = Field(default="", description="Summary of the task result")
    token_used: int = Field(default=0, ge=0, description="Total tokens used")
    tokens_input: Optional[int] = Field(default=None, ge=0, description="Input tokens consumed")
    tokens_output: Optional[int] = Field(default=None, ge=0, description="Output tokens consumed")
    session_key: Optional[str] = Field(default=None, description="OpenClaw session key for exact token tracking")
    is_exact: bool = Field(default=False, description="Whether tokens are exact measurements from session_status API")


@router.post("/{task_id}/report")
@limiter.limit(RATE_LIMITS["create"])
async def report_task_completion(
    request: Request,
    task_id: str,
    report: TaskReport,
    db: Session = Depends(get_db),
):
    """
    Report task completion from Agent.
    
    Called by OPC Bridge Skill or Agent after task completion.
    Supports both estimated and exact token consumption reporting.
    
    **Authentication**: Requires valid Agent ID (checked against assigned agent)
    
    **Request body**:
    - agent_id: OpenClaw Agent ID
    - status: "completed" or "failed"
    - result_summary: Task result description
    - token_used: Total tokens (if exact=False)
    - tokens_input/output: Exact tokens (if exact=True)
    - session_key: For fetching exact tokens from session_status API
    - is_exact: Whether to use exact token tracking
    
    **Returns**:
    - Task update confirmation
    - Budget deduction details
    """
    from src.models import Task, Agent
    from src.services.agent_service import AgentService
    
    # Get task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify agent is assigned to this task
    agent = db.query(Agent).filter(Agent.agent_id == report.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if task.agent_id != agent.id:
        raise HTTPException(status_code=403, detail="Agent not assigned to this task")
    
    # Validate status
    if report.status not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Status must be 'completed' or 'failed'")
    
    try:
        # Use AgentService for consistent task reporting
        service = AgentService(db)
        
        # If exact token tracking is requested and session_key provided
        if report.is_exact and report.session_key:
            result = service.report_task_completion(
                agent_id=agent.agent_id,  # Pass OpenClaw Agent ID
                task_id=task_id,
                token_used=report.token_used,
                result_summary=report.result_summary,
                status=report.status,
                tokens_input=report.tokens_input,
                tokens_output=report.tokens_output,
                session_key=report.session_key,
                is_exact=True,
            )
        else:
            # Use estimated tokens
            result = service.report_task_completion(
                agent_id=agent.agent_id,  # Pass OpenClaw Agent ID
                task_id=task_id,
                token_used=report.token_used,
                result_summary=report.result_summary,
                status=report.status,
            )
        
        logger.info(
            "task_reported",
            task_id=task_id,
            agent_id=agent.id,
            status=report.status,
            is_exact=report.is_exact
        )
        
        # v0.4.0 - Trigger task dependencies
        try:
            from src.services.task_dependency_service import TaskDependencyService
            dep_service = TaskDependencyService(db)
            triggered = dep_service.check_and_trigger_dependencies(task_id, report.status)
            
            if triggered:
                logger.info(
                    "dependencies_triggered",
                    task_id=task_id,
                    triggered_count=len(triggered),
                    triggered_task_ids=[t.id for t in triggered],
                )
        except Exception as e:
            # Don't fail the task report if dependency trigger fails
            logger.error("dependency_trigger_failed", task_id=task_id, error=str(e))
        
        # v0.4.0 - Award skill growth experience for completed tasks
        skill_growth_results = []
        if report.status == "completed":
            try:
                from src.services.skill_growth_service import SkillGrowthService
                growth_service = SkillGrowthService(db)
                skill_growth_results = growth_service.award_task_completion_exp(agent.id, task)
                
                if skill_growth_results:
                    logger.info(
                        "skill_experience_awarded",
                        task_id=task_id,
                        agent_id=agent.id,
                        skills_count=len(skill_growth_results),
                    )
            except Exception as e:
                # Don't fail the task report if skill growth fails
                logger.error("skill_growth_award_failed", task_id=task_id, error=str(e))
        
        return {
            "success": True,
            "task_id": task_id,
            "status": report.status,
            "message": f"Task '{task.title}' marked as {report.status}",
            "budget_deducted": result.get("token_used", report.token_used),
            "agent_remaining_budget": agent.remaining_budget,
            "skill_growth": skill_growth_results if skill_growth_results else None,
        }
        
    except ValueError as e:
        logger.error("task_report_failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("task_report_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process report: {str(e)}")
