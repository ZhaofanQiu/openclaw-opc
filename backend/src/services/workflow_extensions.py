"""
Workflow Engine Extensions v0.5.3

扩展功能：
1. 流程可视化 - 当前进度、历史轨迹
2. 智能推荐 - 基于历史匹配最优员工
3. 瓶颈分析 - 识别返工热点
4. 成就徽章 - 激励机制
5. 时间预测 - AI预测完成时间
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import WorkflowInstance, WorkflowStep, Agent
from models.workflow_engine import (
    StepType, WorkflowStatus, WorkflowHistory, WorkflowReworkRecord
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowVisualizationService:
    """流程可视化服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_workflow_progress(self, workflow_id: str) -> Dict:
        """获取工作流进度可视化数据"""
        workflow = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_id
        ).first()
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id
        ).order_by(WorkflowStep.sequence).all()
        
        total_steps = len(steps)
        completed_steps = sum(1 for s in steps if s.status == "completed")
        current_step_index = workflow.current_step_index
        
        # 构建进度条数据
        progress_data = []
        for i, step in enumerate(steps):
            progress_data.append({
                "sequence": i,
                "name": step.name,
                "type": step.step_type,
                "status": step.status,
                "is_current": i == current_step_index,
                "is_completed": step.status == "completed",
                "assignee": step.assignee.name if step.assignee else None,
                "rework_count": step.rework_count,
                "budget_used": step.used_budget + step.rework_cost,
            })
        
        # 计算整体进度
        if workflow.status == "completed":
            progress_percent = 100
        elif total_steps > 0:
            progress_percent = (completed_steps / total_steps) * 100
        else:
            progress_percent = 0
        
        return {
            "workflow_id": workflow_id,
            "title": workflow.title,
            "status": workflow.status,
            "progress_percent": round(progress_percent, 1),
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": current_step_index + 1 if current_step_index >= 0 else 0,
            "steps": progress_data,
            "budget_progress": {
                "total": workflow.total_budget,
                "used": workflow.used_base_budget + workflow.used_rework_budget,
                "remaining": workflow.remaining_budget,
                "usage_percent": round(
                    ((workflow.used_base_budget + workflow.used_rework_budget) / workflow.total_budget * 100), 1
                ) if workflow.total_budget > 0 else 0,
            },
            "time_estimate": self._estimate_remaining_time(workflow, steps),
        }
    
    def _estimate_remaining_time(self, workflow: WorkflowInstance, steps: List[WorkflowStep]) -> Dict:
        """估计剩余时间"""
        if workflow.status == "completed":
            return {"status": "completed", "remaining_hours": 0}
        
        remaining_hours = 0
        for step in steps:
            if step.sequence >= workflow.current_step_index:
                # 考虑返工可能
                estimated = step.estimated_hours * (1 + step.rework_count * 0.5)
                remaining_hours += estimated
        
        return {
            "status": "in_progress",
            "remaining_hours": round(remaining_hours, 1),
            "estimated_completion": (datetime.utcnow() + timedelta(hours=remaining_hours)).isoformat(),
        }
    
    def get_workflow_timeline(self, workflow_id: str) -> List[Dict]:
        """获取工作流时间线"""
        history = self.db.query(WorkflowHistory).filter(
            WorkflowHistory.workflow_id == workflow_id
        ).order_by(WorkflowHistory.created_at).all()
        
        timeline = []
        for h in history:
            timeline.append({
                "time": h.created_at.isoformat() if h.created_at else None,
                "action": h.action,
                "step": h.step_id,
                "actor": h.actor_id,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "comment": h.comment,
            })
        
        return timeline
    
    def get_bottleneck_analysis(self, workflow_id: str) -> Dict:
        """获取瓶颈分析"""
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id
        ).all()
        
        bottlenecks = []
        for step in steps:
            # 返工次数多的步骤是瓶颈
            if step.rework_count >= 2:
                bottlenecks.append({
                    "step_id": step.id,
                    "name": step.name,
                    "type": step.step_type,
                    "rework_count": step.rework_count,
                    "rework_cost": step.rework_cost,
                    "severity": "high" if step.rework_count >= 3 else "medium",
                    "suggestion": self._get_bottleneck_suggestion(step),
                })
        
        # 按返工次数排序
        bottlenecks.sort(key=lambda x: x["rework_count"], reverse=True)
        
        return {
            "workflow_id": workflow_id,
            "bottleneck_count": len(bottlenecks),
            "bottlenecks": bottlenecks,
            "overall_health": "good" if len(bottlenecks) == 0 else "warning" if len(bottlenecks) <= 2 else "critical",
        }
    
    def _get_bottleneck_suggestion(self, step: WorkflowStep) -> str:
        """获取瓶颈建议"""
        if step.step_type == StepType.EXECUTE.value:
            return "建议加强需求沟通，或增加技术评审环节"
        elif step.step_type == StepType.REVIEW.value:
            return "建议明确评审标准，提供更详细的检查清单"
        elif step.step_type == StepType.TEST.value:
            return "建议加强开发自测，或改进测试用例"
        return "建议分析返工原因，优化流程"


class WorkflowRecommendationService:
    """智能推荐服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def recommend_agents_for_step(
        self,
        step_type: str,
        workflow_title: str,
        workflow_description: str,
        exclude_agents: List[str] = None,
        top_k: int = 3,
    ) -> List[Dict]:
        """
        推荐执行步骤的最佳员工
        
        基于：
        1. 历史完成率
        2. 平均返工次数
        3. 技能匹配度
        4. 当前负载
        """
        exclude_agents = exclude_agents or []
        
        # 获取所有候选员工
        candidates = self.db.query(Agent).filter(
            Agent.is_active == "true",
            ~Agent.id.in_(exclude_agents)
        ).all()
        
        recommendations = []
        for agent in candidates:
            score, reasons = self._calculate_agent_score(
                agent, step_type, workflow_title, workflow_description
            )
            recommendations.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "score": round(score, 2),
                "reasons": reasons,
                "current_load": "busy" if agent.current_task_id else "free",
            })
        
        # 按分数排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:top_k]
    
    def _calculate_agent_score(
        self,
        agent: Agent,
        step_type: str,
        title: str,
        description: str,
    ) -> Tuple[float, List[str]]:
        """计算员工得分"""
        score = 50.0  # 基础分
        reasons = []
        
        # 1. 历史表现分析
        history_score = self._analyze_agent_history(agent.id, step_type)
        score += history_score * 20
        if history_score > 0.8:
            reasons.append("历史表现优秀")
        elif history_score > 0.5:
            reasons.append("历史表现良好")
        
        # 2. 技能匹配
        skill_match = self._match_skills(agent, title, description)
        score += skill_match * 15
        if skill_match > 0.7:
            reasons.append("技能高度匹配")
        
        # 3. 当前负载
        if not agent.current_task_id:
            score += 10
            reasons.append("当前空闲")
        
        # 4. 职级加成
        from models.agent import PositionLevel
        if agent.position_level == PositionLevel.SENIOR.value:
            score += 5
            reasons.append("资深员工")
        
        return min(score, 100), reasons
    
    def _analyze_agent_history(self, agent_id: str, step_type: str) -> float:
        """分析员工历史表现 (0-1)"""
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.step_type == step_type,
            WorkflowStep.status == "completed"
        ).all()
        
        if not steps:
            return 0.5  # 无历史记录，中等分数
        
        total = len(steps)
        no_rework = sum(1 for s in steps if s.rework_count == 0)
        
        return no_rework / total
    
    def _match_skills(self, agent: Agent, title: str, description: str) -> float:
        """匹配技能 (0-1)"""
        text = (title + " " + description).lower()
        
        skill_keywords = {
            "python": ["python", "django", "flask", "fastapi"],
            "javascript": ["javascript", "react", "vue", "angular", "node"],
            "frontend": ["frontend", "css", "html", "ui", "web"],
            "backend": ["backend", "api", "server", "database"],
            "ai": ["ai", "ml", "machine learning", "model"],
        }
        
        matched = 0
        total = 0
        for skill_id, keywords in skill_keywords.items():
            if any(kw in text for kw in keywords):
                total += 1
                if any(s.id == skill_id for s in agent.skills):
                    matched += 1
        
        return matched / total if total > 0 else 0.5
    
    def recommend_budget_allocation(
        self,
        total_budget: float,
        steps_config: List[Dict],
    ) -> List[float]:
        """
        智能推荐预算分配
        
        基于历史数据优化分配
        """
        total_hours = sum(s.get("estimated_hours", 4) for s in steps_config)
        
        allocations = []
        for step in steps_config:
            hours = step.get("estimated_hours", 4)
            base_ratio = hours / total_hours if total_hours > 0 else 1 / len(steps_config)
            
            # 根据步骤类型调整
            if step["type"] == StepType.EXECUTE.value:
                # 执行步骤容易返工，多分配一点
                base_ratio *= 1.1
            elif step["type"] == StepType.REVIEW.value:
                # 评审通常比较准
                base_ratio *= 0.9
            
            allocations.append(base_ratio)
        
        # 归一化
        total_ratio = sum(allocations)
        return [round(total_budget * r / total_ratio, 2) for r in allocations]


class WorkflowAchievementService:
    """成就徽章服务"""
    
    ACHIEVEMENTS = {
        "zero_rework": {
            "id": "zero_rework",
            "name": "零返工专家",
            "description": "连续完成3个任务且无任何返工",
            "icon": "🎯",
            "rarity": "rare",
        },
        "speed_demon": {
            "id": "speed_demon",
            "name": "极速完成",
            "description": "任务实际用时少于预估的50%",
            "icon": "⚡",
            "rarity": "common",
        },
        "budget_master": {
            "id": "budget_master",
            "name": "预算大师",
            "description": "任务完成时预算使用率低于80%",
            "icon": "💰",
            "rarity": "common",
        },
        "firefighter": {
            "id": "firefighter",
            "name": "救火队长",
            "description": "成功处理3个返工熔断的任务",
            "icon": "🚒",
            "rarity": "epic",
        },
        "perfect_delivery": {
            "id": "perfect_delivery",
            "name": "完美交付",
            "description": "任务按时、按预算、零返工完成",
            "icon": "🏆",
            "rarity": "legendary",
        },
        "review_expert": {
            "id": "review_expert",
            "name": "评审专家",
            "description": "累计评审10个步骤且平均评分>85",
            "icon": "👁️",
            "rarity": "rare",
        },
        "multitasker": {
            "id": "multitasker",
            "name": "多面手",
            "description": "参与过所有类型步骤的执行",
            "icon": "🎭",
            "rarity": "epic",
        },
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_achievements(self, agent_id: str) -> List[Dict]:
        """检查员工获得的成就"""
        earned = []
        
        for achievement_id, achievement in self.ACHIEVEMENTS.items():
            if self._check_achievement(agent_id, achievement_id):
                earned.append(achievement)
        
        return earned
    
    def _check_achievement(self, agent_id: str, achievement_id: str) -> bool:
        """检查单个成就"""
        if achievement_id == "zero_rework":
            return self._check_zero_rework(agent_id)
        elif achievement_id == "speed_demon":
            return self._check_speed_demon(agent_id)
        elif achievement_id == "budget_master":
            return self._check_budget_master(agent_id)
        elif achievement_id == "firefighter":
            return self._check_firefighter(agent_id)
        elif achievement_id == "perfect_delivery":
            return self._check_perfect_delivery(agent_id)
        elif achievement_id == "review_expert":
            return self._check_review_expert(agent_id)
        elif achievement_id == "multitasker":
            return self._check_multitasker(agent_id)
        return False
    
    def _check_zero_rework(self, agent_id: str) -> bool:
        """检查零返工专家"""
        recent_workflows = self.db.query(WorkflowInstance).join(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowInstance.status == "completed"
        ).order_by(WorkflowInstance.completed_at.desc()).limit(3).all()
        
        if len(recent_workflows) < 3:
            return False
        
        for wf in recent_workflows:
            for step in wf.steps:
                if step.assignee_id == agent_id and step.rework_count > 0:
                    return False
        return True
    
    def _check_speed_demon(self, agent_id: str) -> bool:
        """检查极速完成"""
        steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.status == "completed",
            WorkflowStep.actual_hours > 0
        ).all()
        
        return any(
            s.actual_hours < s.estimated_hours * 0.5 for s in steps
        )
    
    def _check_budget_master(self, agent_id: str) -> bool:
        """检查预算大师"""
        workflows = self.db.query(WorkflowInstance).join(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowInstance.status == "completed"
        ).all()
        
        for wf in workflows:
            usage = (wf.used_base_budget + wf.used_rework_budget) / wf.total_budget
            if usage < 0.8:
                return True
        return False
    
    def _check_firefighter(self, agent_id: str) -> bool:
        """检查救火队长"""
        # 简化为处理过返工任务
        rework_steps = self.db.query(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.rework_count > 0,
            WorkflowStep.status == "completed"
        ).count()
        
        return rework_steps >= 3
    
    def _check_perfect_delivery(self, agent_id: str) -> bool:
        """检查完美交付"""
        workflows = self.db.query(WorkflowInstance).join(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowInstance.status == "completed"
        ).all()
        
        for wf in workflows:
            if (wf.total_rework_count == 0 and 
                (wf.used_base_budget + wf.used_rework_budget) / wf.total_budget <= 1.0):
                return True
        return False
    
    def _check_review_expert(self, agent_id: str) -> bool:
        """检查评审专家"""
        reviews = self.db.query(WorkflowStep).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.step_type == StepType.REVIEW.value,
            WorkflowStep.status == "completed"
        ).all()
        
        if len(reviews) < 10:
            return False
        
        total_score = 0
        for r in reviews:
            scores = r.review_scores or {}
            if scores:
                total_score += sum(scores.values()) / len(scores)
        
        avg_score = total_score / len(reviews) if reviews else 0
        return avg_score > 85
    
    def _check_multitasker(self, agent_id: str) -> bool:
        """检查多面手"""
        step_types = self.db.query(WorkflowStep.step_type).filter(
            WorkflowStep.assignee_id == agent_id,
            WorkflowStep.status == "completed"
        ).distinct().all()
        
        return len(step_types) >= 5
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """获取成就排行榜"""
        agents = self.db.query(Agent).filter(Agent.is_active == "true").all()
        
        leaderboard = []
        for agent in agents:
            achievements = self.check_achievements(agent.id)
            leaderboard.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "achievement_count": len(achievements),
                "achievements": achievements,
                "rarity_score": self._calculate_rarity_score(achievements),
            })
        
        leaderboard.sort(key=lambda x: (x["achievement_count"], x["rarity_score"]), reverse=True)
        return leaderboard[:limit]
    
    def _calculate_rarity_score(self, achievements: List[Dict]) -> int:
        """计算稀有度分数"""
        rarity_scores = {
            "common": 1,
            "rare": 2,
            "epic": 3,
            "legendary": 5,
        }
        return sum(rarity_scores.get(a["rarity"], 1) for a in achievements)


class WorkflowAnalyticsService:
    """工作流分析服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_team_statistics(self, days: int = 30) -> Dict:
        """获取团队统计"""
        since = datetime.utcnow() - timedelta(days=days)
        
        workflows = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.created_at >= since
        ).all()
        
        total = len(workflows)
        completed = sum(1 for w in workflows if w.status == "completed")
        cancelled = sum(1 for w in workflows if w.status == "cancelled")
        fused = sum(1 for w in workflows if w.status in ["budget_fused", "rework_fused"])
        
        total_budget = sum(w.total_budget for w in workflows)
        used_budget = sum(w.used_base_budget + w.used_rework_budget for w in workflows)
        
        return {
            "period_days": days,
            "workflows": {
                "total": total,
                "completed": completed,
                "cancelled": cancelled,
                "fused": fused,
                "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
            },
            "budget": {
                "total_allocated": round(total_budget, 2),
                "total_used": round(used_budget, 2),
                "usage_rate": round(used_budget / total_budget * 100, 1) if total_budget > 0 else 0,
            },
            "rework": {
                "total_rework_count": sum(w.total_rework_count for w in workflows),
                "avg_rework_per_workflow": round(
                    sum(w.total_rework_count for w in workflows) / total, 2
                ) if total > 0 else 0,
            },
        }
    
    def get_step_type_statistics(self, days: int = 30) -> List[Dict]:
        """获取各步骤类型统计"""
        since = datetime.utcnow() - timedelta(days=days)
        
        steps = self.db.query(WorkflowStep).join(WorkflowInstance).filter(
            WorkflowInstance.created_at >= since
        ).all()
        
        stats = defaultdict(lambda: {
            "total": 0,
            "completed": 0,
            "reworked": 0,
            "total_rework_count": 0,
            "avg_budget_used": 0,
        })
        
        for step in steps:
            t = step.step_type
            stats[t]["total"] += 1
            if step.status == "completed":
                stats[t]["completed"] += 1
            if step.rework_count > 0:
                stats[t]["reworked"] += 1
                stats[t]["total_rework_count"] += step.rework_count
        
        result = []
        for step_type, data in stats.items():
            result.append({
                "step_type": step_type,
                "total": data["total"],
                "completion_rate": round(data["completed"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
                "rework_rate": round(data["reworked"] / data["total"] * 100, 1) if data["total"] > 0 else 0,
                "avg_rework_count": round(data["total_rework_count"] / data["total"], 2) if data["total"] > 0 else 0,
            })
        
        return sorted(result, key=lambda x: x["total"], reverse=True)
