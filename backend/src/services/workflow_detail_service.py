"""
Workflow Detail Service v0.5.8

工作流详情服务 - 提供完整的步骤详情和操作
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from models import Agent, WorkflowInstance, WorkflowStep
from models.workflow_engine import (
    WorkflowHistory, WorkflowReworkRecord,
    StepType, WorkflowStatus, StepStatus
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowDetailService:
    """工作流详情服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_workflow_detail(self, workflow_id: str, agent_id: str) -> Dict:
        """获取工作流详情"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        # 获取所有步骤
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id
        ).order_by(WorkflowStep.sequence).all()
        
        # 获取历史记录
        history = self.db.query(WorkflowHistory).filter(
            WorkflowHistory.workflow_id == workflow_id
        ).order_by(WorkflowHistory.created_at.desc()).all()
        
        # 获取返工记录
        reworks = self.db.query(WorkflowReworkRecord).filter(
            WorkflowReworkRecord.workflow_id == workflow_id
        ).order_by(WorkflowReworkRecord.created_at.desc()).all()
        
        # 确定当前用户是否可以操作
        can_operate = self._check_can_operate(workflow, agent_id)
        
        # 获取当前步骤
        current_step = None
        if workflow.current_step_index >= 0 and workflow.current_step_index < len(steps):
            current_step = steps[workflow.current_step_index]
        
        return {
            "workflow": self._serialize_workflow(workflow),
            "steps": [self._serialize_step(s, agent_id) for s in steps],
            "history": [self._serialize_history(h) for h in history],
            "reworks": [self._serialize_rework(r) for r in reworks],
            "current_step": self._serialize_step(current_step, agent_id) if current_step else None,
            "can_operate": can_operate,
            "available_actions": self._get_available_actions(workflow, current_step, agent_id),
        }
    
    def get_step_detail(self, step_id: str, agent_id: str) -> Dict:
        """获取步骤详情"""
        step = self.db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step:
            raise ValueError(f"Step '{step_id}' not found")
        
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == step.workflow_id
        ).first()
        
        # 获取该步骤的历史记录
        step_history = self.db.query(WorkflowHistory).filter(
            WorkflowHistory.workflow_id == step.workflow_id,
            WorkflowHistory.step_id == step.id
        ).order_by(WorkflowHistory.created_at.desc()).all()
        
        # 获取该步骤的返工记录
        step_reworks = self.db.query(WorkflowReworkRecord).filter(
            WorkflowReworkRecord.workflow_id == step.workflow_id,
            (WorkflowReworkRecord.from_step_id == step.id) | 
            (WorkflowReworkRecord.to_step_id == step.id)
        ).order_by(WorkflowReworkRecord.created_at.desc()).all()
        
        return {
            "step": self._serialize_step_detail(step),
            "workflow": {
                "id": workflow.id,
                "title": workflow.title,
                "status": workflow.status,
            },
            "history": [self._serialize_history(h) for h in step_history],
            "reworks": [self._serialize_rework(r) for r in step_reworks],
            "can_operate": step.assignee_id == agent_id and step.status in ["assigned", "rework"],
            "can_review": self._can_review(step, agent_id),
        }
    
    def _serialize_workflow(self, workflow: WorkflowInstance) -> Dict:
        """序列化工作流"""
        total_steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id
        ).count()
        
        completed_steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id,
            WorkflowStep.status == "completed"
        ).count()
        
        progress = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        return {
            "id": workflow.id,
            "title": workflow.title,
            "description": workflow.description,
            "status": workflow.status,
            "status_display": self._get_status_display(workflow.status),
            "template_id": workflow.template_id,
            "owner_id": workflow.owner_id,
            "owner_name": workflow.owner_name,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "total_budget": workflow.total_budget,
            "base_budget": workflow.base_budget,
            "rework_budget": workflow.rework_budget,
            "used_base_budget": workflow.used_base_budget,
            "used_rework_budget": workflow.used_rework_budget,
            "remaining_budget": workflow.remaining_budget,
            "total_rework_count": workflow.total_rework_count,
            "current_step_index": workflow.current_step_index,
            "progress": round(progress, 1),
            "completed_steps": completed_steps,
            "total_steps": total_steps,
        }
    
    def _serialize_step(self, step: WorkflowStep, viewer_id: str) -> Dict:
        """序列化步骤（列表视图）"""
        if not step:
            return None
        
        assignee = self.db.query(Agent).filter(Agent.id == step.assignee_id).first()
        
        return {
            "id": step.id,
            "name": step.name,
            "step_type": step.step_type,
            "step_type_display": self._get_step_type_display(step.step_type),
            "sequence": step.sequence,
            "status": step.status,
            "status_display": self._get_step_status_display(step.status),
            "assignee_id": step.assignee_id,
            "assignee_name": assignee.name if assignee else "未分配",
            "assignee_avatar": assignee.avatar_url if assignee else None,
            "is_assigned_to_me": step.assignee_id == viewer_id,
            "base_budget": step.base_budget,
            "rework_reserve": step.rework_reserve,
            "used_budget": step.used_budget,
            "rework_cost": step.rework_cost,
            "rework_count": step.rework_count,
            "rework_limit": step.rework_limit,
            "estimated_hours": step.estimated_hours,
            "actual_hours": step.actual_hours,
            "assigned_at": step.assigned_at.isoformat() if step.assigned_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            "is_current": False,  # 由调用方设置
        }
    
    def _serialize_step_detail(self, step: WorkflowStep) -> Dict:
        """序列化步骤详情"""
        assignee = self.db.query(Agent).filter(Agent.id == step.assignee_id).first()
        
        return {
            "id": step.id,
            "name": step.name,
            "step_type": step.step_type,
            "step_type_display": self._get_step_type_display(step.step_type),
            "sequence": step.sequence,
            "status": step.status,
            "status_display": self._get_step_status_display(step.status),
            "assignee_id": step.assignee_id,
            "assignee_name": assignee.name if assignee else "未分配",
            "assignee_avatar": assignee.avatar_url if assignee else None,
            "base_budget": step.base_budget,
            "rework_reserve": step.rework_reserve,
            "used_budget": step.used_budget,
            "rework_cost": step.rework_cost,
            "rework_count": step.rework_count,
            "rework_limit": step.rework_limit,
            "estimated_hours": step.estimated_hours,
            "actual_hours": step.actual_hours,
            "handbook": step.handbook,
            "input_artifacts": step.input_artifacts,
            "output_artifacts": step.output_artifacts,
            "result": step.result,
            "review_scores": step.review_scores,
            "is_rework": step.is_rework == "true",
            "assigned_at": step.assigned_at.isoformat() if step.assigned_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        }
    
    def _serialize_history(self, history: WorkflowHistory) -> Dict:
        """序列化历史记录"""
        actor = self.db.query(Agent).filter(Agent.id == history.actor_id).first()
        
        return {
            "id": history.id,
            "action": history.action,
            "from_status": history.from_status,
            "to_status": history.to_status,
            "actor_id": history.actor_id,
            "actor_name": actor.name if actor else "系统",
            "details": history.details,
            "budget_impact": history.budget_impact,
            "created_at": history.created_at.isoformat() if history.created_at else None,
        }
    
    def _serialize_rework(self, rework: WorkflowReworkRecord) -> Dict:
        """序列化返工记录"""
        from_step = self.db.query(WorkflowStep).filter(WorkflowStep.id == rework.from_step_id).first()
        to_step = self.db.query(WorkflowStep).filter(WorkflowStep.id == rework.to_step_id).first()
        triggered_by = self.db.query(Agent).filter(Agent.id == rework.triggered_by).first()
        
        return {
            "id": rework.id,
            "from_step_name": from_step.name if from_step else "未知",
            "to_step_name": to_step.name if to_step else "未知",
            "triggered_by_name": triggered_by.name if triggered_by else "未知",
            "reason": rework.reason,
            "cost": rework.cost,
            "rework_budget_before": rework.rework_budget_before,
            "rework_budget_after": rework.rework_budget_after,
            "created_at": rework.created_at.isoformat() if rework.created_at else None,
        }
    
    def _check_can_operate(self, workflow: WorkflowInstance, agent_id: str) -> bool:
        """检查用户是否可以操作工作流"""
        # Partner总是可以操作
        partner = self.db.query(Agent).filter(
            Agent.id == agent_id,
            Agent.position_level == 5
        ).first()
        if partner:
            return True
        
        # 工作流所有者可以操作
        if workflow.owner_id == agent_id:
            return True
        
        return False
    
    def _can_review(self, step: WorkflowStep, agent_id: str) -> bool:
        """检查用户是否可以评审此步骤"""
        if step.step_type != StepType.REVIEW.value:
            return False
        
        if step.status not in ["assigned", "rework"]:
            return False
        
        # 只有被分配的评审者可以评审
        return step.assignee_id == agent_id
    
    def _get_available_actions(self, workflow: WorkflowInstance, current_step: WorkflowStep, agent_id: str) -> List[Dict]:
        """获取可用操作列表"""
        actions = []
        
        if not current_step:
            return actions
        
        # 启动工作流
        if workflow.status == WorkflowStatus.PENDING.value and self._check_can_operate(workflow, agent_id):
            actions.append({
                "action": "START",
                "label": "启动工作流",
                "icon": "▶️",
                "description": "开始执行工作流"
            })
        
        # 当前步骤操作
        if current_step.assignee_id == agent_id:
            if current_step.status in ["assigned", "rework"]:
                if current_step.step_type == StepType.EXECUTE.value:
                    actions.append({
                        "action": "COMPLETE",
                        "label": "完成任务",
                        "icon": "✅",
                        "description": "提交任务结果"
                    })
                elif current_step.step_type == StepType.REVIEW.value:
                    actions.append({
                        "action": "PASS",
                        "label": "通过",
                        "icon": "✓",
                        "description": "评审通过，进入下一步"
                    })
                    actions.append({
                        "action": "REWORK",
                        "label": "返工",
                        "icon": "↩️",
                        "description": "要求返工到之前的步骤"
                    })
        
        # 熔断后操作
        if workflow.status in [WorkflowStatus.BUDGET_FUSED.value, WorkflowStatus.REWORK_FUSED.value]:
            if self._check_can_operate(workflow, agent_id):
                actions.append({
                    "action": "FORCE_PASS",
                    "label": "强行通过",
                    "icon": "⚡",
                    "description": "忽略限制，强制通过"
                })
                actions.append({
                    "action": "ADD_BUDGET",
                    "label": "追加预算",
                    "icon": "💰",
                    "description": "增加返工预算继续"
                })
                actions.append({
                    "action": "CANCEL",
                    "label": "取消工作流",
                    "icon": "🚫",
                    "description": "终止此工作流"
                })
        
        # 取消工作流
        if workflow.status in [WorkflowStatus.PENDING.value, WorkflowStatus.IN_PROGRESS.value, WorkflowStatus.REWORK.value]:
            if self._check_can_operate(workflow, agent_id):
                actions.append({
                    "action": "CANCEL",
                    "label": "取消工作流",
                    "icon": "🚫",
                    "description": "终止此工作流",
                    "danger": True
                })
        
        return actions
    
    def _get_status_display(self, status: str) -> str:
        """获取状态显示文本"""
        status_map = {
            "pending": "待启动",
            "in_progress": "进行中",
            "rework": "返工中",
            "completed": "已完成",
            "cancelled": "已取消",
            "budget_fused": "预算熔断",
            "rework_fused": "返工熔断",
        }
        return status_map.get(status, status)
    
    def _get_step_type_display(self, step_type: str) -> str:
        """获取步骤类型显示文本"""
        type_map = {
            "PLAN": "规划",
            "EXECUTE": "执行",
            "REVIEW": "评审",
            "TEST": "测试",
            "APPROVE": "审批",
            "DOCUMENT": "文档",
        }
        return type_map.get(step_type, step_type)
    
    def _get_step_status_display(self, status: str) -> str:
        """获取步骤状态显示文本"""
        status_map = {
            "pending": "待分配",
            "assigned": "已分配",
            "rework": "返工中",
            "completed": "已完成",
        }
        return status_map.get(status, status)
