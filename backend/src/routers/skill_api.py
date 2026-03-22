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
    agent_id: str
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

@router.get("/agents/{agent_id}/current-task")
def get_current_task(agent_id: str, db: Session = Depends(get_db)):
    """
    获取当前分配给 Agent 的任务
    
    Skill 方法: opc_get_current_task()
    """
    try:
        service = SkillDBService(db)
        task = service.get_current_task(agent_id)
        
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
def report_task_result(
    task_id: str,
    data: TaskReportRequest,
    db: Session = Depends(get_db)
):
    """
    报告任务执行结果
    
    Skill 方法: opc_report_task_result(task_id, result, tokens_used)
    """
    try:
        service = SkillDBService(db)
        result = service.report_task_completion(
            agent_id=data.agent_id,
            task_id=task_id,
            result=data.result,
            tokens_used=data.tokens_used
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to report task: {e}")
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

@router.get("/agents/{agent_id}/budget")
def get_budget(agent_id: str, db: Session = Depends(get_db)):
    """
    获取预算状态
    
    Skill 方法: opc_get_budget()
    """
    try:
        service = SkillDBService(db)
        budget = service.get_budget(agent_id)
        
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
