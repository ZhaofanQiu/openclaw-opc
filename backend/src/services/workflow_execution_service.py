"""
Workflow Engine Execution Service

工作流执行核心：启动、步骤流转、完成、返工
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
    """工作流执行服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_workflow(self, workflow_id: str) -> WorkflowInstance:
        """启动工作流，创建第一步"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        if workflow.status != WorkflowStatus.PENDING.value:
            raise ValueError(f"Cannot start workflow with status '{workflow.status}'")
        
        if not workflow.plan_result:
            raise ValueError("Workflow must be planned before starting")
        
        # 创建步骤实例
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
                allocated_budget=plan["budget"],
                estimated_hours=plan["estimated_hours"],
                handbook=plan["handbook"],
                rework_limit=plan.get("rework_limit", 3),
            )
            self.db.add(step)
        
        # 启动第一个步骤
        workflow.status = WorkflowStatus.IN_PROGRESS.value
        workflow.started_at = datetime.utcnow()
        workflow.current_step_index = 0
        
        self.db.commit()
        
        # 获取第一个步骤并通知负责人
        first_step = self._get_current_step(workflow_id)
        if first_step:
            self._notify_step_assignee(first_step)
        
        # 记录历史
        self._add_history(
            workflow_id=workflow_id,
            action="START_WORKFLOW",
            from_status=WorkflowStatus.PENDING.value,
            to_status=WorkflowStatus.IN_PROGRESS.value,
        )
        
        logger.info("workflow_started", workflow_id=workflow_id)
        return workflow
    
    def complete_step(
        self,
        step_id: str,
        action: str,  # PASS, REWORK
        result: Dict,
        actor_id: str,
    ) -> Dict:
        """
        完成当前步骤
        
        Args:
            step_id: 步骤ID
            action: PASS(通过)/REWORK(返工)
            result: 结果数据
            actor_id: 执行者ID
        
        Returns:
            执行结果，包含下一步信息
        """
        step = self.db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step:
            raise ValueError(f"Step '{step_id}' not found")
        
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == step.workflow_id
        ).first()
        
        # 验证权限
        if step.assignee_id != actor_id:
            # 检查是否是Partner
            actor = self.db.query(Agent).filter(Agent.id == actor_id).first()
            from src.models.agent import PositionLevel
            if not actor or actor.position_level != PositionLevel.PARTNER.value:
                raise ValueError("Only assignee or Partner can complete step")
        
        # 更新步骤结果
        step.result = result
        step.completed_at = datetime.utcnow()
        step.actual_hours = result.get("actual_hours", step.estimated_hours)
        
        # 更新预算使用
        budget_used = result.get("budget_used", step.allocated_budget)
        step.used_budget = budget_used
        workflow.used_budget += budget_used
        workflow.remaining_budget -= budget_used
        
        # REVIEW类型：保存评分
        if step.step_type == StepType.REVIEW.value:
            step.review_scores = result.get("review_scores", {})
        
        if action == "PASS":
            return self._handle_pass(step, workflow, result, actor_id)
        elif action == "REWORK":
            return self._handle_rework(step, workflow, result, actor_id)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def _handle_pass(
        self, 
        step: WorkflowStep, 
        workflow: WorkflowInstance,
        result: Dict,
        actor_id: str,
    ) -> Dict:
        """处理通过"""
        step.status = StepStatus.COMPLETED.value
        
        # 记录历史
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="COMPLETE_STEP",
            actor_id=actor_id,
            from_status=StepStatus.IN_PROGRESS.value,
            to_status=StepStatus.COMPLETED.value,
            details={"action": "PASS", "result": result},
        )
        
        # 检查是否是最后一步
        total_steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id
        ).count()
        
        if step.sequence >= total_steps - 1:
            # 流程完成
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
            logger.info("workflow_completed", workflow_id=workflow.id)
            
            return {
                "success": True,
                "workflow_completed": True,
                "message": "Workflow completed successfully",
            }
        
        # 进入下一步
        next_step = self._advance_to_next_step(workflow, step.sequence)
        
        self.db.commit()
        
        return {
            "success": True,
            "workflow_completed": False,
            "next_step": {
                "id": next_step.id,
                "name": next_step.name,
                "type": next_step.step_type,
                "assignee": next_step.assignee.name if next_step.assignee else None,
            },
        }
    
    def _handle_rework(
        self,
        step: WorkflowStep,
        workflow: WorkflowInstance,
        result: Dict,
        actor_id: str,
    ) -> Dict:
        """处理返工"""
        # 找到最近的EXECUTE步骤
        target_step = self._find_nearest_execute_step(workflow.id, step.sequence)
        
        if not target_step:
            raise ValueError("No EXECUTE step found to rework to")
        
        # 检查返工次数
        if target_step.rework_count >= target_step.rework_limit:
            # 返工超限，进入预警状态
            workflow.status = WorkflowStatus.WARNING.value
            workflow.total_rework_count += 1
            
            self._add_history(
                workflow_id=workflow.id,
                step_id=step.id,
                action="REWORK_LIMIT_EXCEEDED",
                actor_id=actor_id,
                details={
                    "target_step": target_step.id,
                    "rework_count": target_step.rework_count,
                    "rework_limit": target_step.rework_limit,
                },
            )
            
            self.db.commit()
            
            logger.warning(
                "rework_limit_exceeded",
                workflow_id=workflow.id,
                step_id=target_step.id,
                count=target_step.rework_count,
            )
            
            return {
                "success": False,
                "warning": True,
                "message": f"Rework limit exceeded ({target_step.rework_count}/{target_step.rework_limit})",
                "options": [
                    {"action": "FORCE_PASS", "label": "强行通过"},
                    {"action": "RESTART", "label": "编辑任务后重新启动"},
                    {"action": "ESCALATE", "label": "升级给Partner处理"},
                ],
            }
        
        # 执行返工
        target_step.status = StepStatus.REWORK.value
        target_step.rework_count += 1
        target_step.is_rework = "true"
        target_step.rework_from_step_id = step.id
        
        workflow.status = WorkflowStatus.REWORK.value
        workflow.total_rework_count += 1
        workflow.current_step_index = target_step.sequence
        
        # 记录返工记录
        rework_record = WorkflowReworkRecord(
            workflow_id=workflow.id,
            from_step_id=step.id,
            to_step_id=target_step.id,
            triggered_by=actor_id,
            reason=result.get("comment", ""),
            review_scores=step.review_scores if step.step_type == StepType.REVIEW.value else {},
        )
        self.db.add(rework_record)
        
        # 记录历史
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="REWORK_TRIGGERED",
            actor_id=actor_id,
            from_status=step.status,
            to_status=StepStatus.REWORK.value,
            details={
                "from_step": step.id,
                "to_step": target_step.id,
                "reason": result.get("comment", ""),
                "rework_count": target_step.rework_count,
            },
        )
        
        self.db.commit()
        
        # 通知被返工的员工
        self._notify_rework(target_step, step, result.get("comment", ""))
        
        logger.info(
            "rework_triggered",
            workflow_id=workflow.id,
            from_step=step.id,
            to_step=target_step.id,
            count=target_step.rework_count,
        )
        
        return {
            "success": True,
            "rework": True,
            "message": f"Rework assigned to step '{target_step.name}'",
            "rework_step": {
                "id": target_step.id,
                "name": target_step.name,
                "assignee": target_step.assignee.name if target_step.assignee else None,
                "rework_count": target_step.rework_count,
                "rework_limit": target_step.rework_limit,
            },
            "triggered_by": {
                "step_id": step.id,
                "step_name": step.name,
                "comment": result.get("comment", ""),
            },
        }
    
    def _find_nearest_execute_step(self, workflow_id: str, current_sequence: int) -> Optional[WorkflowStep]:
        """找到最近的EXECUTE步骤（向前查找）"""
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.sequence < current_sequence,
            WorkflowStep.step_type == StepType.EXECUTE.value
        ).order_by(WorkflowStep.sequence.desc()).all()
        
        return steps[0] if steps else None
    
    def _advance_to_next_step(
        self, 
        workflow: WorkflowInstance, 
        current_sequence: int
    ) -> WorkflowStep:
        """进入下一步"""
        next_step = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id,
            WorkflowStep.sequence > current_sequence
        ).order_by(WorkflowStep.sequence).first()
        
        if not next_step:
            raise ValueError("No next step found")
        
        workflow.current_step_index = next_step.sequence
        next_step.status = StepStatus.ASSIGNED.value
        next_step.assigned_at = datetime.utcnow()
        
        # 通知
        self._notify_step_assignee(next_step)
        
        return next_step
    
    def handle_rework_warning(
        self,
        workflow_id: str,
        action: str,  # FORCE_PASS, RESTART, ESCALATE
        actor_id: str,
        reason: str = "",
    ) -> Dict:
        """处理返工超限的预警"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        if workflow.status != WorkflowStatus.WARNING.value:
            raise ValueError("Workflow is not in WARNING status")
        
        if action == "FORCE_PASS":
            # 强行通过当前步骤
            current_step = self._get_current_step(workflow_id)
            if current_step:
                current_step.status = StepStatus.COMPLETED.value
                current_step.result = {
                    "action": "FORCE_PASS",
                    "reason": reason,
                    "warning_bypassed": True,
                }
            
            # 恢复流程
            workflow.status = WorkflowStatus.IN_PROGRESS.value
            
            # 进入下一步
            next_step = self._advance_to_next_step(workflow, current_step.sequence)
            
            self._add_history(
                workflow_id=workflow_id,
                action="FORCE_PASS",
                actor_id=actor_id,
                details={"reason": reason},
            )
            
            self.db.commit()
            
            return {
                "success": True,
                "action": "FORCE_PASS",
                "message": "Step force passed",
                "next_step": {
                    "id": next_step.id,
                    "name": next_step.name,
                },
            }
        
        elif action == "RESTART":
            # 重新规划并启动
            workflow.status = WorkflowStatus.PLANNING.value
            workflow.current_step_index = -1
            
            # 清除现有步骤
            self.db.query(WorkflowStep).filter(
                WorkflowStep.workflow_id == workflow_id
            ).delete()
            
            self._add_history(
                workflow_id=workflow_id,
                action="RESTART_WORKFLOW",
                actor_id=actor_id,
                details={"reason": reason},
            )
            
            self.db.commit()
            
            return {
                "success": True,
                "action": "RESTART",
                "message": "Workflow restarted, needs re-planning",
            }
        
        elif action == "ESCALATE":
            # 升级给Partner
            partner = self.db.query(Agent).filter(
                Agent.position_level == "PARTNER"
            ).first()
            
            if partner:
                # 通知Partner处理
                self._notify_partner_escalation(workflow, partner, reason)
            
            self._add_history(
                workflow_id=workflow_id,
                action="ESCALATE",
                actor_id=actor_id,
                details={"reason": reason},
            )
            
            self.db.commit()
            
            return {
                "success": True,
                "action": "ESCALATE",
                "message": "Escalated to Partner",
            }
        
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
    
    def _add_history(
        self,
        workflow_id: str,
        action: str,
        step_id: str = None,
        actor_id: str = None,
        from_status: str = None,
        to_status: str = None,
        details: Dict = None,
    ):
        """添加历史记录"""
        history = WorkflowHistory(
            workflow_id=workflow_id,
            step_id=step_id,
            action=action,
            actor_id=actor_id,
            from_status=from_status,
            to_status=to_status,
            details=details or {},
        )
        self.db.add(history)
    
    def _notify_step_assignee(self, step: WorkflowStep):
        """通知步骤负责人"""
        # TODO: 集成消息系统
        logger.info(
            "notify_step_assignee",
            step_id=step.id,
            assignee_id=step.assignee_id,
            step_name=step.name,
        )
    
    def _notify_rework(self, target_step: WorkflowStep, from_step: WorkflowStep, reason: str):
        """通知返工"""
        logger.info(
            "notify_rework",
            target_step=target_step.id,
            assignee_id=target_step.assignee_id,
            from_step=from_step.id,
            reason=reason,
        )
    
    def _notify_partner_escalation(self, workflow: WorkflowInstance, partner: Agent, reason: str):
        """通知Partner升级"""
        logger.info(
            "notify_partner_escalation",
            workflow_id=workflow.id,
            partner_id=partner.id,
            reason=reason,
        )
