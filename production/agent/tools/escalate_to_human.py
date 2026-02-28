"""Escalate ticket to human agent with full context."""
import uuid
import json
from agents import function_tool
from production.database import repositories
from production.workers.kafka_config import get_producer, publish_message

@function_tool
async def escalate_to_human(ticket_id: str, reason: str) -> str:
    """Escalate a ticket to a human agent. Includes reason and full context."""
    try:
        tid = uuid.UUID(ticket_id)
        # Update ticket status
        await repositories.update_ticket_status(tid, "escalated", escalation_reason=reason)

        # Get ticket details for context
        ticket = await repositories.get_ticket(tid)
        if ticket:
            customer_id = ticket["customer_id"]
            history = await repositories.get_customer_messages(customer_id, limit=20)

            # Publish to escalations topic
            producer = get_producer()
            publish_message(producer, "escalations", {
                "ticket_id": ticket_id,
                "reason": reason,
                "customer_id": str(customer_id),
                "channel": ticket["channel"],
                "history": [{"content": m["content"], "channel": m["channel"], "direction": m["direction"]} for m in history],
            })

        return f"Ticket {ticket_id} escalated to human agent. Reason: {reason}"
    except Exception as e:
        return f"Escalation failed: {e}"
