"""
Agent Skill Path v0.5.5

员工技能成长路径可视化
- 当前位置
- 晋升轨迹
- 成长建议
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Agent, WorkflowStep, WorkflowInstance
from models.agent import PositionLevel
from models.workflow_engine import StepType
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentSkillPathService:
    """员工技能成长路径服务"""
    
    # 职级定义
    LEVELS = [
        {"level": 1, "name": "实习生", "title": "Intern", "min_exp": 0},
        {"level": 2, "name": "初级", "title": "Junior", "min_exp": 100},
        {"level": 3, "name": "中级", "title": "Mid-level", "min_exp": 300},
        {"level": 4, "name": "高级", "title": "Senior", "min_exp": 600},
        {"level": 5, "name": "专家", "title": "Expert", "min_exp": 1000},
        {"level": 6, "name": "架构师", "title": "Architect", "min_exp": 1500},
        {"level": 7, "name": "Partner", "title": "Partner", "min_exp": 2000},
    ]
    
    # 技能路径定义
    SKILL_PATHS = {
        "fullstack": {
            "name": "全栈工程师",
            "stages": [
                {"stage": 1, "name": "前端入门", "skills": ["html", "css", "javascript"], "steps": ["EXECUTE"]},
                {"stage": 2, "name": "后端基础", "skills": ["python", "database"], "steps": ["EXECUTE"]},
                {"stage": 3, "name": "全栈能力", "skills": ["react", "api", "deployment"], "steps": ["EXECUTE", "REVIEW"]},
                {"stage": 4, "name": "架构设计", "skills": ["system_design", "microservices"], "steps": ["PLAN", "EXECUTE"]},
                {"stage": 5, "name": "技术Leader", "skills": ["team_leadership", "architecture"], "steps": ["PLAN", "REVIEW", "APPROVE"]},
            ]
        },
        "backend": {
            "name": "后端工程师",
            "stages": [
                {"stage": 1, "name": "API开发", "skills": ["python", "api"], "steps": ["EXECUTE"]},
                {"stage": 2, "name": "数据库专家", "skills": ["database", "sql", "optimization"], "steps": ["EXECUTE"]},
                {"stage": 3, "name": "系统架构", "skills": ["system_design", "distributed_systems"], "steps": ["PLAN", "EXECUTE"]},
                {"stage": 4, "name": "技术专家", "skills": ["microservices", "devops"], "steps": ["PLAN", "REVIEW"]},
            ]
        },
        "frontend": {
            "name": "前端工程师",
            "stages": [
                {"stage": 1, "name": "页面开发", "skills": ["html", "css", "javascript"], "steps": ["EXECUTE"]},
                {"stage": 2, "name": "框架应用", "skills": ["react", "vue", "state_management"], "steps": ["EXECUTE"]},
                {"stage": 3, "name": "前端架构", "skills": ["frontend_architecture", "performance"], "steps": ["PLAN", "EXECUTE"]},
                {"stage": 4, "name": "前端专家", "skills": ["ui_ux", "frontend_leadership"], "steps": ["PLAN", "REVIEW"]},
            ]
        },
        "reviewer": {
            "name": "技术评审",
            "stages": [
                {"stage": 1, "name": "代码审查", "skills": ["code_review", "best_practices"], "steps": ["REVIEW"]},
                {"stage": 2, "name": "质量把控", "skills": ["quality_assurance", "testing"], "steps": ["REVIEW", "TEST"]},
                {"stage": 3, "name": "评审专家", "skills": ["technical_leadership", "mentoring"], "steps": ["REVIEW", "APPROVE"]},
            ]
        },
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_agent_skill_path(self, agent_id: str) -> Dict:
        """获取员工技能成长路径"""
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        # 分析员工历史
        history = self._analyze_agent_history(agent_id)
        
        # 确定最适合的成长路径
        best_path = self._determine_best_path(agent, history)
        
        # 生成路径可视化
        path_visualization = self._generate_path_visualization(agent, best_path, history)
        
        return {
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "current_level": agent.level,
                "position": agent.position_level,
            },
            "current_skills": [s.id for s in agent.skills],
            "recommended_path": best_path,
            "path_visualization": path_visualization,
            "next_milestone": self._get_next_milestone(agent, best_path),
            "growth_suggestions": self._generate_suggestions(agent, history, best_path),
        }
    
    def _analyze_agent_history(self, agent_id: str) -> Dict:
        """分析员工历史表现"""
        # 查询该员工完成的所有步骤
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.status == "completed"
        ).all()
        
        # 统计各类型步骤完成情况
        step_type_stats = {}
        for step in steps:
            t = step.step_type
            if t not in step_type_stats:
                step_type_stats[t] = {"count": 0, "rework": 0, "avg_score": 0}
            step_type_stats[t]["count"] += 1
            step_type_stats[t]["rework"] += step.rework_count
            
            if step.review_scores:
                scores = step.review_scores.values()
                step_type_stats[t]["avg_score"] = sum(scores) / len(scores)
        
        # 计算平均分
        for t in step_type_stats:
            if step_type_stats[t]["count"] > 0:
                step_type_stats[t]["avg_rework"] = step_type_stats[t]["rework"] / step_type_stats[t]["count"]
        
        return {
            "total_completed_steps": len(steps),
            "step_type_stats": step_type_stats,
        }
    
    def _determine_best_path(self, agent: Agent, history: Dict) -> Dict:
        """确定最适合的成长路径"""
        agent_skills = {s.id for s in agent.skills}
        step_stats = history.get("step_type_stats", {})
        
        best_path = None
        best_score = 0
        
        for path_id, path_def in self.SKILL_PATHS.items():
            score = 0
            
            # 技能匹配
            for stage in path_def["stages"]:
                matched_skills = set(stage["skills"]) & agent_skills
                score += len(matched_skills) * 10
            
            # 步骤经验匹配
            for stage in path_def["stages"]:
                for step_type in stage["steps"]:
                    if step_type in step_stats:
                        score += step_stats[step_type]["count"] * 5
            
            if score > best_score:
                best_score = score
                best_path = {"id": path_id, **path_def}
        
        return best_path or {"id": "fullstack", **self.SKILL_PATHS["fullstack"]}
    
    def _generate_path_visualization(self, agent: Agent, path: Dict, history: Dict) -> List[Dict]:
        """生成路径可视化"""
        agent_skills = {s.id for s in agent.skills}
        step_stats = history.get("step_type_stats", {})
        
        visualization = []
        current_stage = 0
        
        for stage in path["stages"]:
            # 检查是否已完成
            skill_match = len(set(stage["skills"]) & agent_skills) / len(stage["skills"])
            step_experience = sum(step_stats.get(s, {}).get("count", 0) for s in stage["steps"])
            
            if skill_match >= 0.8 and step_experience >= 3:
                status = "completed"
                current_stage = stage["stage"]
            elif skill_match >= 0.5 or step_experience >= 1:
                status = "in_progress"
                if current_stage < stage["stage"]:
                    current_stage = stage["stage"] - 0.5
            else:
                status = "locked"
            
            visualization.append({
                "stage": stage["stage"],
                "name": stage["name"],
                "status": status,
                "skills": [
                    {"name": s, "acquired": s in agent_skills}
                    for s in stage["skills"]
                ],
                "required_steps": stage["steps"],
                "progress": {
                    "skill_match": round(skill_match * 100, 1),
                    "step_experience": step_experience,
                },
            })
        
        return visualization
    
    def _get_next_milestone(self, agent: Agent, path: Dict) -> Optional[Dict]:
        """获取下一个里程碑"""
        agent_skills = {s.id for s in agent.skills}
        
        for stage in path["stages"]:
            skill_match = len(set(stage["skills"]) & agent_skills) / len(stage["skills"])
            if skill_match < 0.8:
                missing_skills = set(stage["skills"]) - agent_skills
                return {
                    "stage": stage["stage"],
                    "name": stage["name"],
                    "missing_skills": list(missing_skills),
                    "required_steps": stage["steps"],
                }
        
        return None
    
    def _generate_suggestions(self, agent: Agent, history: Dict, path: Dict) -> List[str]:
        """生成成长建议"""
        suggestions = []
        step_stats = history.get("step_type_stats", {})
        
        # 建议1：多做某类步骤以提升
        next_milestone = self._get_next_milestone(agent, path)
        if next_milestone:
            steps = ", ".join(next_milestone["required_steps"])
            suggestions.append(f"建议多参与{steps}类型任务，积累{next_milestone['name']}经验")
        
        # 建议2：返工率高的改进
        for step_type, stats in step_stats.items():
            if stats.get("avg_rework", 0) > 1:
                suggestions.append(f"{step_type}步骤返工率较高，建议加强质量把控")
        
        # 建议3：技能拓展
        all_path_skills = set()
        for stage in path["stages"]:
            all_path_skills.update(stage["skills"])
        
        agent_skills = {s.id for s in agent.skills}
        missing_skills = all_path_skills - agent_skills
        if missing_skills:
            suggestions.append(f"建议学习：{', '.join(list(missing_skills)[:3])}")
        
        return suggestions
    
    def get_all_paths(self) -> List[Dict]:
        """获取所有成长路径"""
        return [
            {"id": k, "name": v["name"], "stages_count": len(v["stages"])}
            for k, v in self.SKILL_PATHS.items()
        ]
    
    def compare_agents(self, agent_ids: List[str]) -> Dict:
        """对比多个员工的成长路径"""
        comparison = []
        
        for agent_id in agent_ids:
            try:
                path_data = self.get_agent_skill_path(agent_id)
                comparison.append({
                    "agent_id": agent_id,
                    "agent_name": path_data["agent"]["name"],
                    "current_level": path_data["agent"]["current_level"],
                    "recommended_path": path_data["recommended_path"]["name"],
                    "current_stage": sum(1 for s in path_data["path_visualization"] if s["status"] == "completed"),
                    "next_milestone": path_data["next_milestone"]["name"] if path_data["next_milestone"] else "已完成",
                })
            except ValueError:
                continue
        
        return {
            "comparison": comparison,
            "total_agents": len(comparison),
        }
