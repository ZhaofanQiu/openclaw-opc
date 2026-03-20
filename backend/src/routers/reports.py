"""
Report API routes.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.report_service import ReportService

router = APIRouter()


class DailyReportResponse(BaseModel):
    """Daily report response."""
    date: str
    generated_at: str
    summary: dict
    agent_performance: list
    completed_tasks: list


class WeeklyReportResponse(BaseModel):
    """Weekly report response."""
    period: str
    week_start: str
    week_end: str
    generated_at: str
    summary: dict
    completed_tasks: list


@router.get("/daily")
async def get_daily_report(
    date_str: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get daily work report.

    Args:
        date_str: Date in YYYY-MM-DD format (default: yesterday)

    Returns:
        Daily report with tasks, budget, and agent performance
    """
    service = ReportService(db)

    if date_str:
        try:
            report_date = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        report_date = None  # Will default to yesterday

    report = service.generate_daily_report(report_date)
    return report


@router.get("/weekly")
async def get_weekly_report(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get weekly work report.

    Args:
        week_start: Start date of week in YYYY-MM-DD format (default: last Monday)

    Returns:
        Weekly report with summary and daily breakdown
    """
    service = ReportService(db)

    if week_start:
        try:
            week_start_date = date.fromisoformat(week_start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        week_start_date = None

    report = service.generate_weekly_report(week_start_date)
    return report


@router.get("/recent")
async def get_recent_reports(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get recent daily reports.

    Args:
        days: Number of days to include (default: 7, max: 30)

    Returns:
        List of daily reports
    """
    if days < 1 or days > 30:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 30")

    service = ReportService(db)
    reports = service.get_recent_reports(days)
    return {
        "count": len(reports),
        "reports": reports
    }
