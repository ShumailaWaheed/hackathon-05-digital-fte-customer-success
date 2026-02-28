"""Create a support ticket — must be called first per Constitution III."""
import uuid
from pydantic import BaseModel, Field
from agents import function_tool
from production.database import repositories

@function_tool
async def create_ticket(
    customer_id: str,
    issue: str,
    priority: str = "medium",
    channel: str = "webform",
    metadata: str = "{}"
) -> str:
    """Create a ticket for an inbound message. Returns ticket_id."""
    import json
    try:
        meta = json.loads(metadata) if isinstance(metadata, str) else metadata
        result = await repositories.create_ticket(
            customer_id=uuid.UUID(customer_id),
            issue=issue,
            channel=channel,
            priority=priority,
            metadata=meta,
        )
        ticket_id = str(result["id"])
        # Immediately move to in-progress
        await repositories.update_ticket_status(result["id"], "in-progress")
        return f"Ticket created: {ticket_id}"
    except Exception as e:
        return f"Failed to create ticket: {e}"
