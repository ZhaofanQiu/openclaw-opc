"""
Budget models.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from src.database import Base


class TransactionType(str, PyEnum):
    """Transaction type enum."""
    TASK_ALLOCATION = "task_allocation"
    TASK_CONSUMPTION = "task_consumption"
    SALARY = "salary"
    ADJUSTMENT = "adjustment"


class BudgetTransaction(Base):
    """Budget transaction log."""
    
    __tablename__ = "budget_transactions"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    task_id = Column(String, nullable=True)
    
    transaction_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # Positive = add, Negative = consume
    
    description = Column(Text, default="")
    
    created_at = Column(DateTime, default=datetime.utcnow)
