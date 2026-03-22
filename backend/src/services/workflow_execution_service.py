"""
Workflow Execution Service v0.5.2 - 纯串行执行
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import WorkflowInstance, WorkflowStep, Agent
from src.models.workflow_engine import (
    StepType, WorkflowStatus, StepStatus,
    WorkflowHistory, WorkflowReworkRecord
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowExecutionService:
    """工作流执行服务 v0.5.2 - 纯串行"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_workflow(self, workflow_id: str) -> WorkflowInstance:
        """启动工作流"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        if workflow.status != WorkflowStatus.PENDING.value:
            raise ValueError(f"Cannot start workflow with status '{workflow.status}'")
        
        if not workflow.plan_result:
            raise ValueError("Workflow must be planned before starting")
        
        # 创建步骤实例（串行）
        step_plans = workflow.plan_result.get("step_plans", {})
        for step_id, plan in step_plans.items():
            step = WorkflowStep(
                id=str(__import__('uuid').uuid4())[:8],
                workflow_id=workflow_id,
                step_id=step_id,
                step_type=plan["step_type"],
                name=plan["name"],
                sequence=plan["sequence"],
                assignee_id=plan.get("agent_id"),
                base_budget=plan.get("base_budget", 0),
                rework_reserve=plan.get("rework_reserve", 0),
                estimated_hours=plan.get("estimated_hours", 4),
                handbook=plan.get("handbook", ""),
                rework_limit=plan.get("rework_limit", 3),
            )
            self.db.add(step)
        
        # 启动
        workflow.status = WorkflowStatus.IN_PROGRESS.value
        workflow.started_at = datetime.utcnow()
        workflow.current_step_index = 0
        
        # 分配第一步
        first_step = self._get_current_step(workflow_id)
        if first_step:
            first_step.status = StepStatus.ASSIGNED.value
            first_step.assigned_at = datetime.utcnow()
            self._notify_step_assignee(first_step)
        
        self._add_history(
            workflow_id=workflow_id,
            action="START_WORKFLOW",
            from_status=WorkflowStatus.PENDING.value,
            to_status=WorkflowStatus.IN_PROGRESS.value,
        )
        
        self.db.commit()
        logger.info("workflow_started", workflow_id=workflow_id)
        return workflow
    
    def complete_step(
        self,
        step_id: str,
        action: str,
        result: Dict,
        actor_id: str,
    ) -> Dict:
        """完成当前步骤"""
        step = self.db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step:
            raise ValueError(f"Step '{step_id}' not found")
        
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == step.workflow_id
        ).first()
        
        # 验证权限
        if step.assignee_id != actor_id:
            actor = self.db.query(Agent).filter(Agent.id == actor_id).first()
            from src.models.agent import PositionLevel
            if not actor or actor.position_level != PositionLevel.PARTNER.value:
                raise ValueError("Only assignee or Partner can complete step")
        
        # 计算预算消耗
        budget_used = result.get("budget_used", 0)
        
        # 判断首次还是返工
        if step.rework_count > 0:
            budget_source = "rework"
            if budget_used > step.rework_reserve:
                return self._handle_rework_budget_insufficient(step, workflow, budget_used)
            step.rework_cost += budget_used
            step.rework_reserve -= budget_used
            workflow.used_rework_budget += budget_used
        else:
            budget_source = "base"
            step.used_budget = budget_used
            workflow.used_base_budget += budget_used
        
        workflow.remaining_budget -= budget_used
        workflow.total_rework_cost += budget_used if step.rework_count > 0 else 0
        
        # 更新步骤
        step.result = result
        step.completed_at = datetime.utcnow()
        step.actual_hours = result.get("actual_hours", step.estimated_hours)
        
        if step.step_type == StepType.REVIEW.value:
            step.review_scores = result.get("review_scores", {})
        
        budget_impact = {
            "type": budget_source,
            "amount": budget_used,
            "remaining_rework_budget": workflow.rework_budget - workflow.used_rework_budget,
        }
        
        if action == "PASS":
            return self._handle_pass(step, workflow, result, actor_id, budget_impact)
        elif action == "REWORK":
            return self._handle_rework(step, workflow, result, actor_id, budget_impact)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def _handle_rework_budget_insufficient(
        self, step: WorkflowStep, workflow: WorkflowInstance, required: float
    ) -> Dict:
        """返工预算不足"""
        workflow.status = WorkflowStatus.BUDGET_FUSED.value
        
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="REWORK_BUDGET_FUSED",
            details={"required": required, "available": step.rework_reserve},
        )
        self.db.commit()
        
        return {
            "success": False,
            "fused": True,
            "fuse_type": "BUDGET",
            "message": f"返工预算不足：需要{required}，可用{step.rework_reserve}",
            "options": [
                {"action": "ADD_BUDGET", "label": "追加预算"},
                {"action": "FORCE_PASS", "label": "强行通过"},
                {"action": "RESTART", "label": "重新启动"},
                {"action": "CANCEL", "label": "取消任务"},
            ],
        }
    
    def _handle_pass(
        self, step: WorkflowStep, workflow: WorkflowInstance,
        result: Dict, actor_id: str, budget_impact: Dict
    ) -> Dict:
        """处理通过"""
        step.status = StepStatus.COMPLETED.value
        
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="COMPLETE_STEP",
            actor_id=actor_id,
            from_status=StepStatus.IN_PROGRESS.value,
            to_status=StepStatus.COMPLETED.value,
            details={"action": "PASS", "result": result},
            budget_impact=budget_impact,
        )
        
        # 检查是否是最后一步
        total_steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id
        ).count()
        
        if step.sequence >= total_steps - 1:
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.completed_at = datetime.utcnow()
            workflow.current_step_index = -1
            
            self._add_history(
                workflow_id=workflow.id,
                action="COMPLETE_WORKFLOW",
                from_status=WorkflowStatus.IN_PROGRESS.value,
                to_status=WorkflowStatus.COMPLETED.value,
            )
            self.db.commit()
            return {"success": True, "workflow_completed": True}
        
        # 进入下一步
        next_step = self._advance_to_next_step(workflow, step.sequence)
        workflow.current_step_index = next_step.sequence
        
        self.db.commit()
        return {
            "success": True,
            "workflow_completed": False,
            "next_step": {
                "id": next_step.id,
                "name": next_step.name,
                "type": next_step.step_type,
            },
        }
    
    def _handle_rework(
        self, step: WorkflowStep, workflow: WorkflowInstance,
        result: Dict, actor_id: str, budget_impact: Dict
    ) -> Dict:
        """处理返工 - 双熔断"""
        # 1. 返工次数熔断
        if step.rework_count >= step.rework_limit:
            workflow.status = WorkflowStatus.REWORK_FUSED.value
            self.db.commit()
            return {
                "success": False,
                "fused": True,
                "fuse_type": "REWORK_COUNT",
                "message": f"返工次数超限 ({step.rework_count}/{step.rework_limit})",
                "options": [
                    {"action": "FORCE_PASS", "label": "强行通过"},
                    {"action": "RESTART", "label": "重新启动"},
                    {"action": "ADD_BUDGET", "label": "追加预算重试"},
                ],
            }
        
        # 2. 找到返工目标
        target_step = self._find_nearest_execute_step(workflow.id, step.sequence)
        if not target_step:
            raise ValueError("No EXECUTE step found to rework to")
        
        # 执行返工
        target_step.status = StepStatus.REWORK.value
        target_step.rework_count += 1
        target_step.is_rework = "true"
        target_step.rework_from_step_id = step.id
        
        workflow.status = WorkflowStatus.REWORK.value
        workflow.total_rework_count += 1
        workflow.current_step_index = target_step.sequence
        
        # 记录返工
        rework_record = WorkflowReworkRecord(
            workflow_id=workflow.id,
            from_step_id=step.id,
            to_step_id=target_step.id,
            triggered_by=actor_id,
            reason=result.get("comment", ""),
            cost=budget_impact.get("amount", 0),
            rework_budget_before=budget_impact.get("remaining_rework_budget", 0) + budget_impact.get("amount", 0),
            rework_budget_after=budget_impact.get("remaining_rework_budget", 0),
        )
        self.db.add(rework_record)
        
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="REWORK_TRIGGERED",
            actor_id=actor_id,
            details={
                "to_step": target_step.id,
                "rework_count": target_step.rework_count,
            },
            budget_impact=budget_impact,
        )
        
        self.db.commit()
        self._notify_rework(target_step, step, result.get("comment", ""))
        
        return {
            "success": True,
            "rework": True,
            "rework_step": {
                "id": target_step.id,
                "name": target_step.name,
                "rework_count": target_step.rework_count,
                "rework_limit": target_step.rework_limit,
                "remaining_budget": target_step.rework_reserve,
            },
        }
    
    def _find_nearest_execute_step(self, workflow_id: str, current_sequence: int) -> Optional[WorkflowStep]:
        """找到最近的EXECUTE步骤"""
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.sequence < current_sequence,
            WorkflowStep.step_type == StepType.EXECUTE.value
        ).order_by(WorkflowStep.sequence.desc()).all()
        return steps[0] if steps else None
    
    def _advance_to_next_step(self, workflow: WorkflowInstance, current_sequence: int) -> WorkflowStep:
        """进入下一步"""
        next_step = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id,
            WorkflowStep.sequence > current_sequence
        ).order_by(WorkflowStep.sequence).first()
        
        if not next_step:
            raise ValueError("No next step found")
        
        next_step.status = StepStatus.ASSIGNED.value
        next_step.assigned_at = datetime.utcnow()
        self._notify_step_assignee(next_step)
        return next_step
    
    def handle_fuse(
        self, workflow_id: str, action: str, actor_id: str, params: Dict = None
    ) -> Dict:
        """处理熔断"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        if action == "ADD_BUDGET":
            additional = params.get("amount", 0)
            workflow.rework_budget += additional
            workflow.total_budget += additional
            workflow.remaining_budget += additional
            workflow.status = WorkflowStatus.REWORK.value
            
            self._add_history(workflow_id=workflow_id, action="ADD_REWORK_BUDGET", actor_id=actor_id, details={"amount": additional})
            self.db.commit()
            return {"success": True, "new_rework_budget": workflow.rework_budget}
        
        elif action == "FORCE_PASS":
            current_step = self._get_current_step(workflow_id)
            if current_step:
                current_step.status = StepStatus.COMPLETED.value
            workflow.status = WorkflowStatus.IN_PROGRESS.value
            
            if current_step:
                next_step = self._advance_to_next_step(workflow, current_step.sequence)
                workflow.current_step_index = next_step.sequence
            
            self._add_history(workflow_id=workflow_id, action="FORCE_PASS_FUSED", actor_id=actor_id)
            self.db.commit()
            return {"success": True, "action": "FORCE_PASS"}
        
        elif action == "RESTART":
            workflow.status = WorkflowStatus.PLANNING.value
            workflow.current_step_index = -1
            self.db.query(WorkflowStep).filter(WorkflowStep.workflow_id == workflow_id).delete()
            self._add_history(workflow_id=workflow_id, action="RESTART_FUSED", actor_id=actor_id)
            self.db.commit()
            return {"success": True, "action": "RESTART"}
        
        elif action == "CANCEL":
            workflow.status = WorkflowStatus.CANCELLED.value
            self._add_history(workflow_id=workflow_id, action="CANCEL_FUSED", actor_id=actor_id)
            self.db.commit()
            return {"success": True, "action": "CANCEL"}
        
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def _get_current_step(self, workflow_id: str) -> Optional[WorkflowStep]:
        """获取当前步骤"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        if not workflow or workflow.current_step_index < 0:
            return None
        return self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.sequence == workflow.current_step_index
        ).first()
    
    def _add_history(self, **kwargs):
        """添加历史记录"""
        history = WorkflowHistory(**kwargs)
        self.db.add(history)
    
    def _notify_step_assignee(self, step: WorkflowStep):
        """通知步骤负责人"""
        logger.info("notify_step", step_id=step.id, assignee_id=step.assignee_id)
    
    def _notify_rework(self, target_step: WorkflowStep, from_step: WorkflowStep, reason: str):
        """通知返工"""
        logger.info("notify_rework", target=target_step.id, from_step=from_step.id, reason=reason)
