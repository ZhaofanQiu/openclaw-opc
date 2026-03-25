"""
opc-core: 工作流统计服务 (v0.4.2-P2)

工作流统计分析服务

作者: OpenClaw OPC Team
创建日期: 2026-03-25
版本: 0.4.2-P2
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from opc_database.models import Task, TaskStatus
from opc_database.repositories import EmployeeRepository, TaskRepository


@dataclass
class WorkflowStats:
    """工作流整体统计"""
    # 基础统计
    total_workflows: int
    completed_workflows: int
    failed_workflows: int
    in_progress_workflows: int
    
    # 成功率
    completion_rate: float  # 百分比
    failure_rate: float
    
    # 耗时统计（分钟）
    avg_duration: float
    min_duration: float
    max_duration: float
    total_duration: float
    
    # 返工统计
    total_reworks: int
    avg_reworks_per_workflow: float
    rework_rate: float  # 百分比
    

@dataclass
class StepStats:
    """步骤统计"""
    step_index: int
    title: str
    avg_duration_minutes: float
    min_duration_minutes: float
    max_duration_minutes: float
    completed_count: int
    rework_count: int
    rework_rate: float  # 百分比


@dataclass
class DailyStats:
    """每日统计"""
    date: str  # YYYY-MM-DD
    created: int
    completed: int
    failed: int
    reworks: int


@dataclass
class EmployeeWorkflowStats:
    """员工工作流统计"""
    employee_id: str
    employee_name: str
    employee_emoji: Optional[str]
    
    tasks_completed: int
    tasks_failed: int
    tasks_reworked: int
    
    avg_task_duration_minutes: float
    total_tokens_used: int
    
    completion_rate: float
    rework_rate: float
    score: float  # 综合评分 0-100


class WorkflowAnalyticsService:
    """工作流统计服务
    
    提供工作流的各种统计分析功能
    """
    
    def __init__(
        self,
        task_repo: TaskRepository,
        emp_repo: EmployeeRepository,
    ):
        self.task_repo = task_repo
        self.emp_repo = emp_repo
    
    # ========================================
    # 整体统计
    # ========================================
    
    async def get_workflow_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> WorkflowStats:
        """获取工作流整体统计"""
        # 获取时间范围内的所有任务
        tasks = await self._get_tasks_in_range(start_date, end_date)
        
        # 按 workflow_id 分组
        workflow_tasks: Dict[str, List[Task]] = {}
        for task in tasks:
            if task.workflow_id:
                if task.workflow_id not in workflow_tasks:
                    workflow_tasks[task.workflow_id] = []
                workflow_tasks[task.workflow_id].append(task)
        
        total = len(workflow_tasks)
        if total == 0:
            return WorkflowStats(
                total_workflows=0,
                completed_workflows=0,
                failed_workflows=0,
                in_progress_workflows=0,
                completion_rate=0.0,
                failure_rate=0.0,
                avg_duration=0.0,
                min_duration=0.0,
                max_duration=0.0,
                total_duration=0.0,
                total_reworks=0,
                avg_reworks_per_workflow=0.0,
                rework_rate=0.0,
            )
        
        # 统计各状态工作流数量
        completed = 0
        failed = 0
        in_progress = 0
        durations = []
        total_reworks = 0
        
        for workflow_id, wf_tasks in workflow_tasks.items():
            # 检查工作流状态
            all_completed = all(t.status == TaskStatus.COMPLETED.value for t in wf_tasks)
            any_failed = any(t.status == TaskStatus.FAILED.value for t in wf_tasks)
            any_in_progress = any(t.status == TaskStatus.IN_PROGRESS.value for t in wf_tasks)
            
            if all_completed:
                completed += 1
                # 计算耗时
                duration = self._calculate_duration(wf_tasks)
                if duration > 0:
                    durations.append(duration)
            elif any_failed:
                failed += 1
            elif any_in_progress:
                in_progress += 1
            
            # 统计返工
            reworks = sum(1 for t in wf_tasks if t.is_rework)
            total_reworks += reworks
        
        # 计算耗时统计
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        return WorkflowStats(
            total_workflows=total,
            completed_workflows=completed,
            failed_workflows=failed,
            in_progress_workflows=in_progress,
            completion_rate=round(completed / total * 100, 1) if total > 0 else 0,
            failure_rate=round(failed / total * 100, 1) if total > 0 else 0,
            avg_duration=round(avg_duration, 1),
            min_duration=round(min_duration, 1),
            max_duration=round(max_duration, 1),
            total_duration=round(sum(durations), 1),
            total_reworks=total_reworks,
            avg_reworks_per_workflow=round(total_reworks / total, 2) if total > 0 else 0,
            rework_rate=round(total_reworks / len(tasks) * 100, 1) if tasks else 0,
        )
    
    # ========================================
    # 步骤分析
    # ========================================
    
    async def get_step_analysis(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[StepStats]:
        """获取步骤耗时和返工分析"""
        tasks = await self._get_tasks_in_range(start_date, end_date)
        
        # 只分析工作流任务
        workflow_tasks = [t for t in tasks if t.workflow_id is not None]
        
        if not workflow_tasks:
            return []
        
        # 按步骤索引分组
        step_groups: Dict[int, List[Task]] = {}
        for task in workflow_tasks:
            idx = task.step_index or 0
            if idx not in step_groups:
                step_groups[idx] = []
            step_groups[idx].append(task)
        
        stats = []
        for step_index, step_tasks in sorted(step_groups.items()):
            # 计算耗时
            durations = []
            for task in step_tasks:
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds() / 60
                    if duration > 0:
                        durations.append(duration)
            
            # 统计完成数和返工数
            completed = sum(1 for t in step_tasks if t.status == TaskStatus.COMPLETED.value)
            reworks = sum(1 for t in step_tasks if t.is_rework)
            
            # 获取步骤标题（使用最常见的标题）
            titles = {}
            for task in step_tasks:
                title = task.title or f"Step {step_index + 1}"
                titles[title] = titles.get(title, 0) + 1
            most_common_title = max(titles.items(), key=lambda x: x[1])[0] if titles else f"Step {step_index + 1}"
            
            stats.append(StepStats(
                step_index=step_index,
                title=most_common_title,
                avg_duration_minutes=round(sum(durations) / len(durations), 1) if durations else 0,
                min_duration_minutes=round(min(durations), 1) if durations else 0,
                max_duration_minutes=round(max(durations), 1) if durations else 0,
                completed_count=completed,
                rework_count=reworks,
                rework_rate=round(reworks / len(step_tasks) * 100, 1) if step_tasks else 0,
            ))
        
        return stats
    
    # ========================================
    # 趋势分析
    # ========================================
    
    async def get_daily_trend(
        self,
        days: int = 30,
        end_date: Optional[datetime] = None,
    ) -> List[DailyStats]:
        """获取每日趋势统计"""
        if end_date is None:
            end_date = datetime.utcnow()
        
        start_date = end_date - timedelta(days=days)
        
        tasks = await self._get_tasks_in_range(start_date, end_date)
        workflow_tasks = [t for t in tasks if t.workflow_id is not None]
        
        # 生成日期范围
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current.date())
            current += timedelta(days=1)
        
        # 统计每天的数据
        daily_stats = []
        for date in dates:
            date_str = date.isoformat()
            
            # 当天创建的任务（推断工作流创建）
            created = sum(
                1 for t in workflow_tasks
                if t.created_at and t.created_at.date() == date and t.step_index == 0
            )
            
            # 当天完成的任务
            completed = sum(
                1 for t in workflow_tasks
                if t.completed_at and t.completed_at.date() == date
                and t.status == TaskStatus.COMPLETED.value
            )
            
            # 当天失败的任务
            failed = sum(
                1 for t in workflow_tasks
                if t.completed_at and t.completed_at.date() == date
                and t.status == TaskStatus.FAILED.value
            )
            
            # 当天返工的任务
            reworks = sum(
                1 for t in workflow_tasks
                if t.created_at and t.created_at.date() == date
                and t.is_rework
            )
            
            daily_stats.append(DailyStats(
                date=date_str,
                created=created,
                completed=completed,
                failed=failed,
                reworks=reworks,
            ))
        
        return daily_stats
    
    # ========================================
    # 员工排名
    # ========================================
    
    async def get_employee_rankings(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[EmployeeWorkflowStats]:
        """获取员工效率排名"""
        tasks = await self._get_tasks_in_range(start_date, end_date)
        
        # 按员工分组
        emp_tasks: Dict[str, List[Task]] = {}
        for task in tasks:
            if task.assigned_to:
                if task.assigned_to not in emp_tasks:
                    emp_tasks[task.assigned_to] = []
                emp_tasks[task.assigned_to].append(task)
        
        rankings = []
        for emp_id, tasks_list in emp_tasks.items():
            # 获取员工信息
            emp = await self.emp_repo.get_by_id(emp_id)
            if not emp:
                continue
            
            # 统计数据
            completed = sum(1 for t in tasks_list if t.status == TaskStatus.COMPLETED.value)
            failed = sum(1 for t in tasks_list if t.status == TaskStatus.FAILED.value)
            reworked = sum(1 for t in tasks_list if t.is_rework)
            
            # 计算平均耗时
            durations = []
            for task in tasks_list:
                if task.started_at and task.completed_at:
                    duration = (task.completed_at - task.started_at).total_seconds() / 60
                    if duration > 0:
                        durations.append(duration)
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Token使用
            total_tokens = sum(t.tokens_input + t.tokens_output for t in tasks_list)
            
            # 计算率
            total = len(tasks_list)
            completion_rate = completed / total * 100 if total > 0 else 0
            rework_rate = reworked / total * 100 if total > 0 else 0
            
            # 综合评分（0-100）
            # 完成率 * 0.4 + (1-返工率) * 0.3 + 效率分 * 0.3
            # 效率分：根据平均耗时，假设30分钟为满分
            efficiency_score = max(0, 100 - avg_duration / 30 * 100) if avg_duration > 0 else 50
            score = (
                completion_rate * 0.4 +
                (100 - rework_rate) * 0.3 +
                efficiency_score * 0.3
            )
            
            rankings.append(EmployeeWorkflowStats(
                employee_id=emp_id,
                employee_name=emp.name,
                employee_emoji=emp.emoji,
                tasks_completed=completed,
                tasks_failed=failed,
                tasks_reworked=reworked,
                avg_task_duration_minutes=round(avg_duration, 1),
                total_tokens_used=total_tokens,
                completion_rate=round(completion_rate, 1),
                rework_rate=round(rework_rate, 1),
                score=round(score, 1),
            ))
        
        # 按评分排序
        rankings.sort(key=lambda x: x.score, reverse=True)
        return rankings[:limit]
    
    # ========================================
    # 单工作流统计
    # ========================================
    
    async def get_single_workflow_stats(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取单个工作流的统计详情"""
        tasks = await self.task_repo.get_by_workflow(workflow_id)
        if not tasks:
            return None
        
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED.value]
        failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED.value]
        rework_tasks = [t for t in tasks if t.is_rework]
        
        # 计算耗时
        durations = []
        for task in completed_tasks:
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds() / 60
                if duration > 0:
                    durations.append(duration)
        
        # Token使用
        total_tokens = sum(t.tokens_input + t.tokens_output for t in tasks)
        
        # 获取状态
        if len(completed_tasks) == len(tasks):
            status = "completed"
        elif failed_tasks:
            status = "failed"
        else:
            status = "in_progress"
        
        return {
            "workflow_id": workflow_id,
            "status": status,
            "total_steps": len(tasks),
            "completed_steps": len(completed_tasks),
            "failed_steps": len(failed_tasks),
            "rework_count": len(rework_tasks),
            "total_duration_minutes": round(sum(durations), 1) if durations else 0,
            "avg_step_duration_minutes": round(sum(durations) / len(durations), 1) if durations else 0,
            "total_tokens_used": total_tokens,
            "completion_rate": round(len(completed_tasks) / len(tasks) * 100, 1),
        }
    
    # ========================================
    # 辅助方法
    # ========================================
    
    async def _get_tasks_in_range(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[Task]:
        """获取时间范围内的任务"""
        # 这里简化处理，实际应该通过 repository 查询
        # 由于没有日期范围查询，先返回所有任务
        # TODO: 添加日期范围查询到 TaskRepository
        
        # 临时方案：获取所有工作流任务
        # 实际应该根据日期过滤
        return []  # 需要实现具体的查询
    
    def _calculate_duration(self, tasks: List[Task]) -> float:
        """计算工作流总耗时（分钟）"""
        start_times = [t.started_at for t in tasks if t.started_at]
        end_times = [t.completed_at for t in tasks if t.completed_at]
        
        if not start_times or not end_times:
            return 0.0
        
        earliest_start = min(start_times)
        latest_end = max(end_times)
        
        duration = (latest_end - earliest_start).total_seconds() / 60
        return max(0, duration)
    
    # ========================================
    # API 格式化
    # ========================================
    
    def format_stats_for_api(self, stats: WorkflowStats) -> Dict[str, Any]:
        """格式化统计为API响应"""
        return {
            "overview": {
                "total_workflows": stats.total_workflows,
                "completed": stats.completed_workflows,
                "failed": stats.failed_workflows,
                "in_progress": stats.in_progress_workflows,
                "completion_rate": stats.completion_rate,
                "failure_rate": stats.failure_rate,
            },
            "duration": {
                "avg_minutes": stats.avg_duration,
                "min_minutes": stats.min_duration,
                "max_minutes": stats.max_duration,
                "total_minutes": stats.total_duration,
            },
            "rework": {
                "total_reworks": stats.total_reworks,
                "avg_per_workflow": stats.avg_reworks_per_workflow,
                "rework_rate": stats.rework_rate,
            },
        }
    
    def format_step_stats_for_api(self, stats: List[StepStats]) -> List[Dict[str, Any]]:
        """格式化步骤统计为API响应"""
        return [
            {
                "step_index": s.step_index,
                "title": s.title,
                "avg_duration_minutes": s.avg_duration_minutes,
                "min_duration_minutes": s.min_duration_minutes,
                "max_duration_minutes": s.max_duration_minutes,
                "completed_count": s.completed_count,
                "rework_count": s.rework_count,
                "rework_rate": s.rework_rate,
            }
            for s in stats
        ]
    
    def format_daily_stats_for_api(self, stats: List[DailyStats]) -> List[Dict[str, Any]]:
        """格式化每日统计为API响应"""
        return [
            {
                "date": s.date,
                "created": s.created,
                "completed": s.completed,
                "failed": s.failed,
                "reworks": s.reworks,
            }
            for s in stats
        ]
    
    def format_employee_stats_for_api(self, stats: List[EmployeeWorkflowStats]) -> List[Dict[str, Any]]:
        """格式化员工统计为API响应"""
        return [
            {
                "employee_id": s.employee_id,
                "employee_name": s.employee_name,
                "employee_emoji": s.employee_emoji,
                "tasks_completed": s.tasks_completed,
                "tasks_failed": s.tasks_failed,
                "tasks_reworked": s.tasks_reworked,
                "avg_task_duration_minutes": s.avg_task_duration_minutes,
                "total_tokens_used": s.total_tokens_used,
                "completion_rate": s.completion_rate,
                "rework_rate": s.rework_rate,
                "score": s.score,
            }
            for s in stats
        ]
