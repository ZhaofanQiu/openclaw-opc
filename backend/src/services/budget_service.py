"""
Budget service layer.
"""

from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import Agent, BudgetTransaction


class BudgetService:
    """Budget service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_company_budget(self) -> dict:
        """Get company-wide budget overview."""
        agents = self.db.query(Agent).all()
        
        total_budget = sum(a.monthly_budget for a in agents)
        total_used = sum(a.used_budget for a in agents)
        
        return {
            "total_agents": len(agents),
            "total_budget": total_budget,
            "total_used": total_used,
            "total_remaining": total_budget - total_used,
            "usage_percentage": (total_used / total_budget * 100) if total_budget > 0 else 0,
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "budget": a.monthly_budget,
                    "used": a.used_budget,
                    "remaining": a.remaining_budget,
                    "mood_emoji": a.mood_emoji,
                }
                for a in agents
            ],
        }
    
    def get_agent_budget(self, agent_id: str) -> dict:
        """Get agent budget details."""
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            return None
        
        return {
            "agent_id": agent.id,
            "name": agent.name,
            "monthly_budget": agent.monthly_budget,
            "used_budget": agent.used_budget,
            "remaining_budget": agent.remaining_budget,
            "mood_percentage": agent.mood_percentage,
            "mood_emoji": agent.mood_emoji,
            "usage_percentage": (
                (agent.used_budget / agent.monthly_budget * 100)
                if agent.monthly_budget > 0 else 0
            ),
        }
    
    def list_transactions(
        self,
        agent_id: str = None,
        limit: int = 50,
    ) -> List[BudgetTransaction]:
        """List budget transactions."""
        query = self.db.query(BudgetTransaction)
        
        if agent_id:
            agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
            if agent:
                query = query.filter(BudgetTransaction.agent_id == agent.id)
        
        return query.order_by(BudgetTransaction.created_at.desc()).limit(limit).all()
