"""
Budget API routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.budget_service import BudgetService

router = APIRouter()


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
    return service.list_transactions(agent_id=agent_id, limit=limit)
