"""MCP tool: Escalate ticket to human agent."""
import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fte_user:fte_pass@localhost:5432/fte_crm")

async def escalate_to_human(args: dict) -> str:
    ticket_id = args.get("ticket_id")
    reason = args.get("reason", "No reason provided")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute(
            """UPDATE tickets SET status = 'escalated', escalation_reason = $2, updated_at = now()
               WHERE id = $1::uuid""",
            ticket_id, reason,
        )
        await conn.close()
        return f"Ticket {ticket_id} escalated. Reason: {reason}"
    except Exception as e:
        return f"Escalation failed: {e}"
