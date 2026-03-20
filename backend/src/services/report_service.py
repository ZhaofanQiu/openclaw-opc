"""
Daily report service for generating work summaries.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models import Agent, BudgetTransaction, Task


class ReportService:
    """Service for generating daily/periodic reports."""

    def __init__(self, db: Session):
        self.db = db

    def generate_daily_report(self, report_date: Optional[date] = None) -> Dict:
        """
        Generate daily work report.

        Args:
            report_date: Date for report (default: yesterday)

        Returns:
            Report data including tasks, budget, agent stats
        """
        if report_date is None:
            report_date = date.today() - timedelta(days=1)

        # Date range for the report day
        start_of_day = datetime.combine(report_date, datetime.min.time())
        end_of_day = datetime.combine(report_date, datetime.max.time())

        # Get tasks completed on this day
        completed_tasks = self.db.query(Task).filter(
            Task.status == "completed",
            Task.completed_at >= start_of_day,
            Task.completed_at <= end_of_day
        ).all()

        # Get budget transactions for the day
        transactions = self.db.query(BudgetTransaction).filter(
            BudgetTransaction.created_at >= start_of_day,
            BudgetTransaction.created_at <= end_of_day
        ).all()

        # Calculate total budget consumed
        total_consumed = sum(t.amount for t in transactions if t.amount < 0)

        # Agent statistics
        agent_stats = {}
        for task in completed_tasks:
            agent_id = task.agent_id
            if agent_id not in agent_stats:
                agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
                agent_stats[agent_id] = {
                    "name": agent.name if agent else "Unknown",
                    "emoji": agent.emoji if agent else "❓",
                    "tasks_completed": 0,
                    "budget_consumed": 0.0,
                    "tasks": []
                }

            agent_stats[agent_id]["tasks_completed"] += 1
            agent_stats[agent_id]["budget_consumed"] += task.actual_cost
            agent_stats[agent_id]["tasks"].append({
                "id": task.id,
                "title": task.title,
                "cost": task.actual_cost
            })

        # Calculate completion rate for tasks created that day
        tasks_created = self.db.query(Task).filter(
            Task.created_at >= start_of_day,
            Task.created_at <= end_of_day
        ).all()

        created_count = len(tasks_created)
        completed_same_day = len([
            t for t in tasks_created
            if t.status == "completed" and t.completed_at
            and start_of_day <= t.completed_at <= end_of_day
        ])

        completion_rate = (completed_same_day / created_count * 100) if created_count > 0 else 0

        return {
            "date": report_date.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_tasks_completed": len(completed_tasks),
                "total_budget_consumed": abs(total_consumed),
                "tasks_created": created_count,
                "completion_rate": round(completion_rate, 1)
            },
            "agent_performance": list(agent_stats.values()),
            "completed_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "agent_name": agent_stats.get(t.agent_id, {}).get("name", "Unknown"),
                    "actual_cost": t.actual_cost,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in completed_tasks
            ]
        }

    def generate_weekly_report(self, week_start: Optional[date] = None) -> Dict:
        """
        Generate weekly work report.

        Args:
            week_start: Start date of the week (default: last Monday)

        Returns:
            Weekly report data
        """
        if week_start is None:
            # Find last Monday
            today = date.today()
            week_start = today - timedelta(days=today.weekday() + 7)

        week_end = week_start + timedelta(days=6)

        start_datetime = datetime.combine(week_start, datetime.min.time())
        end_datetime = datetime.combine(week_end, datetime.max.time())

        # Get all completed tasks in the week
        completed_tasks = self.db.query(Task).filter(
            Task.status == "completed",
            Task.completed_at >= start_datetime,
            Task.completed_at <= end_datetime
        ).all()

        # Get budget transactions
        transactions = self.db.query(BudgetTransaction).filter(
            BudgetTransaction.created_at >= start_datetime,
            BudgetTransaction.created_at <= end_datetime
        ).all()

        total_consumed = sum(t.amount for t in transactions if t.amount < 0)

        # Daily breakdown
        daily_stats = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            daily_stats[day.isoformat()] = {
                "tasks_completed": 0,
                "budget_consumed": 0.0
            }

        for task in completed_tasks:
            if task.completed_at:
                day_key = task.completed_at.date().isoformat()
                if day_key in daily_stats:
                    daily_stats[day_key]["tasks_completed"] += 1
                    daily_stats[day_key]["budget_consumed"] += task.actual_cost

        return {
            "period": "weekly",
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_tasks_completed": len(completed_tasks),
                "total_budget_consumed": abs(total_consumed),
                "daily_breakdown": daily_stats
            },
            "completed_tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "actual_cost": t.actual_cost,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in completed_tasks
            ]
        }

    def get_recent_reports(self, days: int = 7) -> List[Dict]:
        """
        Get daily reports for recent days.

        Args:
            days: Number of days to include

        Returns:
            List of daily reports
        """
        reports = []
        today = date.today()

        for i in range(days):
            report_date = today - timedelta(days=i+1)
            report = self.generate_daily_report(report_date)
            reports.append(report)

        return reports
