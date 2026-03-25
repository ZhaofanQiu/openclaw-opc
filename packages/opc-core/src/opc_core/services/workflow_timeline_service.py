"""
opc-core: 工作流时间线服务 (v0.4.2-P2)

工作流执行历史时间线构建

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from opc_database.models import Task, TaskStatus
from opc_database.repositories import TaskRepository


class TimelineEventType(str, Enum):
    """时间线事件类型"""
    WORKFLOW_CREATED = "workflow_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    REWORK_REQUESTED = "rework_requested"
    REWORK_COMPLETED = "rework_completed"
    WORKFLOW_COMPLETED = "workflow_completed"


@dataclass
class TimelineEvent:
    """时间线事件"""
    timestamp: datetime
    event_type: TimelineEventType
    step_index: Optional[int]
    task_id: Optional[str]
    title: str
    description: str
    actor: str  # 执行者（用户ID或员工名称）
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TimelineSummary:
    """时间线摘要统计"""
    total_duration_minutes: float
    total_tasks: int
    completed_tasks: int
    rework_count: int
    avg_task_duration_minutes: float
    step_durations: List[Dict[str, Any]]  # 每步耗时


class WorkflowTimelineService:
    """工作流时间线服务
    
    构建工作流执行历史的时间线展示
    """
    
    def __init__(self, task_repo: TaskRepository):
        self.task_repo = task_repo
    
    # ========================================
    # 核心方法: 构建时间线
    # ========================================
    
    async def build_timeline(self, workflow_id: str) -> List[TimelineEvent]:
        """构建工作流时间线"""
        tasks = await self.task_repo.get_by_workflow(workflow_id)
        if not tasks:
            return []
        
        events = []
        
        # 1. 工作流创建事件（从第一个任务的创建时间推断）
        first_task = min(tasks, key=lambda t: t.created_at or datetime.max)
        events.append(TimelineEvent(
            timestamp=first_task.created_at,
            event_type=TimelineEventType.WORKFLOW_CREATED,
            step_index=None,
            task_id=None,
            title="工作流创建",
            description=f"创建 {len(tasks)} 步骤工作流",
            actor=first_task.assigned_by or "system",
            metadata={"total_steps": len(tasks)},
        ))
        
        # 2. 按步骤顺序处理每个任务的事件
        sorted_tasks = sorted(tasks, key=lambda t: t.step_index or 0)
        
        for task in sorted_tasks:
            task_events = self._extract_task_events(task)
            events.extend(task_events)
        
        # 3. 工作流完成事件（从最后一个完成的任务推断）
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED.value]
        if completed_tasks and len(completed_tasks) == len(tasks):
            last_completed = max(completed_tasks, key=lambda t: t.completed_at or datetime.min)
            events.append(TimelineEvent(
                timestamp=last_completed.completed_at,
                event_type=TimelineEventType.WORKFLOW_COMPLETED,
                step_index=None,
                task_id=None,
                title="工作流完成",
                description=f"所有 {len(tasks)} 个步骤已完成",
                actor="system",
                metadata={"total_duration": self._calculate_workflow_duration(tasks)},
            ))
        
        # 按时间排序
        events.sort(key=lambda e: e.timestamp or datetime.min)
        
        return events
    
    async def get_timeline_summary(self, workflow_id: str) -> Optional[TimelineSummary]:
        """获取时间线摘要统计"""
        tasks = await self.task_repo.get_by_workflow(workflow_id)
        if not tasks:
            return None
        
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED.value]
        
        # 计算总耗时
        total_duration = self._calculate_workflow_duration(tasks)
        
        # 计算每步耗时
        step_durations = []
        for task in tasks:
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds() / 60
                step_durations.append({
                    "step_index": task.step_index,
                    "title": task.title,
                    "duration_minutes": round(duration, 1),
                })
        
        # 计算返工次数
        rework_count = sum(1 for t in tasks if t.is_rework)
        
        # 平均任务耗时
        avg_duration = total_duration / len(completed_tasks) if completed_tasks else 0
        
        return TimelineSummary(
            total_duration_minutes=round(total_duration, 1),
            total_tasks=len(tasks),
            completed_tasks=len(completed_tasks),
            rework_count=rework_count,
            avg_task_duration_minutes=round(avg_duration, 1),
            step_durations=step_durations,
        )
    
    # ========================================
    # 辅助方法
    # ========================================
    
    def _extract_task_events(self, task: Task) -> List[TimelineEvent]:
        """从任务中提取时间线事件"""
        events = []
        
        # 从执行日志中提取事件
        if task.execution_log:
            try:
                logs = json.loads(task.execution_log)
                for log in logs:
                    event = self._parse_log_entry(task, log)
                    if event:
                        events.append(event)
            except json.JSONDecodeError:
                pass
        
        # 如果没有日志，从任务状态推断基本事件
        if not events:
            events = self._infer_events_from_status(task)
        
        return events
    
    def _parse_log_entry(self, task: Task, log: Dict[str, Any]) -> Optional[TimelineEvent]:
        """解析日志条目为时间线事件"""
        event_type_str = log.get("event", "")
        timestamp_str = log.get("timestamp")
        
        if not timestamp_str:
            return None
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.utcnow()
        
        # 事件类型映射
        event_mapping = {
            "task_assigned": (TimelineEventType.TASK_ASSIGNED, "任务分配"),
            "task_started": (TimelineEventType.TASK_STARTED, "任务开始"),
            "task_completed": (TimelineEventType.TASK_COMPLETED, "任务完成"),
            "task_failed": (TimelineEventType.TASK_FAILED, "任务失败"),
            "rework_created": (TimelineEventType.REWORK_REQUESTED, "返工请求"),
            "rework_completed": (TimelineEventType.REWORK_COMPLETED, "返工完成"),
        }
        
        if event_type_str not in event_mapping:
            return None
        
        event_type, default_title = event_mapping[event_type_str]
        
        # 构建描述
        description = log.get("message", "")
        if not description:
            if event_type == TimelineEventType.TASK_COMPLETED:
                # 从output_data提取摘要
                try:
                    output = json.loads(task.output_data) if task.output_data else {}
                    description = output.get("summary", "任务已完成")
                except:
                    description = "任务已完成"
            elif event_type == TimelineEventType.REWORK_REQUESTED:
                reason = log.get("reason", "")
                description = f"返工原因: {reason}" if reason else "请求返工"
            else:
                description = default_title
        
        # 构建metadata
        metadata = {}
        if "tokens_used" in log:
            metadata["tokens_used"] = log["tokens_used"]
        if "duration_seconds" in log:
            metadata["duration_minutes"] = round(log["duration_seconds"] / 60, 1)
        if "error" in log:
            metadata["error"] = log["error"]
        
        return TimelineEvent(
            timestamp=timestamp,
            event_type=event_type,
            step_index=task.step_index,
            task_id=task.id,
            title=f"Step {task.step_index + 1}: {default_title}" if task.step_index is not None else default_title,
            description=description,
            actor=task.assigned_to or "system",
            metadata=metadata if metadata else None,
        )
    
    def _infer_events_from_status(self, task: Task) -> List[TimelineEvent]:
        """从任务状态推断事件（无日志时备用）"""
        events = []
        
        # 分配事件
        if task.assigned_at:
            events.append(TimelineEvent(
                timestamp=task.assigned_at,
                event_type=TimelineEventType.TASK_ASSIGNED,
                step_index=task.step_index,
                task_id=task.id,
                title=f"Step {task.step_index + 1}: 任务分配",
                description=f"分配给 {task.assigned_to}",
                actor=task.assigned_by or "system",
            ))
        
        # 开始事件
        if task.started_at:
            events.append(TimelineEvent(
                timestamp=task.started_at,
                event_type=TimelineEventType.TASK_STARTED,
                step_index=task.step_index,
                task_id=task.id,
                title=f"Step {task.step_index + 1}: 任务开始",
                description="Agent开始执行任务",
                actor=task.assigned_to or "system",
            ))
        
        # 完成/失败事件
        if task.completed_at:
            if task.status == TaskStatus.COMPLETED.value:
                # 尝试获取摘要
                description = "任务已完成"
                try:
                    output = json.loads(task.output_data) if task.output_data else {}
                    description = output.get("summary", description)[:100]
                except:
                    pass
                
                events.append(TimelineEvent(
                    timestamp=task.completed_at,
                    event_type=TimelineEventType.TASK_COMPLETED,
                    step_index=task.step_index,
                    task_id=task.id,
                    title=f"Step {task.step_index + 1}: 任务完成",
                    description=description,
                    actor=task.assigned_to or "system",
                    metadata={
                        "tokens_input": task.tokens_input,
                        "tokens_output": task.tokens_output,
                    } if task.tokens_input or task.tokens_output else None,
                ))
            elif task.status == TaskStatus.FAILED.value:
                events.append(TimelineEvent(
                    timestamp=task.completed_at,
                    event_type=TimelineEventType.TASK_FAILED,
                    step_index=task.step_index,
                    task_id=task.id,
                    title=f"Step {task.step_index + 1}: 任务失败",
                    description="任务执行失败",
                    actor=task.assigned_to or "system",
                ))
        
        return events
    
    def _calculate_workflow_duration(self, tasks: List[Task]) -> float:
        """计算工作流总耗时（分钟）"""
        # 找到最早的开始时间和最晚的结束时间
        start_times = [t.started_at for t in tasks if t.started_at]
        end_times = [t.completed_at for t in tasks if t.completed_at]
        
        if not start_times or not end_times:
            return 0.0
        
        earliest_start = min(start_times)
        latest_end = max(end_times)
        
        duration = (latest_end - earliest_start).total_seconds() / 60
        return max(0, duration)
    
    # ========================================
    # 格式化输出
    # ========================================
    
    def format_timeline_for_api(self, events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        """格式化时间线为API响应格式"""
        return [
            {
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "event_type": e.event_type.value,
                "step_index": e.step_index,
                "task_id": e.task_id,
                "title": e.title,
                "description": e.description,
                "actor": e.actor,
                "metadata": e.metadata,
            }
            for e in events
        ]
    
    def format_summary_for_api(self, summary: TimelineSummary) -> Dict[str, Any]:
        """格式化摘要统计为API响应格式"""
        return {
            "total_duration_minutes": summary.total_duration_minutes,
            "total_tasks": summary.total_tasks,
            "completed_tasks": summary.completed_tasks,
            "rework_count": summary.rework_count,
            "avg_task_duration_minutes": summary.avg_task_duration_minutes,
            "step_durations": summary.step_durations,
            "completion_rate": round(
                summary.completed_tasks / summary.total_tasks * 100, 1
            ) if summary.total_tasks > 0 else 0,
        }
