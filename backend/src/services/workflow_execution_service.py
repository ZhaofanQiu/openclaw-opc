"""
Workflow Execution Service v0.5.1 - 并行执行与返工预算
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
    """工作流执行服务 v0.5.1"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_workflow(self, workflow_id: str) -> WorkflowInstance:
        """启动工作流 - 支持并行步骤"""
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
        created_steps = {}
        
        for step_id, plan in step_plans.items():
            # 检查是否是并行容器
            if plan.get("parallel_steps"):
                # 创建并行容器步骤
                parent_step = self._create_step(workflow_id, plan, None)
                created_steps[step_id] = parent_step
                
                # 创建并行子步骤
                for sub_plan in plan["parallel_steps"]:
                    sub_step = self._create_step(
                        workflow_id, 
                        {**sub_plan, "sequence": plan["sequence"]},
                        parent_step.id
                    )
                    sub_step.parallel_group = parent_step.id
                    created_steps[sub_plan["step_id"]] = sub_step
            else:
                step = self._create_step(workflow_id, plan, None)
                created_steps[step_id] = step
        
        # 启动第一个（或第一批）步骤
        workflow.status = WorkflowStatus.IN_PROGRESS.value
        workflow.started_at = datetime.utcnow()
        
        # 找到第一个非并行子步骤
        first_steps = self._get_initial_steps(workflow_id)
        workflow.current_step_ids = [s.id for s in first_steps]
        
        for step in first_steps:
            step.status = StepStatus.ASSIGNED.value
            step.assigned_at = datetime.utcnow()
            self._notify_step_assignee(step)
        
        self._add_history(
            workflow_id=workflow_id,
            action="START_WORKFLOW",
            from_status=WorkflowStatus.PENDING.value,
            to_status=WorkflowStatus.IN_PROGRESS.value,
        )
        
        self.db.commit()
        logger.info("workflow_started", workflow_id=workflow_id, initial_steps=len(first_steps))
        return workflow
    
    def _create_step(self, workflow_id: str, plan: Dict, parent_id: str = None) -> WorkflowStep:
        """创建步骤实例"""
        step = WorkflowStep(
            id=str(__import__('uuid').uuid4())[:8],
            workflow_id=workflow_id,
            step_id=plan["step_id"],
            step_type=plan["step_type"],
            name=plan["name"],
            sequence=plan["sequence"],
            parent_step_id=parent_id,
            is_parallel="true" if parent_id else "false",
            assignee_id=plan.get("agent_id"),
            base_budget=plan.get("base_budget", 0),
            rework_reserve=plan.get("rework_reserve", 0),
            estimated_hours=plan.get("estimated_hours", 4),
            handbook=plan.get("handbook", ""),
            merge_condition=plan.get("merge_condition", "ALL"),
            rework_limit=plan.get("rework_limit", 3),
        )
        self.db.add(step)
        self.db.flush()
        return step
    
    def _get_initial_steps(self, workflow_id: str) -> List[WorkflowStep]:
        """获取初始步骤"""
        # 找到sequence最小的非并行子步骤
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.parent_step_id.is_(None)  # 不是并行子步骤
        ).order_by(WorkflowStep.sequence).all()
        
        if not steps:
            return []
        
        first_step = steps[0]
        
        # 如果是并行容器，返回其子步骤
        if first_step.step_type == StepType.PARALLEL.value:
            children = self.db.query(WorkflowStep).filter(
                WorkflowStep.parent_step_id == first_step.id
            ).all()
            return children
        
        return [first_step]
    
    def complete_step(
        self,
        step_id: str,
        action: str,  # PASS, REWORK
        result: Dict,
        actor_id: str,
    ) -> Dict:
        """完成步骤 - 处理并行和返工预算"""
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
        
        # 判断是首次执行还是返工
        if step.rework_count > 0:
            # 返工：从返工储备扣除
            budget_source = "rework"
            if budget_used > step.rework_reserve:
                # 返工预算不足
                return self._handle_rework_budget_insufficient(step, workflow, budget_used)
            step.rework_cost += budget_used
            step.rework_reserve -= budget_used
            workflow.used_rework_budget += budget_used
        else:
            # 首次：从基础预算扣除
            budget_source = "base"
            step.used_budget = budget_used
            workflow.used_base_budget += budget_used
        
        workflow.remaining_budget -= budget_used
        
        # 更新步骤
        step.result = result
        step.completed_at = datetime.utcnow()
        step.actual_hours = result.get("actual_hours", step.estimated_hours)
        
        if step.step_type == StepType.REVIEW.value:
            step.review_scores = result.get("review_scores", {})
        
        # 记录预算变动
        budget_impact = {
            "type": budget_source,
            "amount": budget_used,
            "step_budget_before": step.base_budget + step.rework_reserve + budget_used,
            "step_budget_after": step.base_budget + step.rework_reserve,
            "remaining_rework_budget": workflow.rework_budget - workflow.used_rework_budget,
        }
        
        if action == "PASS":
            return self._handle_pass(step, workflow, result, actor_id, budget_impact)
        elif action == "REWORK":
            return self._handle_rework(step, workflow, result, actor_id, budget_impact)
        else:
            raise ValueError(f"Invalid action: {action}")
    
    def _handle_rework_budget_insufficient(
        self, 
        step: WorkflowStep, 
        workflow: WorkflowInstance,
        required: float
    ) -> Dict:
        """处理返工预算不足"""
        available = step.rework_reserve
        
        workflow.status = WorkflowStatus.BUDGET_FUSED.value
        
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="REWORK_BUDGET_FUSED",
            details={
                "required": required,
                "available": available,
                "shortfall": required - available,
            },
        )
        
        self.db.commit()
        
        logger.warning(
            "rework_budget_fused",
            workflow_id=workflow.id,
            step_id=step.id,
            required=required,
            available=available,
        )
        
        return {
            "success": False,
            "fused": True,
            "fuse_type": "BUDGET",
            "message": f"返工预算不足：需要{required}，可用{available}",
            "options": [
                {"action": "ADD_BUDGET", "label": "追加预算"},
                {"action": "FORCE_PASS", "label": "强行通过"},
                {"action": "CANCEL", "label": "取消任务"},
            ],
        }
    
    def _handle_pass(
        self, 
        step: WorkflowStep, 
        workflow: WorkflowInstance,
        result: Dict,
        actor_id: str,
        budget_impact: Dict,
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
        
        # 检查是否是并行步骤
        if step.parallel_group:
            return self._handle_parallel_step_complete(step, workflow, budget_impact)
        
        # 检查是否是最后一步
        is_last = self._is_last_step(workflow.id, step.sequence)
        if is_last:
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.completed_at = datetime.utcnow()
            workflow.current_step_ids = []
            
            self._add_history(
                workflow_id=workflow.id,
                action="COMPLETE_WORKFLOW",
                from_status=WorkflowStatus.IN_PROGRESS.value,
                to_status=WorkflowStatus.COMPLETED.value,
            )
            
            self.db.commit()
            return {"success": True, "workflow_completed": True}
        
        # 进入下一步
        next_steps = self._advance_to_next_steps(workflow, step.sequence)
        workflow.current_step_ids = [s.id for s in next_steps]
        
        self.db.commit()
        
        return {
            "success": True,
            "workflow_completed": False,
            "next_steps": [{"id": s.id, "name": s.name, "type": s.step_type} for s in next_steps],
        }
    
    def _handle_parallel_step_complete(
        self,
        step: WorkflowStep,
        workflow: WorkflowInstance,
        budget_impact: Dict,
    ) -> Dict:
        """处理并行步骤完成"""
        # 获取该并行组的所有子步骤
        siblings = self.db.query(WorkflowStep).filter(
            WorkflowStep.parallel_group == step.parallel_group
        ).all()
        
        # 检查合并条件
        parent_step = self.db.query(WorkflowStep).filter(
            WorkflowStep.id == step.parallel_group
        ).first()
        
        merge_condition = parent_step.merge_condition if parent_step else "ALL"
        
        completed_count = sum(1 for s in siblings if s.status == StepStatus.COMPLETED.value)
        total_count = len(siblings)
        
        if merge_condition == "ALL" and completed_count < total_count:
            # 等待其他步骤
            step.status = StepStatus.WAITING.value
            self.db.commit()
            
            return {
                "success": True,
                "parallel_waiting": True,
                "message": f"等待其他并行步骤 ({completed_count}/{total_count})",
            }
        
        # 全部完成，标记父步骤完成并继续
        if parent_step:
            parent_step.status = StepStatus.COMPLETED.value
            parent_step.completed_at = datetime.utcnow()
        
        # 继续后续步骤
        next_steps = self._advance_to_next_steps(workflow, parent_step.sequence if parent_step else step.sequence)
        workflow.current_step_ids = [s.id for s in next_steps]
        
        self.db.commit()
        
        return {
            "success": True,
            "parallel_completed": True,
            "next_steps": [{"id": s.id, "name": s.name} for s in next_steps],
        }
    
    def _handle_rework(
        self,
        step: WorkflowStep,
        workflow: WorkflowInstance,
        result: Dict,
        actor_id: str,
        budget_impact: Dict,
    ) -> Dict:
        """处理返工 - 双熔断检查"""
        # 1. 返工次数熔断检查
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
        if step.parallel_group:
            # 并行步骤返工：返工到其父步骤对应的EXECUTE
            target_step = self._find_rework_target_for_parallel(step, workflow.id)
        else:
            # 普通步骤返工：最近的EXECUTE
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
        
        # 记录返工
        rework_record = WorkflowReworkRecord(
            workflow_id=workflow.id,
            from_step_id=step.id,
            to_step_id=target_step.id,
            triggered_by=actor_id,
            reason=result.get("comment", ""),
            review_scores=step.review_scores if step.step_type == StepType.REVIEW.value else {},
            cost=budget_impact.get("amount", 0),
            rework_budget_before=budget_impact.get("step_budget_before", 0),
            rework_budget_after=budget_impact.get("step_budget_after", 0),
        )
        self.db.add(rework_record)
        
        # 更新当前步骤
        workflow.current_step_ids = [target_step.id]
        
        self._add_history(
            workflow_id=workflow.id,
            step_id=step.id,
            action="REWORK_TRIGGERED",
            actor_id=actor_id,
            details={
                "to_step": target_step.id,
                "rework_count": target_step.rework_count,
                "rework_limit": target_step.rework_limit,
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
                "remaining_rework_budget": target_step.rework_reserve,
            },
        }
    
    def _find_rework_target_for_parallel(
        self, 
        step: WorkflowStep, 
        workflow_id: str
    ) -> Optional[WorkflowStep]:
        """为并行步骤找到返工目标"""
        # 返工到该并行步骤本身（重新执行）
        return step
    
    def _find_nearest_execute_step(self, workflow_id: str, current_sequence: int) -> Optional[WorkflowStep]:
        """找到最近的EXECUTE步骤"""
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.sequence < current_sequence,
            WorkflowStep.step_type == StepType.EXECUTE.value
        ).order_by(WorkflowStep.sequence.desc()).all()
        
        return steps[0] if steps else None
    
    def _is_last_step(self, workflow_id: str, current_sequence: int) -> bool:
        """检查是否是最后一步"""
        next_step = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
            WorkflowStep.sequence > current_sequence,
            WorkflowStep.parent_step_id.is_(None)  # 不是并行子步骤
        ).first()
        return next_step is None
    
    def _advance_to_next_steps(self, workflow: WorkflowInstance, current_sequence: int) -> List[WorkflowStep]:
        """进入下一步（支持并行）"""
        next_step = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id,
            WorkflowStep.sequence > current_sequence,
            WorkflowStep.parent_step_id.is_(None)
        ).order_by(WorkflowStep.sequence).first()
        
        if not next_step:
            return []
        
        # 如果是并行容器，返回其子步骤
        if next_step.step_type == StepType.PARALLEL.value:
            children = self.db.query(WorkflowStep).filter(
                WorkflowStep.parent_step_id == next_step.id
            ).all()
            for child in children:
                child.status = StepStatus.ASSIGNED.value
                child.assigned_at = datetime.utcnow()
                self._notify_step_assignee(child)
            return children
        
        next_step.status = StepStatus.ASSIGNED.value
        next_step.assigned_at = datetime.utcnow()
        self._notify_step_assignee(next_step)
        return [next_step]
    
    def handle_fuse(
        self,
        workflow_id: str,
        action: str,  # ADD_BUDGET, FORCE_PASS, RESTART, CANCEL
        actor_id: str,
        params: Dict = None,
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
            
            self._add_history(
                workflow_id=workflow_id,
                action="ADD_REWORK_BUDGET",
                actor_id=actor_id,
                details={"amount": additional},
            )
            
            self.db.commit()
            return {"success": True, "action": "ADD_BUDGET", "new_budget": workflow.rework_budget}
        
        elif action == "FORCE_PASS":
            # 强行通过当前步骤
            current_steps = self.db.query(WorkflowStep).filter(
                WorkflowStep.id.in_(workflow.current_step_ids)
            ).all()
            
            for step in current_steps:
                step.status = StepStatus.COMPLETED.value
                step.result = {"action": "FORCE_PASS", "fused_bypassed": True}
            
            workflow.status = WorkflowStatus.IN_PROGRESS.value
            
            # 找到下一步
            if current_steps:
                next_steps = self._advance_to_next_steps(workflow, current_steps[0].sequence)
                workflow.current_step_ids = [s.id for s in next_steps]
            
            self._add_history(
                workflow_id=workflow_id,
                action="FORCE_PASS_FUSED",
                actor_id=actor_id,
            )
            
            self.db.commit()
            return {"success": True, "action": "FORCE_PASS"}
        
        elif action == "RESTART":
            # 重新规划
            workflow.status = WorkflowStatus.PLANNING.value
            workflow.current_step_ids = []
            
            self.db.query(WorkflowStep).filter(
                WorkflowStep.workflow_id == workflow_id
            ).delete()
            
            self._add_history(
                workflow_id=workflow_id,
                action="RESTART_FUSED",
                actor_id=actor_id,
            )
            
            self.db.commit()
            return {"success": True, "action": "RESTART"}
        
        elif action == "CANCEL":
            workflow.status = WorkflowStatus.CANCELLED.value
            
            self._add_history(
                workflow_id=workflow_id,
                action="CANCEL_FUSED",
                actor_id=actor_id,
            )
            
            self.db.commit()
            return {"success": True, "action": "CANCEL"}
        
        else:
            raise ValueError(f"Invalid action: {action}")
    
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
