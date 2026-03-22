"""
Exact token tracking service for precise budget calculation.

This service integrates with OpenClaw's session_status to get exact
token consumption instead of estimates.

v0.3.0 P0 #4 - Exact Token Tracking
"""

from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from models import Agent, Task, TaskStatus
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ExactTokenService:
    """Service for exact token tracking using OpenClaw session_status."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def fetch_session_tokens(self, session_key: str) -> Optional[Dict]:
        """
        Fetch exact token usage from OpenClaw session_status.
        
        Args:
            session_key: OpenClaw session identifier
            
        Returns:
            Dict with input_tokens, output_tokens, total_tokens, model
            or None if session not found or error
        """
        try:
            # Try to call OpenClaw gateway API
            import requests
            
            # OpenClaw gateway endpoint
            gateway_url = "http://localhost:8080"
            
            response = requests.get(
                f"{gateway_url}/api/sessions/status",
                params={"sessionKey": session_key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract token info from session_status response
                # Format depends on OpenClaw's actual response structure
                return {
                    "input_tokens": data.get("input_tokens", 0),
                    "output_tokens": data.get("output_tokens", 0),
                    "total_tokens": data.get("total_tokens", 0),
                    "model": data.get("model", "unknown"),
                    "success": True
                }
            else:
                logger.warning(
                    "session_status_fetch_failed",
                    session_key=session_key,
                    status_code=response.status_code,
                    response=response.text
                )
                return None
                
        except requests.RequestException as e:
            logger.warning(
                "session_status_gateway_unavailable",
                session_key=session_key,
                error=str(e)
            )
            return None
        except Exception as e:
            logger.error(
                "session_status_exception",
                session_key=session_key,
                error=str(e)
            )
            return None
    
    def record_exact_tokens(
        self,
        task_id: str,
        session_key: str,
        agent_id: Optional[str] = None
    ) -> Dict:
        """
        Record exact token usage for a completed task.
        
        This should be called after task completion to update
        the exact token consumption.
        
        Args:
            task_id: Task ID
            session_key: OpenClaw session key
            agent_id: Optional agent ID for verification
            
        Returns:
            Dict with success status and token info
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "error": f"Task '{task_id}' not found"}
        
        # Fetch exact tokens from session
        token_data = self.fetch_session_tokens(session_key)
        
        if not token_data:
            return {
                "success": False,
                "error": "Failed to fetch exact token data from session",
                "note": "Session may have expired or Gateway is unavailable"
            }
        
        # Update task with exact tokens
        task.actual_tokens_input = token_data["input_tokens"]
        task.actual_tokens_output = token_data["output_tokens"]
        task.is_exact = "true"
        task.session_key = session_key
        
        # Recalculate actual cost based on exact tokens
        total_tokens = token_data["total_tokens"]
        exact_cost = total_tokens / 100.0  # 1 OC币 = 100 tokens
        
        # Check if cost difference is significant
        cost_diff = abs(exact_cost - task.actual_cost)
        
        if cost_diff > 1.0:  # More than 1 OC币 difference
            logger.info(
                "significant_cost_difference",
                task_id=task_id,
                estimated=task.actual_cost,
                exact=exact_cost,
                diff=cost_diff
            )
            
            # Adjust agent budget if needed
            if task.agent_id:
                agent = self.db.query(Agent).filter(Agent.id == task.agent_id).first()
                if agent:
                    # Adjust used_budget
                    budget_adjustment = exact_cost - task.actual_cost
                    agent.used_budget = (agent.used_budget or 0) + budget_adjustment
                    
                    # Update task cost
                    old_cost = task.actual_cost
                    task.actual_cost = exact_cost
                    
                    # Update transaction
                    from models import BudgetTransaction
                    transaction = self.db.query(BudgetTransaction).filter(
                        BudgetTransaction.task_id == task_id
                    ).first()
                    
                    if transaction:
                        transaction.amount = -exact_cost
                        transaction.is_exact = "true"
                        transaction.actual_tokens_input = token_data["input_tokens"]
                        transaction.actual_tokens_output = token_data["output_tokens"]
                    
                    self.db.commit()
                    
                    logger.info(
                        "budget_adjusted_for_exact_tokens",
                        task_id=task_id,
                        old_cost=old_cost,
                        new_cost=exact_cost,
                        adjustment=budget_adjustment
                    )
        else:
            # Small difference, just update the task
            self.db.commit()
        
        logger.info(
            "exact_tokens_recorded",
            task_id=task_id,
            input_tokens=token_data["input_tokens"],
            output_tokens=token_data["output_tokens"],
            total_tokens=total_tokens,
            model=token_data.get("model", "unknown")
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "input_tokens": token_data["input_tokens"],
            "output_tokens": token_data["output_tokens"],
            "total_tokens": total_tokens,
            "model": token_data.get("model", "unknown"),
            "exact_cost": exact_cost,
            "previous_cost": task.actual_cost if cost_diff <= 1.0 else exact_cost - cost_diff,
            "cost_diff": cost_diff if cost_diff <= 1.0 else cost_diff
        }
    
    def get_exact_token_summary(self, agent_id: Optional[str] = None) -> Dict:
        """
        Get summary of exact vs estimated token tracking.
        
        Args:
            agent_id: Optional agent ID to filter by
            
        Returns:
            Dict with summary statistics
        """
        query = self.db.query(Task).filter(
            Task.status.in_([TaskStatus.COMPLETED.value, TaskStatus.FAILED.value])
        )
        
        if agent_id:
            agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
            if agent:
                query = query.filter(Task.agent_id == agent.id)
        
        tasks = query.all()
        
        total_tasks = len(tasks)
        exact_tasks = sum(1 for t in tasks if t.is_exact == "true")
        estimated_tasks = total_tasks - exact_tasks
        
        total_estimated_cost = sum(t.actual_cost for t in tasks if t.is_exact != "true")
        total_exact_cost = sum(
            ((t.actual_tokens_input or 0) + (t.actual_tokens_output or 0)) / 100.0
            for t in tasks if t.is_exact == "true"
        )
        
        total_input_tokens = sum(t.actual_tokens_input or 0 for t in tasks)
        total_output_tokens = sum(t.actual_tokens_output or 0 for t in tasks)
        
        return {
            "total_tasks": total_tasks,
            "exact_tasks": exact_tasks,
            "estimated_tasks": estimated_tasks,
            "exact_percentage": (exact_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "total_estimated_cost": round(total_estimated_cost, 2),
            "total_exact_cost": round(total_exact_cost, 2),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens
        }
    
    def batch_update_exact_tokens(self, session_keys: Dict[str, str]) -> Dict:
        """
        Batch update exact tokens for multiple tasks.
        
        Args:
            session_keys: Dict mapping task_id -> session_key
            
        Returns:
            Dict with results for each task
        """
        results = {
            "success": [],
            "failed": [],
            "total": len(session_keys)
        }
        
        for task_id, session_key in session_keys.items():
            result = self.record_exact_tokens(task_id, session_key)
            
            if result.get("success"):
                results["success"].append({
                    "task_id": task_id,
                    "tokens": result.get("total_tokens", 0)
                })
            else:
                results["failed"].append({
                    "task_id": task_id,
                    "error": result.get("error", "Unknown error")
                })
        
        logger.info(
            "batch_exact_tokens_update",
            total=len(session_keys),
            success=len(results["success"]),
            failed=len(results["failed"])
        )
        
        return results
