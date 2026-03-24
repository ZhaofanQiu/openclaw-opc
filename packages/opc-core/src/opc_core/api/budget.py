"""
opc-core: 预算管理 API

Budget Router

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#Budget
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository

from ..api.dependencies import get_employee_repo, verify_api_key

router = APIRouter(prefix="/budget", tags=["Budget"])


# ============ 数据模型 ============

class BudgetAddRequest(BaseModel):
    """增加预算请求"""
    amount: float = Field(..., gt=0, description="增加金额")
    reason: str = Field(default="", description="原因")


class BudgetConsumption(BaseModel):
    """预算消耗记录"""
    employee_id: str = Field(..., description="员工ID")
    task_id: str = Field(..., description="任务ID")
    tokens_input: int = Field(..., ge=0, description="输入Token数")
    tokens_output: int = Field(..., ge=0, description="输出Token数")


# ============ API 路由 ============

@router.get("/company", response_model=dict)
async def get_company_budget(
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """获取公司整体预算"""
    stats = await repo.get_budget_stats()
    
    return {
        "total_budget": stats["total_budget"],
        "total_used": stats["total_used"],
        "total_remaining": stats["total_remaining"],
        "employee_count": stats["employee_count"],
        "avg_budget": stats["avg_budget"],
        "avg_remaining": stats["avg_remaining"]
    }


@router.get("/employees", response_model=dict)
async def list_employee_budgets(
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """获取所有员工预算"""
    employees = await repo.get_all(limit=1000)
    
    result = []
    for emp in employees:
        result.append({
            "id": emp.id,
            "name": emp.name,
            "emoji": emp.emoji,
            "monthly_budget": emp.monthly_budget,
            "used_budget": emp.used_budget,
            "remaining": emp.remaining_budget,
            "percentage": emp.budget_percentage,
            "mood": emp.mood_emoji,
            "completed_tasks": emp.completed_tasks
        })
    
    return {"employees": result, "total": len(result)}


@router.get("/employees/{employee_id}", response_model=dict)
async def get_employee_budget(
    employee_id: str,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """获取单个员工预算"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {
        "id": employee.id,
        "name": employee.name,
        "monthly_budget": employee.monthly_budget,
        "used_budget": employee.used_budget,
        "remaining": employee.remaining_budget,
        "percentage": employee.budget_percentage,
        "mood": employee.mood_emoji
    }


@router.post("/employees/{employee_id}/add", response_model=dict)
async def add_budget(
    employee_id: str,
    data: BudgetAddRequest,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """增加员工预算"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await repo.update_budget(employee_id, data.amount, operation="add")
    
    return {
        "message": "Budget added",
        "added": data.amount,
        "new_monthly_budget": employee.monthly_budget + data.amount
    }


@router.post("/record-consumption", response_model=dict)
async def record_consumption(
    data: BudgetConsumption,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key)
):
    """
    记录预算消耗
    
    由 Agent 调用报告任务消耗
    """
    employee = await repo.get_by_id(data.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 计算成本（假设 1 token = 0.01 OC币）
    total_tokens = data.tokens_input + data.tokens_output
    cost = total_tokens * 0.01
    
    # 更新预算
    await repo.update_budget(data.employee_id, cost, operation="use")
    
    return {
        "success": True,
        "cost": cost,
        "tokens_input": data.tokens_input,
        "tokens_output": data.tokens_output,
        "remaining_budget": employee.remaining_budget - cost
    }
