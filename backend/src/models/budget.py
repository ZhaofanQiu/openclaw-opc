"""
Budget models.
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean

from database import Base


class TransactionType(str, PyEnum):
    """Transaction type enum."""
    TASK_ALLOCATION = "task_allocation"
    TASK_CONSUMPTION = "task_consumption"
    SALARY = "salary"
    ADJUSTMENT = "adjustment"


class BudgetTransaction(Base):
    """Budget transaction log.
    
    Tracks both estimated and actual token consumption.
    When is_exact='true', actual_tokens_* contain real values from session_status.
    When is_exact='false', these are estimates based on task complexity.
    """
    
    __tablename__ = "budget_transactions"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    task_id = Column(String, nullable=True)
    
    transaction_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # Positive = add, Negative = consume
    
    description = Column(Text, default="")
    
    # Exact token tracking fields
    actual_tokens_input = Column(Integer, default=0)  # Actual input tokens consumed
    actual_tokens_output = Column(Integer, default=0)  # Actual output tokens consumed
    is_exact = Column(String, default="false")  # "true" if exact values, "false" if estimated
    session_key = Column(String, nullable=True)  # Associated OpenClaw session
    
    created_at = Column(DateTime, default=datetime.utcnow)
