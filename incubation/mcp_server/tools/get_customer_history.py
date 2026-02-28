"""MCP tool: Get cross-channel customer conversation history."""
import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fte_user:fte_pass@localhost:5432/fte_crm")

async def get_customer_history(args: dict) -> str:
    customer_id = args.get("customer_id")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch(
            """SELECT m.direction, m.channel, m.content, m.sentiment_score, m.created_at
               FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.customer_id = $1::uuid
               ORDER BY m.created_at DESC LIMIT 50""",
            customer_id,
        )
        await conn.close()
        if not rows:
            return "No previous conversation history found."
        lines = []
        for r in rows:
            who = "Customer" if r["direction"] == "inbound" else "Agent"
            sent = f" [sentiment: {r['sentiment_score']:.2f}]" if r.get("sentiment_score") else ""
            lines.append(f"[{r['created_at']}] [{r['channel']}] {who}: {r['content']}{sent}")
        return "\n".join(lines)
    except Exception as e:
        return f"Failed to get history: {e}"
