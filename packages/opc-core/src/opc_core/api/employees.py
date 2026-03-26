"""
opc-core: 员工管理 API

Employee Router

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#Employee
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from opc_database.repositories import EmployeeRepository
from opc_database.models import AgentStatus
from opc_openclaw import AgentManager

from ..api.dependencies import get_employee_repo, verify_api_key

router = APIRouter(prefix="/employees", tags=["Employees"])


# ============ 数据模型 ============


class EmployeeCreate(BaseModel):
    """创建员工请求"""

    name: str = Field(..., min_length=1, max_length=50, description="员工姓名")
    emoji: str = Field(default="🤖", description="表情符号")
    position_level: int = Field(default=1, ge=1, le=5, description="职位等级 1-5")
    monthly_budget: float = Field(default=1000.0, ge=0, description="月度预算")
    openclaw_agent_id: Optional[str] = Field(
        default=None, description="绑定的 OpenClaw Agent ID"
    )


class EmployeeUpdate(BaseModel):
    """更新员工请求"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    emoji: Optional[str] = None
    monthly_budget: Optional[float] = Field(default=None, ge=0)


class EmployeeBindRequest(BaseModel):
    """绑定请求"""

    openclaw_agent_id: str = Field(..., description="OpenClaw Agent ID")


class EmployeeResponse(BaseModel):
    """员工响应"""

    id: str
    name: str
    emoji: str
    position_level: int
    status: str
    monthly_budget: float
    used_budget: float
    openclaw_agent_id: Optional[str]
    is_bound: str
    completed_tasks: int

    class Config:
        from_attributes = True


# ============ API 路由 ============


@router.get("", response_model=dict)
async def list_employees(
    status: Optional[str] = None,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取员工列表"""
    if status:
        employees = await repo.get_by_status(AgentStatus(status))
    else:
        employees = await repo.get_all(limit=1000)

    return {"employees": [e.to_dict() for e in employees], "total": len(employees)}


@router.post("", response_model=dict, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """创建新员工"""
    from opc_database.models import Employee

    # 检查 OpenClaw Agent 是否已被绑定
    if data.openclaw_agent_id:
        existing = await repo.get_by_openclaw_id(data.openclaw_agent_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"OpenClaw Agent '{data.openclaw_agent_id}' 已被员工 '{existing.name}' 绑定",
            )

    employee = Employee(
        id=f"emp_{uuid.uuid4().hex[:8]}",
        name=data.name,
        emoji=data.emoji,
        position_level=data.position_level,
        monthly_budget=data.monthly_budget,
        openclaw_agent_id=data.openclaw_agent_id,
        is_bound="true" if data.openclaw_agent_id else "false",
    )

    await repo.create(employee)

    return {"id": employee.id, "name": employee.name, "message": "Employee created"}


@router.get("/{employee_id}", response_model=dict)
async def get_employee(
    employee_id: str,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取员工详情"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return employee.to_dict()


@router.put("/{employee_id}", response_model=dict)
async def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """更新员工信息"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if data.name:
        employee.name = data.name
    if data.emoji:
        employee.emoji = data.emoji
    if data.monthly_budget is not None:
        employee.monthly_budget = data.monthly_budget

    await repo.update(employee)

    return {"message": "Employee updated", "employee": employee.to_dict()}


@router.delete("/{employee_id}", response_model=dict)
async def delete_employee(
    employee_id: str,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """删除员工"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    await repo.delete(employee)

    return {"message": "Employee deleted"}


# ============ 绑定管理 ============


@router.post("/{employee_id}/bind", response_model=dict)
async def bind_agent(
    employee_id: str,
    data: EmployeeBindRequest,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """绑定 OpenClaw Agent"""
    import logging
    logger = logging.getLogger(__name__)
    
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # 检查 Agent 是否已被其他员工绑定
    existing = await repo.get_by_openclaw_id(data.openclaw_agent_id)
    if existing and existing.id != employee_id:
        raise HTTPException(
            status_code=400,
            detail=f"Agent '{data.openclaw_agent_id}' 已被员工 '{existing.name}' 绑定"
        )

    # 验证 Agent 可用性（带错误处理）
    try:
        async with AgentManager() as manager:
            is_available = await manager.is_available(data.openclaw_agent_id)
            if not is_available:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Agent '{data.openclaw_agent_id}' 不可用，请检查 OpenClaw 配置或 Agent 状态"
                )
    except FileNotFoundError:
        logger.error("OpenClaw CLI not found")
        raise HTTPException(
            status_code=503,
            detail="OpenClaw CLI 未找到，请确保 OpenClaw 已正确安装"
        )
    except Exception as e:
        logger.error(f"Agent availability check failed: {e}")
        # 在测试环境中，如果 CLI 不可用，允许强制绑定
        import os
        if os.getenv("OPC_ALLOW_FORCE_BIND") == "true":
            logger.warning(f"Force binding agent {data.openclaw_agent_id} due to CLI error")
        else:
            raise HTTPException(
                status_code=503,
                detail=f"无法验证 Agent 状态: {str(e)}"
            )

    await repo.bind_openclaw_agent(employee_id, data.openclaw_agent_id)

    return {
        "message": "Agent bound successfully",
        "employee_id": employee_id,
        "openclaw_agent_id": data.openclaw_agent_id,
    }


@router.post("/{employee_id}/unbind", response_model=dict)
async def unbind_agent(
    employee_id: str,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """解绑 OpenClaw Agent"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.openclaw_agent_id = None
    employee.is_bound = "false"
    await repo.update(employee)

    return {"message": "Agent unbound"}


@router.get("/{employee_id}/budget", response_model=dict)
async def get_budget(
    employee_id: str,
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取员工预算信息"""
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "monthly_budget": employee.monthly_budget,
        "used_budget": employee.used_budget,
        "remaining": employee.remaining_budget,
        "percentage": employee.budget_percentage,
        "mood": employee.mood_emoji,
    }


# ============ OpenClaw Agent 列表 ============


@router.get("/openclaw/available", response_model=dict)
async def list_available_agents(
    repo: EmployeeRepository = Depends(get_employee_repo),
    api_key: str = Depends(verify_api_key),
):
    """获取可用的 OpenClaw Agent（未绑定的，且只返回 opc_ 开头的）"""
    import os
    import json

    config_path = os.path.expanduser("~/.openclaw/openclaw.json")

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        agents = config.get("agents", {}).get("list", [])

        # 获取已绑定的 Agent IDs
        all_employees = await repo.get_all(limit=1000)
        bound_ids = {e.openclaw_agent_id for e in all_employees if e.openclaw_agent_id}

        # 过滤：只保留 opc_ 开头且未被绑定的
        # 命名规范：以 "opc_" 开头，排除 main/default
        def is_valid_opc_agent(agent_id: str) -> bool:
            if not agent_id:
                return False
            if agent_id in ("main", "default"):
                return False
            if not agent_id.startswith("opc_"):
                return False
            return True

        available = [
            {"id": a.get("id"), "name": a.get("name", a.get("id"))}
            for a in agents
            if a.get("id") not in bound_ids and is_valid_opc_agent(a.get("id", ""))
        ]

        return {"agents": available, "total": len(available)}

    except Exception as e:
        return {"agents": [], "total": 0, "error": str(e)}
