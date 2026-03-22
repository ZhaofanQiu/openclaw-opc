"""
Task execution service for managing the Agent task execution loop.

This service handles:
1. Sending tasks to Agents via sessions_send
2. Tracking task execution state
3. Receiving completion reports from Agents
4. Handling timeouts and failures
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

from sqlalchemy.orm import Session

from models import Agent, AgentStatus, Task, TaskStatus
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ExecutionStatus(str, Enum):
    """Task execution status."""
    SENT = "sent"           # Task sent to Agent, waiting for ack
    ACKED = "acked"         # Agent acknowledged receipt
    RUNNING = "running"     # Agent is working on task
    COMPLETED = "completed" # Agent reported completion
    FAILED = "failed"       # Agent reported failure or error
    TIMEOUT = "timeout"     # Task timed out
    CANCELLED = "cancelled" # Task was cancelled


class TaskExecutionService:
    """Service for managing task execution lifecycle."""
    
    # Default timeout for task execution (in minutes)
    DEFAULT_TIMEOUT_MINUTES = 30
    
    def __init__(self, db: Session):
        self.db = db
    
    def send_task_to_agent(self, task_id: str, agent_id: str) -> Dict:
        """
        Send task to Agent via sessions_send.
        
        This is the core of the execution loop - when a task is assigned,
        we actively notify the Agent to start working.
        
        Args:
            task_id: Task ID
            agent_id: Agent ID (employee.agent_id, which is the openclaw agent_id)
            
        Returns:
            Dict with success status and message
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "error": f"Task '{task_id}' not found"}
        
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found"}
        
        # Build task message for the Agent
        task_message = self._build_task_message(task, agent)
        
        try:
            # Try to import sessions_send from openclaw
            # This is the key integration point with OpenClaw
            result = self._send_via_sessions(agent_id, task_message)
            
            if result.get("success"):
                # Update task status
                task.status = TaskStatus.ASSIGNED.value
                task.execution_status = ExecutionStatus.SENT.value
                task.sent_to_agent_at = datetime.utcnow()
                task.execution_session_id = result.get("session_id")  # Store async message ID
                
                # Update agent status
                agent.status = AgentStatus.WORKING.value
                agent.current_task_id = task.id
                
                self.db.commit()
                
                logger.info(
                    "task_sent_to_agent",
                    task_id=task_id,
                    agent_id=agent_id,
                    session_id=result.get("session_id")
                )
                
                return {
                    "success": True,
                    "message": f"Task sent to Agent '{agent.name}'",
                    "session_id": result.get("session_id"),
                    "async": True
                }
            else:
                logger.error(
                    "failed_to_send_task",
                    task_id=task_id,
                    agent_id=agent_id,
                    error=result.get("error")
                )
                return {
                    "success": False,
                    "error": result.get("error", "Failed to send task to Agent")
                }
                
        except Exception as e:
            logger.error(
                "exception_sending_task",
                task_id=task_id,
                agent_id=agent_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": f"Failed to send task: {str(e)}"
            }
    
    def _build_task_message(self, task: Task, agent: Agent) -> str:
        """
        Build the task message to send to the Agent.
        
        This message should be clear and actionable for the Agent.
        """
        message_parts = [
            f"📋 **新任务分配**",
            f"",
            f"**任务ID**: {task.id}",
            f"**标题**: {task.title}",
            f"**优先级**: {task.priority}",
            f"**预算**: {task.estimated_cost} OC币 (约 {int(task.estimated_cost * 100)} tokens)",
            f"",
        ]
        
        if task.description:
            message_parts.extend([
                f"**描述**:",
                f"{task.description}",
                f"",
            ])
        
        # Handle skill requirements safely
        try:
            if hasattr(task, 'required_skills') and task.required_skills:
                message_parts.append(f"**所需技能**: {', '.join(task.required_skills)}")
        except:
            pass  # Skills not available, skip
        
        # Handle due date safely - Task model doesn't have due_date field
        # Use is_overdue flag instead
        try:
            if hasattr(task, 'is_overdue') and task.is_overdue == "true":
                message_parts.append(f"**⚠️ 注意**: 此任务已逾期")
        except:
            pass
        
        message_parts.extend([
            f"",
            f"---",
            f"请完成后调用 opc_report(task_id='{task.id}', token_used=实际消耗, result_summary='结果摘要', status='completed') 报告结果。",
            f"如果无法完成，请调用 opc_report(status='failed', result_summary='失败原因')。",
        ])
        
        return "\n".join(message_parts)
    
    def _send_via_sessions(self, agent_id: str, message: str) -> Dict:
        """
        Send message to Agent via sessions_send.
        
        Async mode: Returns immediately, message is queued for background processing.
        """
        try:
            import requests
            
            # Use async message API instead of direct sessions_send
            # This returns immediately without waiting for Agent response
            gateway_url = "http://localhost:8080"
            
            payload = {
                "recipient_id": agent_id,
                "content": message,
                "subject": "任务分配",
                "message_type": "task",
                "timeout_seconds": 1800  # 30 minutes
            }
            
            response = requests.post(
                f"{gateway_url}/api/async-messages/send",
                json=payload,
                timeout=5  # Short timeout for API call
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "session_id": data.get("message_id"),
                    "async": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Gateway returned {response.status_code}: {response.text}"
                }
                
        except ImportError:
            return self._send_via_fallback(agent_id, message)
        except requests.RequestException as e:
            logger.warning("gateway_unavailable", error=str(e))
            return self._send_via_fallback(agent_id, message)
    
    def _send_via_fallback(self, agent_id: str, message: str) -> Dict:
        """
        Fallback implementation when OpenClaw gateway is not available.
        
        This stores the message in a queue for the Agent to pick up later.
        """
        # Store in a "pending messages" queue
        # In production, this would use Redis or a database queue
        from services.notification_service import NotificationService
        
        notification_service = NotificationService(self.db)
        
        # Create a notification that the Agent can check
        notification_service.create_notification(
            type="task_assigned",
            title="新任务待处理",
            message=f"Agent '{agent_id}' 有新任务分配。OpenClaw Gateway 当前不可用，任务已进入队列。",
            agent_id=agent_id
        )
        
        return {
            "success": True,
            "session_id": f"queued_{str(uuid.uuid4())[:8]}",
            "note": "Gateway unavailable, task queued for later delivery"
        }
    
    def report_task_completion(
        self,
        task_id: str,
        agent_id: str,
        token_used: int,
        result_summary: str,
        status: str = "completed"
    ) -> Dict:
        """
        Receive task completion report from Agent.
        
        This is called by the Agent via opc_report() or directly via API.
        
        Args:
            task_id: Task ID
            agent_id: Agent ID
            token_used: Actual tokens consumed
            result_summary: Summary of work done
            status: "completed" or "failed"
            
        Returns:
            Dict with success status and updated budget info
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "error": f"Task '{task_id}' not found"}
        
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found"}
        
        # Verify this Agent was assigned this task
        if task.agent_id != agent.id:
            return {
                "success": False,
                "error": f"Task '{task_id}' is not assigned to Agent '{agent_id}'"
            }
        
        # Calculate actual cost (1 OC币 = 100 tokens)
        actual_cost = token_used / 100.0
        
        # Update task
        task.status = TaskStatus.COMPLETED.value if status == "completed" else TaskStatus.FAILED.value
        task.execution_status = ExecutionStatus.COMPLETED.value if status == "completed" else ExecutionStatus.FAILED.value
        task.actual_cost = actual_cost
        task.token_used = token_used
        task.result_summary = result_summary
        task.completed_at = datetime.utcnow()
        
        # Update agent budget and status
        agent.used_budget = (agent.used_budget or 0) + actual_cost
        agent.status = AgentStatus.IDLE.value
        agent.current_task_id = None
        
        # Record transaction manually
        from models import BudgetTransaction, TransactionType
        import uuid
        transaction = BudgetTransaction(
            id=str(uuid.uuid4())[:8],
            agent_id=agent.id,
            task_id=task.id,
            transaction_type=TransactionType.TASK_CONSUMPTION.value if hasattr(TransactionType, 'TASK_CONSUMPTION') else "task",
            amount=-actual_cost,
            description=f"Task '{task.title}' {status}",
        )
        self.db.add(transaction)
        
        self.db.commit()
        
        # Create notification
        from services.notification_service import NotificationService
        notification_service = NotificationService(self.db)
        
        if status == "completed":
            notification_service.notify_task_completed(
                task_id=task.id,
                task_title=task.title,
                agent_name=agent.name
            )
        else:
            notification_service.create_notification(
                type="task_failed",
                title="任务执行失败",
                message=f"Agent '{agent.name}' 报告任务 '{task.title}' 失败: {result_summary}",
                agent_id=agent_id,
                task_id=task.id
            )
        
        logger.info(
            "task_completion_reported",
            task_id=task_id,
            agent_id=agent_id,
            status=status,
            cost=actual_cost,
            tokens=token_used
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "status": status,
            "cost": actual_cost,
            "remaining_budget": agent.remaining_budget,
            "fused": agent.remaining_budget <= 0
        }
    
    def check_execution_timeout(self, task_id: str) -> bool:
        """
        Check if a task has exceeded its execution timeout.
        
        Returns True if task timed out and was marked as such.
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        if task.execution_status not in [ExecutionStatus.SENT.value, ExecutionStatus.ACKED.value, ExecutionStatus.RUNNING.value]:
            return False
        
        # Check timeout
        if task.sent_to_agent_at:
            timeout = timedelta(minutes=self.DEFAULT_TIMEOUT_MINUTES)
            if datetime.utcnow() - task.sent_to_agent_at > timeout:
                # Mark as timeout
                task.execution_status = ExecutionStatus.TIMEOUT.value
                task.status = TaskStatus.FAILED.value
                
                # Reset agent status
                agent = self.db.query(Agent).filter(Agent.id == task.agent_id).first()
                if agent:
                    agent.status = AgentStatus.IDLE.value
                    agent.current_task_id = None
                
                self.db.commit()
                
                # Create notification
                from services.notification_service import NotificationService
                notification_service = NotificationService(self.db)
                notification_service.create_notification(
                    type="task_timeout",
                    title="任务执行超时",
                    message=f"任务 '{task.title}' 执行超时（{self.DEFAULT_TIMEOUT_MINUTES}分钟）",
                    task_id=task.id
                )
                
                logger.warning("task_execution_timeout", task_id=task_id)
                return True
        
        return False
    
    def get_execution_status(self, task_id: str) -> Optional[Dict]:
        """Get detailed execution status for a task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return None
        
        return {
            "task_id": task.id,
            "status": task.status,
            "execution_status": task.execution_status,
            "sent_at": task.sent_to_agent_at.isoformat() if task.sent_to_agent_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "session_id": task.execution_session_id,
            "actual_cost": task.actual_cost,
            "token_used": task.token_used,
            "result_summary": task.result_summary
        }
