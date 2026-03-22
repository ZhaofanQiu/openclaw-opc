"""
任务分配 API 路由
支持通过聊天形式分配任务给员工
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.task_template_service import TaskTemplateService
from services.task_response_parser import TaskResultHandler
from services.async_message_service import AsyncMessageService
from routers.async_messages import process_message_async

router = APIRouter(prefix="/api/task-assignment", tags=["Task Assignment"])


# ============ 请求/响应模型 ============

class AssignTaskRequest(BaseModel):
    """分配任务请求"""
    agent_id: str = Field(..., description="员工Agent ID")
    task_type: str = Field(default="base", description="任务类型")
    description: str = Field(..., description="任务描述")
    priority: str = Field(default="normal", description="优先级")
    budget: float = Field(default=100.0, description="预算(OC币)")
    deadline_hours: int = Field(default=24, description="截止小时数")
    # 可选参数
    related_task_id: Optional[str] = Field(None, description="关联的系统任务ID")
    template_params: Optional[dict] = Field(default_factory=dict, description="模板特定参数")


class AssignTaskResponse(BaseModel):
    """分配任务响应"""
    success: bool
    message_id: str
    task_content: str
    status: str
    check_url: str


class QuickTaskRequest(BaseModel):
    """快速任务请求"""
    agent_id: str = Field(..., description="员工Agent ID")
    instruction: str = Field(..., description="任务指令")
    output_path: Optional[str] = Field(None, description="输出路径")
    budget: float = Field(default=100.0, description="预算")


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    success: bool
    task_id: str
    status: str
    result_summary: Optional[str]
    output_path: Optional[str]
    token_used: int
    is_valid_format: bool


class TaskTemplateListResponse(BaseModel):
    """任务模板列表响应"""
    templates: list


# ============ API 端点 ============

@router.post("/assign", response_model=AssignTaskResponse)
async def assign_task(
    request: AssignTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    分配标准化任务给员工
    
    使用预定义模板生成任务消息，通过异步消息发送给员工。
    
    **示例请求**:
    ```json
    {
        "agent_id": "agent_abc123",
        "task_type": "database_query",
        "description": "查询本月完成的任务数量",
        "priority": "normal",
        "budget": 50,
        "deadline_hours": 4,
        "template_params": {
            "db_type": "SQLite",
            "tables": "tasks",
            "query_requirements": "统计本月完成的任务数"
        }
    }
    ```
    """
    # 生成任务ID
    import uuid
    task_id = str(uuid.uuid4())[:8]
    
    # 生成任务消息
    template_service = TaskTemplateService()
    task_content = template_service.generate_task_message(
        task_type=request.task_type,
        task_id=task_id,
        description=request.description,
        priority=request.priority,
        budget=request.budget,
        deadline_hours=request.deadline_hours,
        **request.template_params
    )
    
    # 创建异步消息
    message_service = AsyncMessageService(db)
    message = message_service.create_message(
        sender_id="system",
        sender_type="system",
        sender_name="OPC系统",
        recipient_id=request.agent_id,
        content=task_content,
        message_type="task",
        subject=f"任务分配: {request.description[:30]}...",
        related_task_id=request.related_task_id or task_id,
        timeout_seconds=request.deadline_hours * 3600,
    )
    
    # 提交后台处理
    background_tasks.add_task(process_message_async, message.id)
    
    return {
        "success": True,
        "message_id": message.id,
        "task_content": task_content,
        "status": "pending",
        "check_url": f"/api/async-messages/{message.id}",
    }


@router.post("/quick-assign")
async def quick_assign_task(
    request: QuickTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    快速分配简单任务
    
    不需要复杂模板，直接发送指令给员工。
    
    **示例请求**:
    ```json
    {
        "agent_id": "agent_abc123",
        "instruction": "请读取 /data/report.txt 并总结要点",
        "output_path": "workspace/tasks/summary.md",
        "budget": 30
    }
    ```
    """
    import uuid
    task_id = str(uuid.uuid4())[:8]
    
    # 生成简化版任务消息
    task_content = f"""📋 **快速任务** | 任务ID: {task_id}

## 🎯 任务
{request.instruction}

## 📤 输出要求
- **保存位置**: {request.output_path or f'workspace/tasks/{task_id}/'}
- **格式**: 根据任务内容确定

## ⏰ 限制
- **预算**: {request.budget} OC币

## 🔗 反馈格式
```
STATUS: completed/failed
RESULT: [结果摘要]
OUTPUT_PATH: [输出路径]
TOKEN_USED: [数字]
```
"""
    
    # 创建异步消息
    message_service = AsyncMessageService(db)
    message = message_service.create_message(
        sender_id="system",
        sender_type="system",
        sender_name="OPC系统",
        recipient_id=request.agent_id,
        content=task_content,
        message_type="task",
        subject=f"快速任务: {request.instruction[:30]}...",
        related_task_id=task_id,
        timeout_seconds=1800,  # 30分钟默认超时
    )
    
    # 提交后台处理
    background_tasks.add_task(process_message_async, message.id)
    
    return {
        "success": True,
        "message_id": message.id,
        "task_id": task_id,
        "status": "pending",
        "check_url": f"/api/async-messages/{message.id}",
    }


@router.get("/templates", response_model=TaskTemplateListResponse)
async def get_task_templates():
    """获取可用的任务模板列表"""
    template_service = TaskTemplateService()
    return {"templates": template_service.get_available_templates()}


@router.post("/parse-result")
async def parse_task_result(
    response_text: str,
    db: Session = Depends(get_db),
):
    """
    解析任务完成反馈（测试/验证用）
    
    **示例请求**:
    ```json
    {
        "response_text": "STATUS: completed\\nRESULT: 查询完成\\nOUTPUT_PATH: /tasks/result.json\\nTOKEN_USED: 100"
    }
    ```
    """
    from services.task_response_parser import TaskResponseParser
    
    parser = TaskResponseParser()
    result = parser.parse_with_fuzzy_matching(response_text)
    is_valid, error_msg = parser.validate_result(result)
    
    return {
        "is_valid_format": result.is_valid_format,
        "validation_error": error_msg if not is_valid else None,
        "parsed": {
            "status": result.status,
            "result_summary": result.result_summary,
            "output_path": result.output_path,
            "token_used": result.token_used,
            "error_reason": result.error_reason,
        }
    }


@router.post("/process-response/{task_id}")
async def process_task_response(
    task_id: str,
    agent_response: str,
    db: Session = Depends(get_db),
):
    """
    处理员工任务完成回复
    
    解析员工回复并更新任务状态。
    """
    handler = TaskResultHandler(db)
    result = handler.process_agent_response(task_id, agent_response)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/agent-tasks/{agent_id}")
async def get_agent_tasks(
    agent_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    获取员工任务历史
    
    查询分配给某员工的所有任务消息。
    """
    from models import AsyncMessage, AsyncMessageStatus
    
    query = db.query(AsyncMessage).filter(
        AsyncMessage.recipient_id == agent_id,
        AsyncMessage.message_type == "task"
    )
    
    if status:
        query = query.filter(AsyncMessage.status == status)
    
    messages = query.order_by(AsyncMessage.created_at.desc()).limit(limit).all()
    
    service = AsyncMessageService(db)
    return {
        "tasks": [service.to_dict(m) for m in messages],
        "total": len(messages),
        "pending_count": len([m for m in messages if m.status in ["pending", "sending", "sent"]]),
    }
