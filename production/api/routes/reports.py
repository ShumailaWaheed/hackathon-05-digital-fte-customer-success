"""Daily report API endpoint.

T059: GET /api/reports/daily — accepts optional date query param,
returns report data as JSON per contracts/api.yaml.
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Query

from production.workers.report_generator import generate_report

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/reports/daily")
async def get_daily_report(
    report_date: date | None = Query(None, alias="date", description="Date for report (YYYY-MM-DD, defaults to yesterday)"),
):
    """Get daily sentiment and performance report.

    Per contracts/api.yaml — returns average_sentiment, sentiment_trend,
    escalation_rate, top_issues, channel_breakdown.
    """
    report = await generate_report(report_date=report_date)
    return report
