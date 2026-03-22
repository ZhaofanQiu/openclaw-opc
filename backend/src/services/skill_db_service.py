"""
Skill Database Service

处理 opc-bridge skill 的数据库操作
带权限控制，Agent 只能访问自己的数据
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from models import Task, TaskStatus, Agent, Budget
from utils.logging_config import get_logger

logger = get_logger(__name__)

class SkillDBService:
    """
    Skill 数据库服务
    
    为 opc-bridge skill 提供数据库操作
    所有操作都带权限检查
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============ 任务相关 ============
    
    def get_current_task(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 的当前任务
        
        查找分配给该 agent 的 pending/assigned 状态的任务
        """
        try:
            task = self.db.query(Task).filter(
                Task.assigned_to == agent_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.ASSIGNED])
            ).order_by(Task.created_at.desc()).first()
            
            if not task:
                return None
            
            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "estimated_cost": task.estimated_cost,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get current task: {e}")
            return None
    
    def report_task_completion(self,
                               agent_id: str,
                               task_id: str,
                               result: str,
                               tokens_used: int) -> Dict[str, Any]:
        """
        报告任务完成
        
        更新任务状态、计算成本、更新预算
        """
        try:
            # 1. 查找任务
            task = self.db.query(Task).filter(
                Task.id == task_id,
                Task.assigned_to == agent_id
            ).first()
            
            if not task:
                return {"success": False, "error": "Task not found or not assigned to this agent"}
            
            # 2. 计算成本 (假设 100 tokens = 1 OC币)
            cost = tokens_used / 100
            
            # 3. 更新任务
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.tokens_used = tokens_used
            task.actual_cost = cost
            
            # 4. 更新预算
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.used_budget += cost
            
            # 5. 提交
            self.db.commit()
            
            logger.info(f"Task {task_id} completed by {agent_id}, cost: {cost}")
            
            return {
                "success": True,
                "cost": cost,
                "remaining_budget": agent.monthly_budget - agent.used_budget if agent else 0
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to report task: {e}")
            return {"success": False, "error": str(e)}
    
    # ============ 预算相关 ============
    
    def get_budget(self, agent_id: str) -> Dict[str, Any]:
        """获取 Agent 预算"""
        try:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                return {"error": "Agent not found"}
            
            remaining = agent.monthly_budget - agent.used_budget
            percentage = (remaining / agent.monthly_budget * 100) if agent.monthly_budget > 0 else 0
            
            # 心情 emoji
            if percentage > 60:
                mood = "😊"
            elif percentage > 30:
                mood = "😐"
            elif percentage > 10:
                mood = "😔"
            else:
                mood = "🚨"
            
            return {
                "monthly_budget": agent.monthly_budget,
                "used_budget": agent.used_budget,
                "remaining_budget": remaining,
                "mood": mood
            }
            
        except Exception as e:
            logger.error(f"Failed to get budget: {e}")
            return {"error": str(e)}
    
    # ============ 数据库操作 (带权限) ============
    
    def read_data(self,
                  agent_id: str,
                  table: str,
                  query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        读取数据（带权限检查）
        
        Agent 只能读取与自己和自己的任务相关的数据
        """
        try:
            # TODO: 实现通用的权限检查
            # 根据 table 类型检查权限
            
            if table == "tasks":
                # 只能读取自己的任务
                tasks = self.db.query(Task).filter(
                    Task.assigned_to == agent_id
                ).all()
                return [self._task_to_dict(t) for t in tasks]
            
            # 其他表...
            logger.warning(f"Table {table} read not implemented")
            return []
            
        except Exception as e:
            logger.error(f"Failed to read data: {e}")
            return []
    
    def write_data(self,
                   agent_id: str,
                   table: str,
                   data: Dict[str, Any]) -> Dict[str, Any]:
        """
        写入数据（带权限检查）
        
        Agent 只能写入与自己和自己的任务相关的数据
        """
        try:
            # TODO: 实现通用的权限检查
            logger.warning(f"Table {table} write not implemented")
            return {"success": False, "error": "Not implemented"}
            
        except Exception as e:
            logger.error(f"Failed to write data: {e}")
            return {"success": False, "error": str(e)}
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Task 转字典"""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value if task.status else None,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
