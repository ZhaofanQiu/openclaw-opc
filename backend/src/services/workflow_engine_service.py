"""
Workflow Engine Service v0.5.2 - 纯串行执行
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Agent, WorkflowTemplate, WorkflowInstance, WorkflowStep
from src.models.workflow_engine import (
    StepType, WorkflowStatus, StepStatus,
    WorkflowHistory, WorkflowReworkRecord
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowEngineService:
    """工作流引擎服务 v0.5.2 - 纯串行"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_workflow(
        self,
        title: str,
        description: str,
        total_budget: float,
        created_by: str,
        template_id: str = None,
        rework_budget_ratio: float = 0.2,
    ) -> WorkflowInstance:
        """创建工作流 - 含返工预算分配"""
        base_budget = total_budget * (1 - rework_budget_ratio)
        rework_budget = total_budget * rework_budget_ratio
        
        workflow = WorkflowInstance(
            id=str(uuid.uuid4())[:8],
            template_id=template_id,
            title=title,
            description=description,
            status=WorkflowStatus.PLANNING.value,
            total_budget=total_budget,
            base_budget=base_budget,
            rework_budget=rework_budget,
            remaining_budget=total_budget,
            created_by=created_by,
            current_step_index=-1,
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        
        logger.info("workflow_created", 
                   workflow_id=workflow.id, 
                   total=total_budget,
                   base=base_budget,
                   rework=rework_budget)
        return workflow
    
    def auto_plan_workflow(self, workflow_id: str) -> Dict:
        """Partner自动规划"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        # 串行流程
        steps_config = self._create_serial_flow(workflow)
        
        # 分配预算
        step_plans = self._allocate_step_budgets(
            steps_config, 
            workflow.base_budget,
            workflow.rework_budget
        )
        
        # 匹配员工
        for step_id, plan in step_plans.items():
            assignee = self._match_agent_for_step(plan, workflow)
            plan["agent_id"] = assignee.id if assignee else None
            plan["agent_name"] = assignee.name if assignee else None
            plan["handbook"] = self._generate_step_handbook(plan, workflow, assignee)
        
        plan_result = {
            "analysis": self._analyze_requirements(workflow),
            "selected_steps": list(step_plans.keys()),
            "step_plans": step_plans,
            "budget_summary": {
                "total": workflow.total_budget,
                "base": workflow.base_budget,
                "rework_reserve": workflow.rework_budget,
            },
            "handbook": self._generate_full_handbook(workflow, step_plans),
        }
        
        workflow.plan_result = plan_result
        workflow.status = WorkflowStatus.PENDING.value
        self.db.commit()
        
        logger.info("workflow_planned", workflow_id=workflow_id, steps=len(step_plans))
        return plan_result
    
    def _create_serial_flow(self, workflow: WorkflowInstance) -> List[Dict]:
        """创建串行任务流程"""
        steps = [
            {"step_id": "plan", "type": "PLAN", "name": "需求规划", "estimated_hours": 2},
        ]
        
        # 复杂任务：前后端分开（串行）
        if workflow.total_budget > 2000 or self._is_complex_task(workflow):
            steps.extend([
                {"step_id": "backend", "type": "EXECUTE", "name": "后端开发", "estimated_hours": 10},
                {"step_id": "frontend", "type": "EXECUTE", "name": "前端开发", "estimated_hours": 8},
            ])
        else:
            steps.append({"step_id": "execute", "type": "EXECUTE", "name": "开发实现", "estimated_hours": 8})
        
        steps.extend([
            {"step_id": "review", "type": "REVIEW", "name": "代码评审", "estimated_hours": 2,
             "review_criteria": ["quality", "performance", "security"]},
            {"step_id": "test", "type": "TEST", "name": "测试验证", "estimated_hours": 3},
            {"step_id": "deliver", "type": "DELIVER", "name": "交付用户", "estimated_hours": 1},
        ])
        
        if workflow.total_budget > 1000:
            steps.insert(1, {"step_id": "approve", "type": "APPROVE", "name": "预算审批", "estimated_hours": 1})
        
        return steps
    
    def _is_complex_task(self, workflow: WorkflowInstance) -> bool:
        """判断是否为复杂任务"""
        desc_lower = workflow.description.lower()
        return any(k in desc_lower for k in ["前端", "后端", "frontend", "backend"])
    
    def _allocate_step_budgets(
        self, 
        steps_config: List[Dict], 
        base_budget: float,
        total_rework_budget: float
    ) -> Dict[str, Dict]:
        """分配预算到各步骤"""
        step_plans = {}
        total_hours = sum(s.get("estimated_hours", 4) for s in steps_config)
        
        for i, step_config in enumerate(steps_config):
            step_id = step_config["step_id"]
            hours = step_config.get("estimated_hours", 4)
            weight = hours / total_hours if total_hours > 0 else 1 / len(steps_config)
            
            step_base_budget = base_budget * weight
            step_rework_reserve = total_rework_budget * weight * 2
            
            step_plans[step_id] = {
                "step_id": step_id,
                "step_type": step_config["type"],
                "name": step_config["name"],
                "sequence": i,
                "base_budget": round(step_base_budget, 2),
                "rework_reserve": round(step_rework_reserve, 2),
                "estimated_hours": hours,
                "review_criteria": step_config.get("review_criteria"),
                "rework_limit": 3,
            }
        
        return step_plans
    
    def _match_agent_for_step(self, step_plan: Dict, workflow: WorkflowInstance) -> Optional[Agent]:
        """为步骤匹配员工"""
        step_type = step_plan["step_type"]
        candidates = self.db.query(Agent).filter(Agent.is_active == "true").all()
        
        if step_type == StepType.PLAN.value:
            for agent in candidates:
                if any(s.id in ["architecture", "system_design"] for s in agent.skills):
                    return agent
            return max(candidates, key=lambda a: a.level, default=None)
        
        if step_type == StepType.APPROVE.value:
            from src.models.agent import PositionLevel
            return self.db.query(Agent).filter(
                Agent.position_level == PositionLevel.PARTNER.value
            ).first()
        
        if step_type == StepType.EXECUTE.value:
            # 根据步骤名称匹配
            name_lower = step_plan["name"].lower()
            keywords = []
            if "前端" in name_lower or "frontend" in name_lower:
                keywords = ["frontend", "react", "vue", "css"]
            elif "后端" in name_lower or "backend" in name_lower:
                keywords = ["backend", "api", "database", "python"]
            else:
                keywords = ["programming"]
            
            best_match = None
            best_score = 0
            for agent in candidates:
                score = 0
                for skill in agent.skills:
                    if any(kw in skill.id.lower() for kw in keywords):
                        score += 15
                if not agent.current_task_id:
                    score += 5
                score += agent.level
                if score > best_score:
                    best_score = score
                    best_match = agent
            return best_match
        
        if step_type == StepType.REVIEW.value:
            candidates = [a for a in candidates if a.level >= 3]
            return candidates[0] if candidates else None
        
        if step_type == StepType.DELIVER.value:
            from src.models.agent import PositionLevel
            return self.db.query(Agent).filter(
                Agent.position_level == PositionLevel.PARTNER.value
            ).first()
        
        return candidates[0] if candidates else None
    
    def _generate_step_handbook(self, plan: Dict, workflow: WorkflowInstance, assignee: Agent) -> str:
        """生成步骤手册"""
        parts = [
            f"# {plan['name']} 执行手册",
            "",
            f"**任务**: {workflow.title}",
            f"**类型**: {plan['step_type']}",
            f"**负责人**: {assignee.name if assignee else '待定'}",
            f"**基础预算**: {plan['base_budget']} OC币",
            f"**返工储备**: {plan['rework_reserve']} OC币",
            f"**预计工时**: {plan['estimated_hours']} 小时",
            "",
            "## 预算使用规则",
            "- 首次执行：从基础预算扣除",
            "- 返工时：从返工储备扣除",
            "- 返工储备耗尽将触发熔断",
        ]
        return "\n".join(parts)
    
    def _generate_full_handbook(self, workflow: WorkflowInstance, step_plans: Dict) -> str:
        """生成完整手册"""
        parts = [
            f"# {workflow.title} - 任务手册",
            "",
            f"**总预算**: {workflow.total_budget} OC币",
            f"**基础预算**: {workflow.base_budget} OC币",
            f"**返工预算池**: {workflow.rework_budget} OC币",
            "",
            "## 执行流程（串行）",
        ]
        for step_id, plan in sorted(step_plans.items(), key=lambda x: x[1]["sequence"]):
            parts.append(f"\n{plan['sequence'] + 1}. {plan['name']}")
            parts.append(f"   负责人: {plan.get('agent_name', '待定')}")
            parts.append(f"   预算: {plan['base_budget']} (返工储备: {plan['rework_reserve']})")
        return "\n".join(parts)
    
    def _analyze_requirements(self, workflow: WorkflowInstance) -> str:
        """分析需求"""
        return f"任务分析：{'复杂任务' if self._is_complex_task(workflow) else '标准任务'}，预算{workflow.total_budget} OC币"
