"""
opc-core: 手册管理 API

Manual Router

作者: OpenClaw OPC Team
创建日期: 2026-03-24
版本: 0.4.0

API文档: API.md#Manual
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import verify_api_key

router = APIRouter(prefix="/manuals", tags=["Manuals"])

# 手册存储路径
MANUALS_DIR = Path("data/manuals")


# ============ 数据模型 ============


class ManualUpdateRequest(BaseModel):
    """更新手册请求"""

    content: str = Field(..., description="手册内容")


class ManualGenerateRequest(BaseModel):
    """生成手册请求"""

    task_id: str = Field(..., description="任务ID")
    title: str = Field(..., description="任务标题")
    description: str = Field(default="", description="任务描述")


# ============ 辅助函数 ============


def get_manual_path(manual_type: str, entity_id: Optional[str] = None) -> Path:
    """
    获取手册路径

    manual_type: company | employee | role | task
    """
    if manual_type == "company":
        return MANUALS_DIR / "company.md"
    elif manual_type == "employee":
        return MANUALS_DIR / "employees" / f"{entity_id}.md"
    elif manual_type == "role":
        return MANUALS_DIR / "roles" / f"{entity_id}.md"
    elif manual_type == "task":
        return MANUALS_DIR / "tasks" / f"{entity_id}.md"
    else:
        raise ValueError(f"Unknown manual type: {manual_type}")


def read_manual_file(path: Path) -> Optional[str]:
    """读取手册文件"""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def write_manual_file(path: Path, content: str):
    """写入手册文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ============ 公司手册 ============


@router.get("/company", response_model=dict)
async def get_company_manual(api_key: str = Depends(verify_api_key)):
    """获取公司手册"""
    path = get_manual_path("company")
    content = read_manual_file(path)

    if content is None:
        # 初始化默认手册
        content = """# 公司手册

## 公司使命

打造高效的一人公司运营系统。

## 核心价值观

- 效率第一
- 持续改进
- 数据驱动

## 员工规范

1. 及时响应任务
2. 准确报告进度
3. 高效使用预算
"""
        write_manual_file(path, content)

    return {"type": "company", "path": str(path), "content": content}


@router.put("/company", response_model=dict)
async def update_company_manual(
    data: ManualUpdateRequest, api_key: str = Depends(verify_api_key)
):
    """更新公司手册"""
    path = get_manual_path("company")
    write_manual_file(path, data.content)

    return {"message": "Company manual updated", "path": str(path)}


# ============ 员工手册 ============


@router.get("/employee/{employee_id}", response_model=dict)
async def get_employee_manual(employee_id: str, api_key: str = Depends(verify_api_key)):
    """获取员工手册"""
    path = get_manual_path("employee", employee_id)
    content = read_manual_file(path)

    if content is None:
        raise HTTPException(status_code=404, detail="Employee manual not found")

    return {
        "type": "employee",
        "employee_id": employee_id,
        "path": str(path),
        "content": content,
    }


@router.put("/employee/{employee_id}", response_model=dict)
async def update_employee_manual(
    employee_id: str, data: ManualUpdateRequest, api_key: str = Depends(verify_api_key)
):
    """更新员工手册"""
    path = get_manual_path("employee", employee_id)
    write_manual_file(path, data.content)

    return {"message": "Employee manual updated", "path": str(path)}


@router.post("/employee/{employee_id}/init", response_model=dict)
async def init_employee_manual(
    employee_id: str,
    name: str = "员工",
    position_level: int = 1,
    api_key: str = Depends(verify_api_key),
):
    """初始化员工手册"""
    path = get_manual_path("employee", employee_id)

    position_names = {1: "实习生", 2: "专员", 3: "资深", 4: "专家", 5: "合伙人"}
    position_name = position_names.get(position_level, "员工")

    content = f"""# {name} 的员工手册

## 基本信息

- **姓名**: {name}
- **职位**: {position_name} (Level {position_level})
- **ID**: {employee_id}

## 职责描述

作为{position_name}，你需要：

1. 按时完成分配的任务
2. 主动报告进度
3. 高效使用预算

## 技能要求

- 专业领域知识
- 问题解决能力
- 沟通协作能力

## 工作规范

- 收到任务后立即确认
- 遇到困难及时反馈
- 任务完成后报告结果
"""

    write_manual_file(path, content)

    return {"message": "Employee manual initialized", "path": str(path)}


# ============ 任务手册 ============


@router.get("/task/{task_id}", response_model=dict)
async def get_task_manual(task_id: str, api_key: str = Depends(verify_api_key)):
    """获取任务手册"""
    path = get_manual_path("task", task_id)
    content = read_manual_file(path)

    if content is None:
        raise HTTPException(status_code=404, detail="Task manual not found")

    return {"type": "task", "task_id": task_id, "path": str(path), "content": content}


@router.post("/task/generate", response_model=dict)
async def generate_task_manual(
    data: ManualGenerateRequest, api_key: str = Depends(verify_api_key)
):
    """生成任务手册"""
    path = get_manual_path("task", data.task_id)

    content = f"""# 任务手册: {data.title}

## 任务信息

- **任务ID**: {data.task_id}
- **标题**: {data.title}
- **描述**: {data.description}

## 执行步骤

1. 理解任务需求
2. 制定执行计划
3. 执行具体工作
4. 验证结果
5. 报告完成

## 注意事项

- 注意预算控制
- 及时报告进度
- 遇到困难立即反馈

## 交付标准

- 完成所有要求的功能
- 通过基本测试
- 提供清晰的总结
"""

    write_manual_file(path, content)

    return {
        "message": "Task manual generated",
        "path": str(path),
        "task_id": data.task_id,
    }


@router.post("/task/{task_id}/regenerate", response_model=dict)
async def regenerate_task_manual(
    task_id: str,
    title: str = "未命名任务",
    description: str = "",
    api_key: str = Depends(verify_api_key),
):
    """重新生成任务手册"""
    return await generate_task_manual(
        ManualGenerateRequest(task_id=task_id, title=title, description=description),
        api_key,
    )
