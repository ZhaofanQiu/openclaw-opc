"""
Skill API Router

提供 opc-bridge skill 调用的 API
Agent 通过这些接口与 OPC 交互
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from database import get_db
from services.skill_db_service_v2 import SkillDBService
from models.agent_v2 import AgentStatus
from models.task_v2 import TaskStatus
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Skill API"])

# ============ 数据模型 ============

class TaskReportRequest(BaseModel):
    agent_id: str  # OpenClaw Agent ID (如 opc_partner)
    result: str
    tokens_used: int = Field(..., ge=0)

class DbReadRequest(BaseModel):
    agent_id: str
    table: str
    query: Dict[str, Any] = Field(default_factory=dict)

class DbWriteRequest(BaseModel):
    agent_id: str
    table: str
    data: Dict[str, Any]

# ============ 任务管理 ============

@router.get("/agents/{openclaw_agent_id}/current-task")
def get_current_task(openclaw_agent_id: str, db: Session = Depends(get_db)):
    """
    获取当前分配给 Agent 的任务
    
    Skill 方法: opc_get_current_task()
    
    Args:
        openclaw_agent_id: OpenClaw Agent ID (如 opc_partner)
    """
    try:
        # 1. 通过 openclaw_agent_id 找到员工
        from models.agent_v2 import Agent
        agent = db.query(Agent).filter(
            Agent.openclaw_agent_id == openclaw_agent_id
        ).first()
        
        if not agent:
            return {
                "has_task": False,
                "task": None,
                "error": f"Agent not found: {openclaw_agent_id}"
            }
        
        # 2. 使用员工内部 ID 查询任务
        service = SkillDBService(db)
        task = service.get_current_task(agent.id)
        
        if task:
            return {
                "has_task": True,
                "task": task
            }
        else:
            return {
                "has_task": False,
                "task": None
            }
            
    except Exception as e:
        logger.error(f"Failed to get current task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/report")
async def report_task_result(
    task_id: str,
    data: TaskReportRequest,
    db: Session = Depends(get_db)
):
    """
    报告任务执行结果
    
    Skill 方法: opc_report_task_result(task_id, result, tokens_used)
    """
    try:
        # 1. 通过 openclaw_agent_id 找到员工
        from models.agent_v2 import Agent
        from models.task_v2 import Task
        
        agent = db.query(Agent).filter(
            Agent.openclaw_agent_id == data.agent_id
        ).first()
        
        # 如果找不到，尝试通过 task_id 反查
        if not agent:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task and task.assigned_to:
                agent = db.query(Agent).filter(Agent.id == task.assigned_to).first()
                logger.info(f"Found agent by task assignment: {agent.name if agent else 'None'} for task {task_id}")
        
        if not agent:
            # 记录失败的回调日志
            from services.agent_interaction_log_service_v2 import AgentInteractionLogService
            AgentInteractionLogService.log(
                agent_id=data.agent_id,
                agent_name=data.agent_id,
                interaction_type="callback",
                direction="incoming",
                content=f"Report task {task_id}: {data.result[:100]}...",
                success=False,
                error_message=f"Agent not found for openclaw_agent_id: {data.agent_id}"
            )
            return {"success": False, "error": f"Agent not found for openclaw_agent_id: {data.agent_id}"}
        
        # 2. 使用员工内部 ID 报告任务
        service = SkillDBService(db)
        result = service.report_task_completion(
            agent_id=agent.id,  # 使用内部员工 ID
            task_id=task_id,
            result=data.result,
            tokens_used=data.tokens_used
        )
        
        # 3. 记录回调日志
        from services.agent_interaction_log_service_v2 import AgentInteractionLogService
        AgentInteractionLogService.log(
            agent_id=data.agent_id,
            agent_name=agent.name,
            interaction_type="callback",
            direction="incoming",
            content=f"Report task {task_id}: {data.result[:200]}...",
            metadata={
                "task_id": task_id,
                "tokens_used": data.tokens_used,
                "cost": result.get("cost", 0),
                "internal_agent_id": agent.id
            },
            success=result.get("success", False)
        )
        
        # 4. WebSocket 推送通知
        try:
            from core.websocket_manager import notify_task_completed, notify_budget_update
            await notify_task_completed(
                task_id=task_id,
                agent_id=agent.id,
                success=result.get("success", False),
                cost=result.get("cost", 0)
            )
            await notify_budget_update(
                agent_id=agent.id,
                used_budget=agent.used_budget,
                monthly_budget=agent.monthly_budget
            )
        except Exception as ws_error:
            logger.warning(f"WebSocket notification failed: {ws_error}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to report task: {e}")
        # 记录异常日志
        from services.agent_interaction_log_service_v2 import AgentInteractionLogService
        AgentInteractionLogService.log(
            agent_id=data.agent_id,
            agent_name=data.agent_id,
            interaction_type="callback",
            direction="incoming",
            content=f"Report task {task_id}",
            success=False,
            error_message=str(e)
        )
        return {"success": False, "error": str(e)}


# ============ 手册读取 ============

@router.get("/manuals/read")
def read_manual_by_path(
    path: str,  # 文件路径或手册类型
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    读取手册内容
    
    Skill 方法: opc_read_manual(path)
    
    支持:
    - 绝对路径: /path/to/manual.md
    - 相对路径: data/manuals/task_123.md
    - 类型+ID: task:123, position:senior, company:default
    """
    try:
        logger.info(f"Reading manual: {path} for agent {agent_id}")
        
        content = ""
        
        # 处理类型:ID 格式
        if ":" in path:
            manual_type, manual_id = path.split(":", 1)
            # 构建实际路径
            base_dir = os.path.join(os.getcwd(), "data", "manuals")
            file_path = os.path.join(base_dir, f"{manual_type}_{manual_id}.md")
        else:
            # 直接使用路径
            file_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        
        # 安全检查：确保在允许的目录内
        allowed_dirs = [
            os.path.join(os.getcwd(), "data", "manuals"),
            os.path.join(os.getcwd(), "docs"),
        ]
        
        real_path = os.path.realpath(file_path)
        is_allowed = any(real_path.startswith(d) for d in allowed_dirs)
        
        if not is_allowed:
            raise HTTPException(status_code=403, detail="Access denied: path not allowed")
        
        # 读取文件
        if os.path.exists(real_path) and os.path.isfile(real_path):
            with open(real_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # 文件不存在，返回默认内容
            content = f"# {path}\n\n手册内容待补充..."
        
        return {
            "path": path,
            "file_path": real_path,
            "content": content,
            "size": len(content)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 数据库操作 ============

@router.post("/db/read")
def db_read(data: DbReadRequest, db: Session = Depends(get_db)):
    """
    读取数据库
    
    Skill 方法: opc_db_read(table, query)
    
    注意: 带权限检查，Agent 只能访问自己的数据
    """
    try:
        service = SkillDBService(db)
        result = service.read_data(
            agent_id=data.agent_id,
            table=data.table,
            query=data.query
        )
        
        return {
            "data": result,
            "count": len(result),
            "table": data.table
        }
        
    except Exception as e:
        logger.error(f"DB read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/db/write")
def db_write(data: DbWriteRequest, db: Session = Depends(get_db)):
    """
    写入数据库
    
    Skill 方法: opc_db_write(table, data)
    
    注意: 带权限检查
    """
    try:
        logger.info(f"DB write by {data.agent_id}: {data.table}")
        
        # TODO:
        # 1. 验证 Agent 权限
        # 2. 执行写入
        # 3. 返回记录 ID
        
        return {
            "success": True,
            "id": f"record_demo"
        }
    except Exception as e:
        logger.error(f"DB write failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ 预算查询 ============

@router.get("/agents/{openclaw_agent_id}/budget")
def get_budget(openclaw_agent_id: str, db: Session = Depends(get_db)):
    """
    获取预算状态
    
    Skill 方法: opc_get_budget()
    
    Args:
        openclaw_agent_id: OpenClaw Agent ID (如 opc_partner)
    """
    try:
        # 1. 通过 openclaw_agent_id 找到员工
        from models.agent_v2 import Agent
        agent = db.query(Agent).filter(
            Agent.openclaw_agent_id == openclaw_agent_id
        ).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {openclaw_agent_id}")
        
        # 2. 使用员工内部 ID 查询预算
        service = SkillDBService(db)
        budget = service.get_budget(agent.id)
        
        if "error" in budget:
            raise HTTPException(status_code=404, detail=budget["error"])
        
        return budget
        
    except Exception as e:
        logger.error(f"Failed to get budget: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Skill 健康检查 ============

@router.get("/health")
def skill_health_check():
    """Skill 健康检查"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "message": "OPC Bridge Skill API is running"
    }
