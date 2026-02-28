"""Generate daily sentiment and metrics report.

T060: Queries agent_metrics grouped by date, computes average_sentiment,
sentiment_trend, top_5_categories, escalation_rate, channel_breakdown.
Per FR-025, FR-026.
"""

from datetime import date as date_type, timedelta

from agents import function_tool
from production.database import repositories


@function_tool
async def generate_daily_report(date: str) -> str:
    """Generate daily sentiment report for the given date (YYYY-MM-DD).

    Returns Markdown report with summary, trend, top issues, and channel breakdown.
    """
    try:
        metrics = await repositories.get_metrics_for_date(date)

        if not metrics:
            return f"No activity recorded for {date}."

        total = len(metrics)
        escalated = sum(1 for m in metrics if m.get("escalated"))
        sentiments = [m["sentiment_score"] for m in metrics if m.get("sentiment_score") is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        # Sentiment trend (compare to previous day)
        report_date = date_type.fromisoformat(date)
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

        # Top issues from escalation reasons
        issue_counts: dict[str, int] = {}
        for m in metrics:
            reason = m.get("escalation_reason")
            if reason:
                for part in reason.split("; "):
                    issue_counts[part] = issue_counts.get(part, 0) + 1

        top_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]

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

        # Build report
        esc_rate = f"{100 * escalated / total:.1f}%" if total else "N/A"
        report_lines = [
            f"# Daily Report — {date}",
            "",
            "## Summary",
            f"- Total interactions: {total}",
            f"- Average sentiment: {avg_sentiment:.2f}",
            f"- Sentiment trend: {trend}",
            f"- Escalation rate: {escalated}/{total} ({esc_rate})",
            "",
        ]

        if top_issues:
            report_lines.append("## Top Issues")
            for issue, count in top_issues:
                report_lines.append(f"- {issue}: {count}")
            report_lines.append("")

        report_lines.append("## Channel Breakdown")
        for ch, data in channels.items():
            ch_avg = sum(data["sentiments"]) / len(data["sentiments"]) if data["sentiments"] else 0
            report_lines.append(
                f"- **{ch}**: {data['count']} messages, "
                f"avg sentiment {ch_avg:.2f}, {data['escalated']} escalated"
            )

        return "\n".join(report_lines)
    except Exception as e:
        return f"Report generation failed: {e}"
