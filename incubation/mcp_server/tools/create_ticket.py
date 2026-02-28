"""MCP tool: Create a support ticket."""
import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fte_user:fte_pass@localhost:5432/fte_crm")

async def create_ticket(args: dict) -> str:
    customer_id = args.get("customer_id")
    issue = args.get("issue", "")
    priority = args.get("priority", "medium")
    channel = args.get("channel", "webform")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        row = await conn.fetchrow(
            """INSERT INTO tickets (customer_id, channel, issue, priority)
               VALUES ($1::uuid, $2, $3, $4)
               RETURNING id""",
            customer_id, channel, issue, priority,
        )
        ticket_id = str(row["id"])
        await conn.execute(
            "UPDATE tickets SET status = 'in-progress', updated_at = now() WHERE id = $1::uuid",
            ticket_id,
        )
        await conn.close()
        return f"Ticket created: {ticket_id}"
    except Exception as e:
        return f"Failed to create ticket: {e}"
