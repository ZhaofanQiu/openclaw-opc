"""
opc-core: 工作流时间线服务测试 (v0.4.2-P2)

测试 WorkflowTimelineService

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from opc_database.models import Task, TaskStatus
from opc_core.services import (
    TimelineEventType,
    WorkflowTimelineService,
)


@pytest.fixture
def mock_task_repo():
    """模拟任务仓库"""
    return AsyncMock()


@pytest.fixture
def timeline_service(mock_task_repo):
    """时间线服务实例"""
    return WorkflowTimelineService(mock_task_repo)


@pytest.fixture
def sample_tasks():
    """示例任务列表"""
    now = datetime.utcnow()
    
    return [
        Task(
            id="task-1",
            workflow_id="wf-001",
            title="步骤1",
            step_index=0,
            status=TaskStatus.COMPLETED.value,
            created_at=now,
            assigned_at=now + timedelta(minutes=1),
            started_at=now + timedelta(minutes=2),
            completed_at=now + timedelta(minutes=12),
            assigned_to="emp-1",
            assigned_by="user-1",
            is_rework=False,
            tokens_input=100,
            tokens_output=200,
        ),
        Task(
            id="task-2",
            workflow_id="wf-001",
            title="步骤2",
            step_index=1,
            status=TaskStatus.COMPLETED.value,
            created_at=now,
            assigned_at=now + timedelta(minutes=13),
            started_at=now + timedelta(minutes=14),
            completed_at=now + timedelta(minutes=20),
            assigned_to="emp-2",
            assigned_by="user-1",
            is_rework=False,
            tokens_input=50,
            tokens_output=100,
        ),
    ]


class TestWorkflowTimelineService:
    """工作流时间线服务测试"""
    
    @pytest.mark.asyncio
    async def test_build_timeline(self, timeline_service, mock_task_repo, sample_tasks):
        """测试构建时间线"""
        mock_task_repo.get_by_workflow.return_value = sample_tasks
        
        events = await timeline_service.build_timeline("wf-001")
        
        # 应该有多个事件：创建、分配、开始、完成等
        assert len(events) > 0
        
        # 验证事件类型
        event_types = [e.event_type for e in events]
        assert TimelineEventType.WORKFLOW_CREATED in event_types
        assert TimelineEventType.TASK_ASSIGNED in event_types
        assert TimelineEventType.TASK_STARTED in event_types
        assert TimelineEventType.TASK_COMPLETED in event_types
        assert TimelineEventType.WORKFLOW_COMPLETED in event_types
    
    @pytest.mark.asyncio
    async def test_build_timeline_empty(self, timeline_service, mock_task_repo):
        """测试空工作流时间线"""
        mock_task_repo.get_by_workflow.return_value = []
        
        events = await timeline_service.build_timeline("wf-empty")
        
        assert len(events) == 0
    
    @pytest.mark.asyncio
    async def test_build_timeline_with_rework(self, timeline_service, mock_task_repo):
        """测试包含返工的时间线"""
        now = datetime.utcnow()
        
        # 创建一个有返工的任务
        rework_task = Task(
            id="task-rework",
            workflow_id="wf-002",
            title="返工步骤",
            step_index=0,
            status=TaskStatus.COMPLETED.value,
            created_at=now,
            started_at=now,
            completed_at=now + timedelta(minutes=10),
            assigned_to="emp-1",
            is_rework=True,
        )
        
        # 添加执行日志
        rework_task.execution_log = json.dumps([
            {
                "event": "rework_created",
                "timestamp": now.isoformat(),
                "reason": "需要修改",
            },
            {
                "event": "rework_completed",
                "timestamp": (now + timedelta(minutes=10)).isoformat(),
            }
        ])
        
        mock_task_repo.get_by_workflow.return_value = [rework_task]
        
        events = await timeline_service.build_timeline("wf-002")
        
        # 验证返工事件
        event_types = [e.event_type for e in events]
        assert TimelineEventType.REWORK_REQUESTED in event_types
        assert TimelineEventType.REWORK_COMPLETED in event_types
    
    @pytest.mark.asyncio
    async def test_get_timeline_summary(self, timeline_service, mock_task_repo, sample_tasks):
        """测试获取时间线摘要"""
        mock_task_repo.get_by_workflow.return_value = sample_tasks
        
        summary = await timeline_service.get_timeline_summary("wf-001")
        
        assert summary is not None
        assert summary.total_tasks == 2
        assert summary.completed_tasks == 2
        assert summary.rework_count == 0
        assert summary.total_duration_minutes > 0
        assert len(summary.step_durations) == 2
    
    @pytest.mark.asyncio
    async def test_get_timeline_summary_empty(self, timeline_service, mock_task_repo):
        """测试空工作流摘要"""
        mock_task_repo.get_by_workflow.return_value = []
        
        summary = await timeline_service.get_timeline_summary("wf-empty")
        
        assert summary is None
    
    def test_extract_task_events_from_logs(self, timeline_service):
        """测试从日志提取事件"""
        now = datetime.utcnow()
        
        task = Task(
            id="task-1",
            title="测试任务",
            step_index=0,
            assigned_to="emp-1",
            execution_log=json.dumps([
                {
                    "event": "task_started",
                    "timestamp": now.isoformat(),
                    "message": "开始执行",
                },
                {
                    "event": "task_completed",
                    "timestamp": (now + timedelta(minutes=10)).isoformat(),
                    "message": "完成",
                    "tokens_used": 150,
                    "duration_seconds": 600,
                }
            ]),
        )
        
        events = timeline_service._extract_task_events(task)
        
        assert len(events) == 2
        assert events[0].event_type == TimelineEventType.TASK_STARTED
        assert events[1].event_type == TimelineEventType.TASK_COMPLETED
        assert events[1].metadata["tokens_used"] == 150
    
    def test_infer_events_from_status_assigned(self, timeline_service):
        """测试从状态推断分配事件"""
        now = datetime.utcnow()
        
        task = Task(
            id="task-1",
            title="测试",
            step_index=0,
            assigned_at=now,
            assigned_to="emp-1",
            assigned_by="user-1",
        )
        
        events = timeline_service._infer_events_from_status(task)
        
        assert len(events) >= 1
        assert events[0].event_type == TimelineEventType.TASK_ASSIGNED
    
    def test_infer_events_from_status_completed(self, timeline_service):
        """测试从状态推断完成事件"""
        now = datetime.utcnow()
        
        task = Task(
            id="task-1",
            title="测试",
            step_index=0,
            status=TaskStatus.COMPLETED.value,
            started_at=now,
            completed_at=now + timedelta(minutes=10),
            assigned_to="emp-1",
            output_data=json.dumps({"summary": "任务已完成"}),
            tokens_input=100,
            tokens_output=200,
        )
        
        events = timeline_service._infer_events_from_status(task)
        
        completed_events = [e for e in events if e.event_type == TimelineEventType.TASK_COMPLETED]
        assert len(completed_events) == 1
        assert completed_events[0].metadata["tokens_input"] == 100
    
    def test_calculate_workflow_duration(self, timeline_service, sample_tasks):
        """测试计算工作流总耗时"""
        duration = timeline_service._calculate_duration(sample_tasks)
        
        assert duration > 0
        # 第一个任务开始到最后一个任务完成
        expected_duration = 20  # 分钟
        assert abs(duration - expected_duration) < 1  # 允许1分钟误差
    
    def test_format_timeline_for_api(self, timeline_service):
        """测试格式化时间线为API响应"""
        from opc_core.services.workflow_timeline_service import TimelineEvent
        
        now = datetime.utcnow()
        events = [
            TimelineEvent(
                timestamp=now,
                event_type=TimelineEventType.TASK_COMPLETED,
                step_index=0,
                task_id="task-1",
                title="完成步骤1",
                description="任务已完成",
                actor="emp-1",
                metadata={"tokens_used": 100},
            )
        ]
        
        result = timeline_service.format_timeline_for_api(events)
        
        assert len(result) == 1
        assert result[0]["event_type"] == "task_completed"
        assert result[0]["metadata"]["tokens_used"] == 100
    
    def test_format_summary_for_api(self, timeline_service):
        """测试格式化摘要统计为API响应"""
        from opc_core.services.workflow_timeline_service import TimelineSummary
        
        summary = TimelineSummary(
            total_duration_minutes=30.5,
            total_tasks=3,
            completed_tasks=3,
            rework_count=1,
            avg_task_duration_minutes=10.2,
            step_durations=[
                {"step_index": 0, "title": "步骤1", "duration_minutes": 10},
                {"step_index": 1, "title": "步骤2", "duration_minutes": 20.5},
            ],
        )
        
        result = timeline_service.format_summary_for_api(summary)
        
        assert result["total_duration_minutes"] == 30.5
        assert result["total_tasks"] == 3
        assert result["completion_rate"] == 100.0
        assert len(result["step_durations"]) == 2
