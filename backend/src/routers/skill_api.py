"""
Skill API Router

提供 opc-bridge skill 调用的 API
Agent 通过这些接口与 OPC 交互
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from src.database import get_db
from src.services.skill_db_service import SkillDBService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/skill", tags=["Skill API"])

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

@router.get("/manuals/{manual_type}/{manual_id}")
def read_manual(
    manual_type: str,  # task, position, company
    manual_id: str,
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    读取手册内容
    
    Skill 方法: opc_read_manual(manual_type, manual_id)
    """
    try:
        # TODO: 从文件系统读取手册
        # manuals_dir = "data/manuals"
        # file_path = f"{manuals_dir}/{manual_type}_{manual_id}.md"
        
        logger.info(f"Reading manual: {manual_type}/{manual_id}")
        
        # 临时返回示例
        return {
            "content": f"这是 {manual_type} 手册的内容",
            "constraints": [
                "约束条件 1: 请遵循规范",
                "约束条件 2: 注意预算"
            ],
            "references": [
                "参考文档 1",
                "参考文档 2"
            ]
        }
    except Exception as e:
        logger.error(f"Failed to read manual: {e}")
        raise HTTPException(status_code=404, detail="Manual not found")

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
