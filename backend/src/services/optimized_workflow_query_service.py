"""
Optimized Workflow Query Service
优化后的工作流查询服务 - 解决N+1查询问题
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from models import Agent, WorkflowInstance, WorkflowStep
from models.workflow_engine import (
    WorkflowHistory, WorkflowReworkRecord,
    StepType, WorkflowStatus, StepStatus
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


class OptimizedWorkflowQueryService:
    """优化的工作流查询服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_workflow_detail_optimized(self, workflow_id: str, agent_id: str) -> Dict:
        """
        优化的工作流详情查询
        
        优化点:
        1. 使用 joinedload 预加载步骤的assignee信息，避免N+1查询
        2. 使用单个聚合查询计算进度统计
        """
        # 1. 获取工作流（基础信息）
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        # 2. 获取步骤（使用joinedload预加载assignee）
        steps = self.db.query(WorkflowStep).options(
            joinedload(WorkflowStep.assignee)
        ).filter(
            WorkflowStep.workflow_id == workflow_id
        ).order_by(WorkflowStep.sequence).all()
        
        # 3. 批量查询步骤统计（避免N+1）
        step_stats = self._get_workflow_step_stats(workflow_id)
        
        # 4. 获取历史记录（限制数量，避免大查询）
        history = self.db.query(WorkflowHistory).filter(
            WorkflowHistory.workflow_id == workflow_id
        ).order_by(WorkflowHistory.created_at.desc()).limit(50).all()
        
        # 5. 获取返工记录（限制数量）
        reworks = self.db.query(WorkflowReworkRecord).filter(
            WorkflowReworkRecord.workflow_id == workflow_id
        ).order_by(WorkflowReworkRecord.created_at.desc()).limit(20).all()
        
        # 6. 获取当前步骤
        current_step = None
        if workflow.current_step_index >= 0 and workflow.current_step_index < len(steps):
            current_step = steps[workflow.current_step_index]
        
        return {
            "workflow": self._serialize_workflow_optimized(workflow, step_stats),
            "steps": [self._serialize_step_optimized(s, agent_id) for s in steps],
            "history": [self._serialize_history(h) for h in history],
            "reworks": [self._serialize_rework(r) for r in reworks],
            "current_step": self._serialize_step_optimized(current_step, agent_id) if current_step else None,
            "can_operate": self._check_can_operate(workflow, agent_id),
            "available_actions": self._get_available_actions(workflow, current_step, agent_id),
        }
    
    def _get_workflow_step_stats(self, workflow_id: str) -> Dict:
        """使用聚合查询获取步骤统计（单次查询）"""
        result = self.db.query(
            func.count(WorkflowStep.id).label('total'),
            func.sum(
                func.case(
                    [(WorkflowStep.status == StepStatus.COMPLETED.value, 1)],
                    else_=0
                )
            ).label('completed')
        ).filter(
            WorkflowStep.workflow_id == workflow_id
        ).first()
        
        total = result.total or 0
        completed = result.completed or 0
        
        return {
            'total': total,
            'completed': completed,
            'progress': (completed / total * 100) if total > 0 else 0
        }
    
    def _serialize_workflow_optimized(self, workflow: WorkflowInstance, stats: Dict) -> Dict:
        """序列化工作流（使用预计算的统计）"""
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
            "progress": round(stats['progress'], 1),
            "completed_steps": stats['completed'],
            "total_steps": stats['total'],
        }
    
    def _serialize_step_optimized(self, step: WorkflowStep, viewer_id: str) -> Optional[Dict]:
        """序列化步骤（使用预加载的assignee）"""
        if not step:
            return None
        
        # 使用预加载的assignee，避免额外查询
        assignee_name = step.assignee.name if step.assignee else None
        assignee_emoji = step.assignee.emoji if step.assignee else None
        
        return {
            "id": step.id,
            "sequence": step.sequence,
            "name": step.name,
            "description": step.description,
            "step_type": step.step_type,
            "step_type_display": self._get_step_type_display(step.step_type),
            "status": step.status,
            "status_display": self._get_step_status_display(step.status),
            "assignee_id": step.assignee_id,
            "assignee_name": assignee_name,
            "assignee_emoji": assignee_emoji,
            "base_budget": step.base_budget,
            "rework_budget": step.rework_budget,
            "planned_hours": step.planned_hours,
            "actual_hours": step.actual_hours,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            "rework_count": step.rework_count,
            "is_current": False,  # 由调用者设置
            "can_operate": step.assignee_id == viewer_id and step.status in ["assigned", "rework"],
        }
    
    def get_workflow_list_optimized(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """
        优化的工作流列表查询（支持分页）
        
        Args:
            agent_id: 筛选特定员工参与的工作流
            status: 筛选状态
            page: 页码（从1开始）
            page_size: 每页数量
        """
        # 构建基础查询
        query = self.db.query(WorkflowInstance)
        
        # 应用筛选
        if agent_id:
            # 查询员工参与的工作流
            subquery = self.db.query(WorkflowStep.workflow_id).filter(
                WorkflowStep.assignee_id == agent_id
            ).distinct()
            query = query.filter(WorkflowInstance.id.in_(subquery))
        
        if status:
            query = query.filter(WorkflowInstance.status == status)
        
        # 计算总数
        total_count = query.count()
        
        # 分页
        workflows = query.order_by(
            WorkflowInstance.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()
        
        # 批量获取统计信息
        workflow_ids = [w.id for w in workflows]
        stats_map = self._get_workflows_stats_batch(workflow_ids)
        
        return {
            "workflows": [
                self._serialize_workflow_list(w, stats_map.get(w.id, {}))
                for w in workflows
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
    
    def _get_workflows_stats_batch(self, workflow_ids: List[str]) -> Dict[str, Dict]:
        """批量获取多个工作流的统计信息"""
        if not workflow_ids:
            return {}
        
        results = self.db.query(
            WorkflowStep.workflow_id,
            func.count(WorkflowStep.id).label('total'),
            func.sum(
                func.case(
                    [(WorkflowStep.status == StepStatus.COMPLETED.value, 1)],
                    else_=0
                )
            ).label('completed')
        ).filter(
            WorkflowStep.workflow_id.in_(workflow_ids)
        ).group_by(WorkflowStep.workflow_id).all()
        
        stats_map = {}
        for workflow_id, total, completed in results:
            total = total or 0
            completed = completed or 0
            stats_map[workflow_id] = {
                'total': total,
                'completed': completed,
                'progress': (completed / total * 100) if total > 0 else 0
            }
        
        return stats_map
    
    def _serialize_workflow_list(self, workflow: WorkflowInstance, stats: Dict) -> Dict:
        """列表视图序列化（简化字段）"""
        return {
            "id": workflow.id,
            "title": workflow.title,
            "status": workflow.status,
            "status_display": self._get_status_display(workflow.status),
            "owner_name": workflow.owner_name,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "progress": round(stats.get('progress', 0), 1),
            "completed_steps": stats.get('completed', 0),
            "total_steps": stats.get('total', 0),
            "remaining_budget": workflow.remaining_budget,
            "total_budget": workflow.total_budget,
        }
    
    def get_agent_pending_workflows_optimized(self, agent_id: str) -> List[Dict]:
        """
        优化的员工待办工作流查询
        
        使用JOIN一次性获取工作流和步骤信息
        """
        results = self.db.query(WorkflowStep, WorkflowInstance).join(
            WorkflowInstance,
            WorkflowStep.workflow_id == WorkflowInstance.id
        ).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.status.in_(["assigned", "in_progress", "rework"]),
            WorkflowInstance.status.in_(["in_progress", "rework"])
        ).order_by(
            WorkflowInstance.created_at.desc()
        ).all()
        
        return [
            {
                "step": {
                    "id": step.id,
                    "sequence": step.sequence,
                    "name": step.name,
                    "step_type": step.step_type,
                    "status": step.status,
                },
                "workflow": {
                    "id": workflow.id,
                    "title": workflow.title,
                    "status": workflow.status,
                }
            }
            for step, workflow in results
        ]
    
    # Helper methods
    def _get_status_display(self, status: str) -> str:
        """获取状态显示文本"""
        displays = {
            "draft": "草稿",
            "in_progress": "进行中",
            "completed": "已完成",
            "cancelled": "已取消",
            "fused": "已熔断",
            "rework": "返工中",
        }
        return displays.get(status, status)
    
    def _get_step_type_display(self, step_type: str) -> str:
        """获取步骤类型显示文本"""
        displays = {
            "PLAN": "规划",
            "EXECUTE": "执行",
            "REVIEW": "评审",
            "TEST": "测试",
            "APPROVE": "审批",
            "DOCUMENT": "文档",
        }
        return displays.get(step_type, step_type)
    
    def _get_step_status_display(self, status: str) -> str:
        """获取步骤状态显示文本"""
        displays = {
            "pending": "待分配",
            "assigned": "已分配",
            "in_progress": "进行中",
            "completed": "已完成",
            "rework": "返工中",
        }
        return displays.get(status, status)
    
    def _check_can_operate(self, workflow: WorkflowInstance, agent_id: str) -> bool:
        """检查用户是否可以操作工作流"""
        # Partner可以操作所有
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if agent and agent.position_level == 5:
            return True
        
        # 所有者可以操作
        if workflow.owner_id == agent_id:
            return True
        
        return False
    
    def _get_available_actions(self, workflow, current_step, agent_id: str) -> List[str]:
        """获取可用操作列表"""
        actions = []
        
        if not current_step:
            return actions
        
        if workflow.status not in ["in_progress", "rework"]:
            return actions
        
        # 如果是当前步骤负责人
        if current_step.assignee_id == agent_id:
            if current_step.status in ["assigned", "in_progress"]:
                actions.append("complete")
            if current_step.step_type in ["REVIEW", "TEST", "APPROVE"]:
                actions.append("review")
        
        # Partner或所有者可以处理熔断
        if self._check_can_operate(workflow, agent_id):
            if workflow.status == "fused":
                actions.extend(["force_pass", "add_budget", "restart", "cancel"])
        
        return actions
    
    def _serialize_history(self, history: WorkflowHistory) -> Dict:
        """序列化历史记录"""
        return {
            "id": history.id,
            "action": history.action,
            "step_id": history.step_id,
            "actor_id": history.actor_id,
            "details": history.details,
            "budget_impact": history.budget_impact,
            "created_at": history.created_at.isoformat() if history.created_at else None,
        }
    
    def _serialize_rework(self, rework: WorkflowReworkRecord) -> Dict:
        """序列化返工记录"""
        return {
            "id": rework.id,
            "from_step_id": rework.from_step_id,
            "to_step_id": rework.to_step_id,
            "reason": rework.reason,
            "budget_deducted": rework.budget_deducted,
            "created_at": rework.created_at.isoformat() if rework.created_at else None,
        }
