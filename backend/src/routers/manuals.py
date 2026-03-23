"""
Manuals Router (v2.0)

四种手册的统一管理：
1. 公司手册 (company)
2. 员工手册 (employee/{id})
3. 职责手册 (role/{id})
4. 任务手册 (task/{id})
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.company_manual_service import (
    get_company_manual,
    update_company_manual,
    initialize_company_manual
)
from services.employee_manual_service import (
    get_employee_manual,
    update_employee_manual,
    add_user_requirement_to_employee
)
from services.role_manual_service import get_role_manual, list_roles
from services.manual_service import get_task_manual
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Manuals"])


# ============ 数据模型 ============

class CompanyManualUpdate(BaseModel):
    content: str


class EmployeeManualUpdate(BaseModel):
    content: str


class UserRequirementAdd(BaseModel):
    requirement: str


# ============ 公司手册 ============

@router.get("/company")
def read_company_manual():
    """获取公司手册"""
    manual = get_company_manual()
    if not manual:
        raise HTTPException(status_code=404, detail="Company manual not found")
    return manual


@router.put("/company")
def update_company_manual_endpoint(data: CompanyManualUpdate):
    """更新公司手册（用户修改）"""
    try:
        result = update_company_manual(data.content)
        return result
    except Exception as e:
        logger.error(f"Failed to update company manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/company/init")
def init_company_manual():
    """初始化默认公司手册"""
    path = initialize_company_manual()
    return {"message": "Company manual initialized", "path": path}


# ============ 员工手册 ============

@router.get("/employee/{employee_id}")
def read_employee_manual(employee_id: str):
    """获取员工手册"""
    manual = get_employee_manual(employee_id)
    if not manual:
        raise HTTPException(status_code=404, detail="Employee manual not found")
    return manual


@router.put("/employee/{employee_id}")
def update_employee_manual_endpoint(employee_id: str, data: EmployeeManualUpdate):
    """更新员工手册（用户通过聊天修改）"""
    try:
        result = update_employee_manual(employee_id, data.content)
        return result
    except Exception as e:
        logger.error(f"Failed to update employee manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/employee/{employee_id}/requirement")
def add_employee_requirement(employee_id: str, data: UserRequirementAdd):
    """添加用户要求到员工手册"""
    success = add_user_requirement_to_employee(employee_id, data.requirement)
    if not success:
        raise HTTPException(status_code=404, detail="Employee manual not found")
    return {"message": "Requirement added", "employee_id": employee_id}


# ============ 职责手册 ============

@router.get("/roles")
def list_available_roles():
    """列出所有可用职责"""
    return {"roles": list_roles()}


@router.get("/role/{role_id}")
def read_role_manual(role_id: str):
    """获取职责手册"""
    manual = get_role_manual(role_id)
    if not manual:
        raise HTTPException(status_code=404, detail=f"Role manual not found: {role_id}")
    return manual


# ============ 任务手册 ============

@router.get("/task/{task_id}")
def read_task_manual(task_id: str):
    """获取任务手册"""
    manual = get_task_manual(task_id)
    if not manual:
        raise HTTPException(status_code=404, detail="Task manual not found")
    return manual


# ============ 批量获取 ============

@router.get("/employee/{employee_id}/all")
def get_all_manuals_for_employee(
    employee_id: str,
    role_id: Optional[str] = None,
    task_id: Optional[str] = None
):
    """
    获取员工执行工作前需要阅读的所有手册
    
    Args:
        role_id: 本次任务的职责类型（planner/executor/reviewer/tester）
        task_id: 当前任务ID（可选，获取任务手册）
    
    Returns:
        {
            "company": {...},
            "employee": {...},
            "role": {...},
            "task": {...}
        }
    """
    result = {}
    
    # 1. 公司手册
    company = get_company_manual()
    if company:
        result["company"] = {
            "type": "company",
            "relative_path": company["relative_path"],
            "content": company["content"]
        }
    
    # 2. 员工手册
    employee = get_employee_manual(employee_id)
    if employee:
        result["employee"] = {
            "type": "employee",
            "employee_id": employee_id,
            "relative_path": employee["relative_path"],
            "content": employee["content"]
        }
    
    # 3. 职责手册
    if role_id:
        role = get_role_manual(role_id)
        if role:
            result["role"] = {
                "type": "role",
                "role_id": role_id,
                "role_name": role["role_name"],
                "relative_path": role["relative_path"],
                "content": role["content"]
            }
    
    # 4. 任务手册
    if task_id:
        task = get_task_manual(task_id)
        if task:
            result["task"] = {
                "type": "task",
                "task_id": task_id,
                "relative_path": task["relative_path"],
                "content": task["content"]
            }
    
    return result