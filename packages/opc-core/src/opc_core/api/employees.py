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
    position_level: int = Field(default=1, ge=1, le=5, description="职位等级 1-5")
    job_type: str = Field(default="general", description="工种/岗位类型")
    monthly_budget: float = Field(default=1000.0, ge=0, description="月度预算")
    openclaw_agent_id: Optional[str] = Field(
        default=None, description="绑定的 OpenClaw Agent ID"
    )


class EmployeeUpdate(BaseModel):
    """更新员工请求"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    job_type: Optional[str] = None
    monthly_budget: Optional[float] = Field(default=None, ge=0)


class EmployeeBindRequest(BaseModel):
    """绑定请求"""

    openclaw_agent_id: str = Field(..., description="OpenClaw Agent ID")


class EmployeeResponse(BaseModel):
    """员工响应"""

    id: str
    name: str
    position_level: int
    job_type: str
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
        position_level=data.position_level,
        job_type=data.job_type,
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
    if data.job_type:
        employee.job_type = data.job_type
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
    """删除员工
    
    删除员工时，会将其未完成的任务恢复为未分配状态
    """
    from opc_database.models import TaskStatus
    
    employee = await repo.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # 获取当前 session
    session = repo.session
    
    # 处理未完成的任务 - 将它们恢复为未分配状态
    from opc_database.repositories import TaskRepository
    task_repo = TaskRepository(session)
    
    # 获取员工的所有任务
    all_tasks = await task_repo.get_by_employee(employee_id=employee_id, limit=1000)
    
    unassigned_count = 0
    for task in all_tasks:
        # 只处理未完成的任务（非已完成/已取消状态）
        if task.status not in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
            task.status = TaskStatus.PENDING.value
            task.assigned_to = None
            await task_repo.update(task)
            unassigned_count += 1
    
    # 删除员工
    await repo.delete(employee)

    return {
        "message": "Employee deleted",
        "unassigned_tasks": unassigned_count
    }


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

        # 过滤：只保留 opc_ 或 opc- 开头且未被绑定的
        # 命名规范：以 "opc_" 或 "opc-" 开头，排除 main/default
        def is_valid_opc_agent(agent_id: str) -> bool:
            if not agent_id:
                return False
            if agent_id in ("main", "default"):
                return False
            # 接受 opc_ 或 opc- 开头
            if not (agent_id.startswith("opc_") or agent_id.startswith("opc-")):
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


@router.post("/openclaw/create-agent", response_model=dict)
async def create_openclaw_agent(
    data: dict,
    api_key: str = Depends(verify_api_key),
):
    """
    创建新的 OpenClaw Agent
    
    这会：
    1. 修改 openclaw.json 添加新 Agent 配置
    2. 重启 OpenClaw Gateway
    3. 等待重启完成
    
    请求体:
    {
        "agent_id": "opc_worker_1",  # 必须以 opc_ 或 opc- 开头
        "name": "Worker 1",           # 可选，默认使用 agent_id
        "confirm_restart": true       # 必须设置为 true 表示确认重启
    }
    """
    import os
    import json
    import subprocess
    import asyncio
    
    agent_id = data.get("agent_id", "").strip()
    name = data.get("name", "").strip() or agent_id
    confirm_restart = data.get("confirm_restart", False)
    
    # 验证参数
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id 不能为空")
    
    if not (agent_id.startswith("opc_") or agent_id.startswith("opc-")):
        raise HTTPException(status_code=400, detail="agent_id 必须以 opc_ 或 opc- 开头")
    
    if agent_id in ("main", "default"):
        raise HTTPException(status_code=400, detail="agent_id 不能为 main 或 default")
    
    if not confirm_restart:
        raise HTTPException(status_code=400, detail="必须设置 confirm_restart: true 确认重启 OpenClaw Gateway")
    
    # 读取当前配置
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    if not os.path.exists(config_path):
        raise HTTPException(status_code=500, detail="找不到 OpenClaw 配置文件")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {str(e)}")
    
    # 检查是否已存在
    agents_list = config.get("agents", {}).get("list", [])
    for agent in agents_list:
        if agent.get("id") == agent_id:
            raise HTTPException(status_code=400, detail=f"Agent '{agent_id}' 已存在")
    
    # 创建新的 Agent 配置
    new_agent = {
        "id": agent_id,
        "default": False,
        "name": name,
        "workspace": f"/root/.openclaw/agents/{agent_id}/agent/workspace",
        "agentDir": f"/root/.openclaw/agents/{agent_id}/agent"
    }
    
    # 添加 Agent 目录
    agent_dir = os.path.expanduser(f"~/.openclaw/agents/{agent_id}/agent")
    workspace_dir = os.path.join(agent_dir, "workspace")
    memory_dir = os.path.join(agent_dir, "memory")
    
    try:
        os.makedirs(workspace_dir, exist_ok=True)
        os.makedirs(memory_dir, exist_ok=True)
        
        # 创建默认的 IDENTITY.md
        identity_content = f"""# IDENTITY.md - Who Am I?

- **Name:** {name}
- **Creature:** OpenClaw Agent for OPC
- **Vibe:** Professional assistant

## Role

You are an AI employee in the OpenClaw OPC (One-Person Company) system.
Your task is to help complete assigned work efficiently and professionally.

## Capabilities

- Execute tasks assigned through the OPC system
- Report progress and results
- Communicate with the manager when needed
"""
        identity_path = os.path.join(agent_dir, "IDENTITY.md")
        with open(identity_path, 'w', encoding='utf-8') as f:
            f.write(identity_content)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建 Agent 目录失败: {str(e)}")
    
    # 更新配置
    agents_list.append(new_agent)
    config["agents"]["list"] = agents_list
    
    # 保存配置
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置文件失败: {str(e)}")
    
    # 重启 OpenClaw Gateway
    restart_result = {"success": False, "message": ""}
    try:
        # 使用 openclaw gateway restart 命令
        proc = subprocess.run(
            ["openclaw", "gateway", "restart"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if proc.returncode == 0:
            restart_result = {"success": True, "message": "Gateway restart initiated"}
        else:
            restart_result = {
                "success": False, 
                "message": f"Restart failed: {proc.stderr or proc.stdout}"
            }
    except subprocess.TimeoutExpired:
        restart_result = {"success": True, "message": "Gateway restart command sent (timeout, may still be restarting)"}
    except Exception as e:
        restart_result = {"success": False, "message": str(e)}
    
    # 等待至少 30 秒让 Gateway 重启
    await asyncio.sleep(30)
    
    return {
        "message": "Agent created and Gateway restarted",
        "agent": new_agent,
        "restart_status": restart_result,
        "note": "请等待 30 秒后刷新页面查看新 Agent"
    }
