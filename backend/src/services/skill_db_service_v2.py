"""
Skill Database Service (v2.0)

使用简化版模型
"""

import json
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from models.agent_v2 import Agent, AgentStatus
from models.task_v2 import Task, TaskStatus
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SkillDBService:
    """
    Skill 数据库服务 (v2.0)
    
    为 opc-bridge skill 提供数据库操作
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============ 任务相关 ============
    
    def get_current_task(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取 Agent 的当前任务
        
        查找分配给该 agent 的 assigned/in_progress 状态的任务
        """
        try:
            task = self.db.query(Task).filter(
                Task.assigned_to == agent_id,
                Task.status.in_([TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value])
            ).order_by(Task.assigned_at.desc()).first()
            
            if not task:
                return None
            
            return task.to_dict()
            
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
            
            # 2. 计算成本 (100 tokens = 1 OC币)
            cost = tokens_used / 100
            
            # 3. 更新任务
            task.status = TaskStatus.COMPLETED.value
            task.result = result
            task.actual_cost = cost
            task.completed_at = datetime.utcnow()
            
            # 4. 更新 Agent 预算和统计
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.used_budget += cost
                agent.completed_tasks += 1
                agent.status = AgentStatus.IDLE.value
                agent.current_task_id = None
            
            # 5. 提交
            self.db.commit()
            
            logger.info(f"Task {task_id} completed by {agent_id}, cost: {cost}")
            
            return {
                "success": True,
                "cost": cost,
                "remaining_budget": agent.remaining_budget if agent else 0
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
            
            return {
                "monthly_budget": agent.monthly_budget,
                "used_budget": agent.used_budget,
                "remaining_budget": agent.remaining_budget,
                "mood": agent.mood_emoji
            }
            
        except Exception as e:
            logger.error(f"Failed to get budget: {e}")
            return {"error": str(e)}
    
    # ============ 数据库操作 ============
    
    def read_data(self,
                  agent_id: str,
                  table: str,
                  query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        读取数据（带权限检查）
        
        Agent 只能读取自己的数据
        """
        try:
            if table == "tasks":
                # 只能读取自己的任务
                tasks = self.db.query(Task).filter(
                    Task.assigned_to == agent_id
                ).all()
                return [t.to_dict() for t in tasks]
            
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
        """
        try:
            logger.warning(f"Table {table} write not implemented")
            return {"success": False, "error": "Not implemented"}
            
        except Exception as e:
            logger.error(f"Failed to write data: {e}")
            return {"success": False, "error": str(e)}


from datetime import datetime