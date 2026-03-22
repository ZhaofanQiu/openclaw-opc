"""
Workflow Engine Service for v0.5.0

统一工作流引擎核心服务
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.models import Agent, Skill, WorkflowTemplate, WorkflowInstance, WorkflowStep
from src.models.workflow_engine import (
    StepType, WorkflowStatus, StepStatus, 
    WorkflowHistory, WorkflowReworkRecord
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowEngineService:
    """统一工作流引擎服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 工作流模板管理 ==========
    
    def create_template(
        self,
        name: str,
        description: str,
        steps_config: List[Dict],
        budget_allocation: List[float],
        created_by: str,
        category: str = "general",
        default_rework_limit: int = 3,
    ) -> WorkflowTemplate:
        """创建工作流模板"""
        template = WorkflowTemplate(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            category=category,
            steps_config=steps_config,
            budget_allocation=budget_allocation,
            default_rework_limit=default_rework_limit,
            created_by=created_by,
        )
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """获取模板"""
        return self.db.query(WorkflowTemplate).filter(
            WorkflowTemplate.id == template_id
        ).first()
    
    # ========== 工作流实例管理 ==========
    
    def create_workflow(
        self,
        title: str,
        description: str,
        total_budget: float,
        created_by: str,
        template_id: str = None,
    ) -> WorkflowInstance:
        """
        创建工作流实例
        
        用户只需提供：主题、描述、总预算
        Partner会进行自动规划
        """
        workflow = WorkflowInstance(
            id=str(uuid.uuid4())[:8],
            template_id=template_id,
            title=title,
            description=description,
            status=WorkflowStatus.PLANNING.value,  # 初始状态：规划中
            total_budget=total_budget,
            remaining_budget=total_budget,
            created_by=created_by,
            current_step_index=-1,
        )
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        
        logger.info("workflow_created", workflow_id=workflow.id, title=title)
        return workflow
    
    def auto_plan_workflow(self, workflow_id: str) -> Dict:
        """
        Partner自动规划工作流
        
        根据任务内容，Partner决定：
        1. 需要哪些步骤
        2. 每个步骤由谁负责
        3. 每个步骤的预算
        4. 生成任务手册
        """
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        # 获取Partner
        partner = self.db.query(Agent).filter(Agent.id == workflow.created_by).first()
        if not partner:
            raise ValueError("Partner not found")
        
        # 分析任务，选择合适的模板或自定义流程
        steps_config = self._analyze_and_select_steps(workflow)
        
        # 为每个步骤分配员工
        step_plans = {}
        budget_allocation = self._allocate_budget(
            workflow.total_budget, 
            len(steps_config)
        )
        
        for i, step_config in enumerate(steps_config):
            step_id = step_config["step_id"]
            
            # 根据步骤类型匹配合适的员工
            assignee = self._match_agent_for_step(step_config, workflow)
            
            # 生成步骤手册
            handbook = self._generate_step_handbook(
                step_config, workflow, assignee
            )
            
            step_plans[step_id] = {
                "step_type": step_config["type"],
                "name": step_config["name"],
                "sequence": i,
                "agent_id": assignee.id if assignee else None,
                "agent_name": assignee.name if assignee else None,
                "budget": budget_allocation[i],
                "estimated_hours": step_config.get("estimated_hours", 4),
                "handbook": handbook,
                "rework_limit": step_config.get("rework_limit", 3),
            }
        
        # 生成完整任务手册
        full_handbook = self._generate_full_handbook(workflow, step_plans)
        
        plan_result = {
            "analysis": self._analyze_requirements(workflow),
            "selected_steps": [s["step_id"] for s in steps_config],
            "step_plans": step_plans,
            "handbook": full_handbook,
            "total_estimated_hours": sum(p["estimated_hours"] for p in step_plans.values()),
            "planned_at": datetime.utcnow().isoformat(),
        }
        
        workflow.plan_result = plan_result
        workflow.status = WorkflowStatus.PENDING.value  # 规划完成，待启动
        self.db.commit()
        
        logger.info("workflow_planned", workflow_id=workflow_id, steps=len(steps_config))
        return plan_result
    
    def _analyze_and_select_steps(self, workflow: WorkflowInstance) -> List[Dict]:
        """分析任务并选择合适的步骤序列"""
        # 默认标准开发流程
        default_steps = [
            {"step_id": "plan", "type": "PLAN", "name": "需求规划", "estimated_hours": 2},
            {"step_id": "execute", "type": "EXECUTE", "name": "开发实现", "estimated_hours": 8},
            {"step_id": "review", "type": "REVIEW", "name": "代码评审", "estimated_hours": 2, 
             "review_criteria": ["quality", "performance", "security", "maintainability"]},
            {"step_id": "test", "type": "TEST", "name": "测试验证", "estimated_hours": 3},
            {"step_id": "deliver", "type": "DELIVER", "name": "交付用户", "estimated_hours": 1},
        ]
        
        # 根据任务内容调整
        title_lower = workflow.title.lower()
        desc_lower = workflow.description.lower()
        
        # 如果是纯研究/调研任务
        if any(k in title_lower for k in ["调研", "研究", "research", "分析"]):
            return [
                {"step_id": "plan", "type": "PLAN", "name": "研究规划", "estimated_hours": 1},
                {"step_id": "execute", "type": "EXECUTE", "name": "执行研究", "estimated_hours": 6},
                {"step_id": "review", "type": "REVIEW", "name": "成果评审", "estimated_hours": 1},
                {"step_id": "deliver", "type": "DELIVER", "name": "交付报告", "estimated_hours": 1},
            ]
        
        # 如果是文档/写作任务
        if any(k in title_lower for k in ["文档", "写作", "doc", "写作", "content"]):
            return [
                {"step_id": "plan", "type": "PLAN", "name": "内容规划", "estimated_hours": 1},
                {"step_id": "execute", "type": "EXECUTE", "name": "内容创作", "estimated_hours": 5},
                {"step_id": "review", "type": "REVIEW", "name": "内容审核", "estimated_hours": 1},
                {"step_id": "deliver", "type": "DELIVER", "name": "发布交付", "estimated_hours": 0.5},
            ]
        
        # 大预算任务增加审批步骤
        if workflow.total_budget > 1000:
            default_steps.insert(1, {
                "step_id": "approve", "type": "APPROVE", "name": "预算审批", "estimated_hours": 1
            })
        
        return default_steps
    
    def _match_agent_for_step(
        self, 
        step_config: Dict, 
        workflow: WorkflowInstance
    ) -> Optional[Agent]:
        """
        为步骤匹配合适的员工
        
        匹配逻辑：
        1. 步骤类型 → 所需技能
        2. 预算限制 → 员工等级
        3. 工作负载 → 空闲员工优先
        """
        step_type = step_config["type"]
        
        # 规划步骤：找架构师或高级开发者
        if step_type == StepType.PLAN.value:
            candidates = self.db.query(Agent).filter(
                Agent.is_active == "true"
            ).all()
            # 找有架构经验的
            for agent in candidates:
                if any(s.id in ["architecture", "system_design"] for s in agent.skills):
                    return agent
            # 否则找等级最高的
            return max(candidates, key=lambda a: a.level, default=None)
        
        # 审批步骤：必须是Partner
        if step_type == StepType.APPROVE.value:
            from src.models.agent import PositionLevel
            return self.db.query(Agent).filter(
                Agent.position_level == PositionLevel.PARTNER.value
            ).first()
        
        # 执行步骤：找对应技能的开发者
        if step_type == StepType.EXECUTE.value:
            # 从任务描述中提取所需技能
            required_skills = self._extract_required_skills(workflow.description)
            
            candidates = self.db.query(Agent).filter(
                Agent.is_active == "true"
            ).all()
            
            best_match = None
            best_score = 0
            
            for agent in candidates:
                score = 0
                # 技能匹配
                for skill in agent.skills:
                    if skill.id in required_skills:
                        score += 10
                # 空闲度
                if not agent.current_task_id:
                    score += 5
                # 等级
                score += agent.level
                
                if score > best_score:
                    best_score = score
                    best_match = agent
            
            return best_match
        
        # 评审步骤：找资深开发者（非原开发者）
        if step_type == StepType.REVIEW.value:
            candidates = self.db.query(Agent).filter(
                Agent.is_active == "true",
                Agent.level >= 3  # 需要一定等级
            ).all()
            return candidates[0] if candidates else None
        
        # 测试步骤：找测试人员
        if step_type == StepType.TEST.value:
            candidates = self.db.query(Agent).filter(
                Agent.is_active == "true"
            ).all()
            for agent in candidates:
                if any(s.id == "testing" for s in agent.skills):
                    return agent
            return candidates[0] if candidates else None
        
        # 交付步骤：Partner负责
        if step_type == StepType.DELIVER.value:
            from src.models.agent import PositionLevel
            return self.db.query(Agent).filter(
                Agent.position_level == PositionLevel.PARTNER.value
            ).first()
        
        return None
    
    def _extract_required_skills(self, description: str) -> List[str]:
        """从描述中提取所需技能"""
        skills = []
        desc_lower = description.lower()
        
        skill_keywords = {
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "js", "react", "vue", "angular", "node"],
            "database": ["database", "sql", "postgres", "mysql", "mongodb"],
            "devops": ["docker", "kubernetes", "k8s", "ci/cd", "deploy"],
            "frontend": ["frontend", "css", "html", "ui", "web"],
            "backend": ["backend", "api", "server"],
            "ai": ["ai", "ml", "machine learning", "model", "gpt"],
            "writing": ["doc", "document", "write", "content"],
        }
        
        for skill_id, keywords in skill_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                skills.append(skill_id)
        
        return skills
    
    def _allocate_budget(self, total_budget: float, step_count: int) -> List[float]:
        """分配预算到各步骤"""
        # 默认比例：规划10%，执行50%，其他平分40%
        if step_count == 4:
            ratios = [0.1, 0.5, 0.25, 0.15]  # plan, execute, review, deliver
        elif step_count == 5:
            ratios = [0.1, 0.45, 0.2, 0.15, 0.1]  # plan, execute, review, test, deliver
        else:
            # 平均分配
            ratios = [1.0 / step_count] * step_count
        
        return [total_budget * r for r in ratios]
    
    def _generate_step_handbook(
        self, 
        step_config: Dict, 
        workflow: WorkflowInstance,
        assignee: Agent,
    ) -> str:
        """生成步骤执行手册"""
        step_type = step_config["type"]
        
        handbook_parts = [
            f"# {step_config['name']} 执行手册",
            "",
            f"**任务**: {workflow.title}",
            f"**步骤类型**: {step_type}",
            f"**负责人**: {assignee.name if assignee else '待定'}",
            f"**预计工时**: {step_config.get('estimated_hours', 4)} 小时",
            "",
            "## 任务背景",
            workflow.description,
            "",
        ]
        
        if step_type == StepType.PLAN.value:
            handbook_parts.extend([
                "## 规划要求",
                "1. 分析需求，明确目标",
                "2. 制定实施方案",
                "3. 识别风险和依赖",
                "4. 输出：规划文档",
                "",
            ])
        elif step_type == StepType.EXECUTE.value:
            handbook_parts.extend([
                "## 执行要求",
                "1. 按照规划执行",
                "2. 遵循代码规范",
                "3. 编写必要文档",
                "4. 自测通过后提交",
                "",
            ])
        elif step_type == StepType.REVIEW.value:
            criteria = step_config.get("review_criteria", ["quality", "performance"])
            handbook_parts.extend([
                "## 评审要求",
                "1. 检查代码质量",
                "2. 评估性能和安全性",
                "3. 给出改进建议",
                "4. 评分维度: " + ", ".join(criteria),
                "",
            ])
        
        handbook_parts.extend([
            "## 完成标准",
            "- [ ] 按照要求完成工作",
            "- [ ] 通过自检",
            "- [ ] 输出物完整",
            "",
            "## 注意事项",
            "如有问题及时反馈，不要阻塞流程。",
        ])
        
        return "\n".join(handbook_parts)
    
    def _generate_full_handbook(
        self, 
        workflow: WorkflowInstance, 
        step_plans: Dict
    ) -> str:
        """生成完整任务手册"""
        parts = [
            f"# {workflow.title} - 任务手册",
            "",
            "## 任务概述",
            workflow.description,
            "",
            f"**总预算**: {workflow.total_budget} OC币",
            f"**总工时**: {sum(p['estimated_hours'] for p in step_plans.values())} 小时",
            "",
            "## 执行流程",
            "",
        ]
        
        for step_id, plan in sorted(step_plans.items(), key=lambda x: x[1]["sequence"]):
            parts.extend([
                f"### {plan['sequence'] + 1}. {plan['name']}",
                f"- **负责人**: {plan['agent_name'] or '待定'}",
                f"- **预算**: {plan['budget']} OC币",
                f"- **工时**: {plan['estimated_hours']} 小时",
                "",
            ])
        
        parts.extend([
            "## 各步骤详细手册",
            "",
        ])
        
        for step_id, plan in step_plans.items():
            parts.append(plan["handbook"])
            parts.append("---")
            parts.append("")
        
        return "\n".join(parts)
    
    def _analyze_requirements(self, workflow: WorkflowInstance) -> str:
        """分析需求"""
        return f"""需求分析：
- 任务类型：{self._detect_task_type(workflow)}
- 复杂度：根据预算{workflow.total_budget} OC币判断为{'高' if workflow.total_budget > 1000 else '中' if workflow.total_budget > 500 else '低'}复杂度
- 预估工时：见各步骤规划
"""
    
    def _detect_task_type(self, workflow: WorkflowInstance) -> str:
        """检测任务类型"""
        title = workflow.title.lower()
        if any(k in title for k in ["开发", "dev", "code", "实现"]):
            return "开发任务"
        elif any(k in title for k in ["调研", "研究", "research"]):
            return "研究任务"
        elif any(k in title for k in ["文档", "doc", "写作"]):
            return "文档任务"
        elif any(k in title for k in ["设计", "design", "ui"]):
            return "设计任务"
        return "综合任务"
