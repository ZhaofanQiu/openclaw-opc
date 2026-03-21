"""
Budget API routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from src.database import get_db
from src.services.budget_service import BudgetService

router = APIRouter()


class ExactConsumptionRequest(BaseModel):
    """Request to record exact token consumption."""
    agent_id: str = Field(..., description="Agent ID (OpenClaw agent ID)")
    task_id: str = Field(..., description="Task ID")
    tokens_input: int = Field(..., ge=0, description="Actual input tokens consumed")
    tokens_output: int = Field(..., ge=0, description="Actual output tokens consumed")
    session_key: str = Field(..., description="OpenClaw session identifier")


class UpdateExactRequest(BaseModel):
    """Request to update transaction with exact values."""
    tokens_input: int = Field(..., ge=0, description="Actual input tokens")
    tokens_output: int = Field(..., ge=0, description="Actual output tokens")
    session_key: str = Field(..., description="OpenClaw session key")


@router.get("/company")
async def get_company_budget(
    db: Session = Depends(get_db),
):
    """Get company-wide budget overview."""
    service = BudgetService(db)
    return service.get_company_budget()


@router.get("/agents/{agent_id}")
async def get_agent_budget(
    agent_id: str,
    db: Session = Depends(get_db),
):
    """Get agent budget details."""
    service = BudgetService(db)
    return service.get_agent_budget(agent_id)


@router.get("/transactions")
async def list_transactions(
    agent_id: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List budget transactions."""
    service = BudgetService(db)
    transactions = service.list_transactions(agent_id=agent_id, limit=limit)
    
    # Format response with exact tracking info
    result = []
    for t in transactions:
        result.append({
            "id": t.id,
            "agent_id": t.agent_id,
            "task_id": t.task_id,
            "transaction_type": t.transaction_type,
            "amount": t.amount,
            "description": t.description,
            "actual_tokens_input": t.actual_tokens_input,
            "actual_tokens_output": t.actual_tokens_output,
            "total_tokens": t.actual_tokens_input + t.actual_tokens_output,
            "is_exact": t.is_exact == "true",
            "session_key": t.session_key,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    
    return result


@router.post("/exact-consumption")
async def record_exact_consumption(
    request: ExactConsumptionRequest,
    db: Session = Depends(get_db),
):
    """
    Record exact token consumption from session_status.
    Called by Partner Agent after task completion with actual token usage.
    """
    from src.models import Agent
    
    service = BudgetService(db)
    
    # Get internal agent ID
    agent = db.query(Agent).filter(Agent.agent_id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found")
    
    try:
        transaction = service.record_exact_consumption(
            agent_id=agent.id,
            task_id=request.task_id,
            tokens_input=request.tokens_input,
            tokens_output=request.tokens_output,
            session_key=request.session_key,
        )
        return {
            "success": True,
            "transaction": {
                "id": transaction.id,
                "tokens_input": transaction.actual_tokens_input,
                "tokens_output": transaction.actual_tokens_output,
                "total_tokens": transaction.actual_tokens_input + transaction.actual_tokens_output,
                "cost": abs(transaction.amount),
                "is_exact": True,
                "session_key": transaction.session_key,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record consumption: {str(e)}")


@router.patch("/transactions/{transaction_id}/exact")
async def update_transaction_exact(
    transaction_id: str,
    request: UpdateExactRequest,
    db: Session = Depends(get_db),
):
    """
    Update an existing transaction with exact token values.
    Called when actual token consumption becomes available after estimation.
    """
    service = BudgetService(db)
    
    transaction = service.update_transaction_with_exact(
        transaction_id=transaction_id,
        tokens_input=request.tokens_input,
        tokens_output=request.tokens_output,
        session_key=request.session_key,
    )
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "success": True,
        "transaction": {
            "id": transaction.id,
            "tokens_input": transaction.actual_tokens_input,
            "tokens_output": transaction.actual_tokens_output,
            "total_tokens": transaction.actual_tokens_input + transaction.actual_tokens_output,
            "cost": abs(transaction.amount),
            "is_exact": transaction.is_exact == "true",
            "session_key": transaction.session_key,
        }
    }


@router.get("/comparison")
async def get_consumption_comparison(
    days: int = 30,
    db: Session = Depends(get_db),
):
    """
    Get comparison between estimated and actual token consumption.
    Shows accuracy of estimates vs real usage.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 365")
    
    service = BudgetService(db)
    return service.get_consumption_comparison(days=days)
