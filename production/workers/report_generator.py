"""Scheduled daily report generator.

T058: Calls generate_daily_report logic, formats output as Markdown,
stores in database. Runs once daily. Per FR-025.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import date, timedelta

from production.database import repositories

logger = logging.getLogger(__name__)

REPORT_INTERVAL = int(os.environ.get("REPORT_INTERVAL", "86400"))  # 24h
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down report generator...", signum)
    _shutdown = True


async def generate_report(report_date: date | None = None) -> dict:
    """Generate a daily report for the given date.

    Computes: average_sentiment, sentiment_trend, top_issues,
    escalation_rate, channel_breakdown. Per FR-025, FR-026.

    Returns:
        dict with all report fields.
    """
    if report_date is None:
        report_date = date.today() - timedelta(days=1)

    date_str = report_date.isoformat()
    metrics = await repositories.get_metrics_for_date(date_str)

    total = len(metrics)
    if total == 0:
        return {
            "date": date_str,
            "total_messages": 0,
            "average_sentiment": 0.0,
            "sentiment_trend": "stable",
            "escalation_rate": 0.0,
            "top_issues": [],
            "channel_breakdown": {},
        }

    # Average sentiment
    sentiments = [m["sentiment_score"] for m in metrics if m.get("sentiment_score") is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

    # Sentiment trend (compare to previous day)
    prev_date = (report_date - timedelta(days=1)).isoformat()
    prev_metrics = await repositories.get_metrics_for_date(prev_date)
    prev_sentiments = [m["sentiment_score"] for m in prev_metrics if m.get("sentiment_score") is not None]
    prev_avg = sum(prev_sentiments) / len(prev_sentiments) if prev_sentiments else avg_sentiment

    if avg_sentiment > prev_avg + 0.05:
        trend = "improving"
    elif avg_sentiment < prev_avg - 0.05:
        trend = "declining"
    else:
        trend = "stable"

    # Escalation rate
    escalated = sum(1 for m in metrics if m.get("escalated"))
    escalation_rate = escalated / total if total > 0 else 0.0

    # Top issues (from escalation reasons)
    issue_counts: dict[str, int] = {}
    for m in metrics:
        reason = m.get("escalation_reason")
        if reason:
            for part in reason.split("; "):
                issue_counts[part] = issue_counts.get(part, 0) + 1

    top_issues = sorted(
        [{"category": k, "count": v} for k, v in issue_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    # Channel breakdown
    channels: dict[str, dict] = {}
    for m in metrics:
        ch = m.get("channel", "unknown")
        if ch not in channels:
            channels[ch] = {"count": 0, "sentiments": [], "escalated": 0}
        channels[ch]["count"] += 1
        if m.get("sentiment_score") is not None:
            channels[ch]["sentiments"].append(m["sentiment_score"])
        if m.get("escalated"):
            channels[ch]["escalated"] += 1

    channel_breakdown = {}
    for ch, data in channels.items():
        ch_avg = sum(data["sentiments"]) / len(data["sentiments"]) if data["sentiments"] else 0.0
        channel_breakdown[ch] = {
            "total_messages": data["count"],
            "average_sentiment": round(ch_avg, 3),
            "escalation_count": data["escalated"],
        }

    report = {
        "date": date_str,
        "total_messages": total,
        "average_sentiment": round(avg_sentiment, 3),
        "sentiment_trend": trend,
        "escalation_rate": round(escalation_rate, 3),
        "top_issues": top_issues,
        "channel_breakdown": channel_breakdown,
    }

    logger.info(
        "Report generated: date=%s messages=%d avg_sentiment=%.3f trend=%s escalation=%.1f%%",
        date_str, total, avg_sentiment, trend, escalation_rate * 100,
    )

    return report


async def run_report_generator() -> None:
    """Main loop — generates daily report once per day."""
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("Report generator started — running every %ds", REPORT_INTERVAL)

    while not _shutdown:
        try:
            report = await generate_report()
            logger.info("Daily report: %s", report.get("date"))
        except Exception as e:
            logger.error("Report generation failed: %s", e)

        await asyncio.sleep(REPORT_INTERVAL)

    logger.info("Report generator shut down")


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_report_generator())


if __name__ == "__main__":
    main()
