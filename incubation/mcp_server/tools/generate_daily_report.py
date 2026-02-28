"""MCP tool: Generate daily sentiment report."""
import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fte_user:fte_pass@localhost:5432/fte_crm")

async def generate_daily_report(args: dict) -> str:
    date = args.get("date", "")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch(
            "SELECT * FROM agent_metrics WHERE created_at::date = $1::date ORDER BY created_at",
            date,
        )
        await conn.close()
        if not rows:
            return f"No activity for {date}."
        total = len(rows)
        escalated = sum(1 for r in rows if r["escalated"])
        sentiments = [r["sentiment_score"] for r in rows if r.get("sentiment_score") is not None]
        avg = sum(sentiments) / len(sentiments) if sentiments else 0
        channels = {}
        for r in rows:
            ch = r["channel"]
            channels.setdefault(ch, {"count": 0, "escalated": 0})
            channels[ch]["count"] += 1
            if r["escalated"]:
                channels[ch]["escalated"] += 1
        lines = [
            f"# Daily Report — {date}",
            f"Total: {total} | Avg Sentiment: {avg:.2f} | Escalation Rate: {100*escalated/total:.1f}%",
        ]
        for ch, d in channels.items():
            lines.append(f"- {ch}: {d['count']} msgs, {d['escalated']} escalated")
        return "\n".join(lines)
    except Exception as e:
        return f"Report error: {e}"
