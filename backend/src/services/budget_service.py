"""
Budget service layer.
"""

from typing import List, Optional

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
    
    def record_exact_consumption(
        self,
        agent_id: str,
        task_id: str,
        tokens_input: int,
        tokens_output: int,
        session_key: str,
        description: str = "",
    ) -> BudgetTransaction:
        """
        Record exact token consumption from session_status.
        
        Args:
            agent_id: Internal agent ID
            task_id: Task ID
            tokens_input: Actual input tokens consumed
            tokens_output: Actual output tokens consumed
            session_key: OpenClaw session identifier
            description: Transaction description
        
        Returns:
            Created BudgetTransaction
        """
        import uuid
        
        total_tokens = tokens_input + tokens_output
        cost = total_tokens / 100.0  # 1 OC币 = 100 tokens
        
        transaction = BudgetTransaction(
            id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            task_id=task_id,
            transaction_type="task_consumption",
            amount=-cost,
            description=description or f"Exact consumption: {total_tokens} tokens",
            actual_tokens_input=tokens_input,
            actual_tokens_output=tokens_output,
            is_exact="true",
            session_key=session_key,
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction
    
    def update_transaction_with_exact(
        self,
        transaction_id: str,
        tokens_input: int,
        tokens_output: int,
        session_key: str,
    ) -> Optional[BudgetTransaction]:
        """
        Update an existing transaction with exact token values.
        Called when actual token consumption becomes available.
        
        Args:
            transaction_id: Transaction ID to update
            tokens_input: Actual input tokens
            tokens_output: Actual output tokens
            session_key: OpenClaw session key
        
        Returns:
            Updated transaction or None if not found
        """
        transaction = self.db.query(BudgetTransaction).filter(
            BudgetTransaction.id == transaction_id
        ).first()
        
        if not transaction:
            return None
        
        transaction.actual_tokens_input = tokens_input
        transaction.actual_tokens_output = tokens_output
        transaction.is_exact = "true"
        transaction.session_key = session_key
        
        # Recalculate cost based on exact tokens
        total_tokens = tokens_input + tokens_output
        new_amount = -(total_tokens / 100.0)
        
        # Update agent budget if amount changed significantly
        old_amount = transaction.amount
        if abs(new_amount - old_amount) > 0.01:
            agent = self.db.query(Agent).filter(Agent.id == transaction.agent_id).first()
            if agent:
                # Adjust agent budget
                agent.used_budget = agent.used_budget - abs(old_amount) + abs(new_amount)
            transaction.amount = new_amount
        
        self.db.commit()
        self.db.refresh(transaction)
        
        return transaction
    
    def get_consumption_comparison(
        self,
        days: int = 30,
    ) -> dict:
        """
        Get comparison between estimated and actual token consumption.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Comparison statistics
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        transactions = self.db.query(BudgetTransaction).filter(
            BudgetTransaction.created_at >= cutoff_date,
            BudgetTransaction.transaction_type == "task_consumption"
        ).all()
        
        exact_transactions = [t for t in transactions if t.is_exact == "true"]
        estimated_transactions = [t for t in transactions if t.is_exact != "true"]
        
        total_estimated = sum(abs(t.amount) for t in estimated_transactions)
        total_exact = sum(abs(t.amount) for t in exact_transactions)
        
        total_estimated_tokens = sum(
            t.actual_tokens_input + t.actual_tokens_output
            for t in estimated_transactions
        )
        total_exact_tokens = sum(
            t.actual_tokens_input + t.actual_tokens_output
            for t in exact_transactions
        )
        
        return {
            "period_days": days,
            "total_transactions": len(transactions),
            "exact_count": len(exact_transactions),
            "estimated_count": len(estimated_transactions),
            "exact_percentage": (
                len(exact_transactions) / len(transactions) * 100
                if transactions else 0
            ),
            "estimated_cost": round(total_estimated, 2),
            "exact_cost": round(total_exact, 2),
            "estimated_tokens": total_estimated_tokens,
            "exact_tokens": total_exact_tokens,
            "cost_difference": round(total_exact - total_estimated, 2),
            "accuracy_percentage": (
                (1 - abs(total_exact - total_estimated) / total_estimated * 100)
                if total_estimated > 0 else 100
            ),
        }
