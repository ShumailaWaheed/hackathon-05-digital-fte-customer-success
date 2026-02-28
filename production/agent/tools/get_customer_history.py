"""Retrieve full cross-channel conversation history for a customer."""
import uuid
from agents import function_tool
from production.database import repositories

@function_tool
async def get_customer_history(customer_id: str) -> str:
    """Get cross-channel conversation history for a customer. Returns formatted history."""
    try:
        messages = await repositories.get_customer_messages(
            uuid.UUID(customer_id), limit=50
        )
        if not messages:
            return "No previous conversation history found."

        formatted = []
        for m in messages:
            direction = "Customer" if m["direction"] == "inbound" else "Agent"
            channel = m["channel"]
            sentiment = f" [sentiment: {m['sentiment_score']:.2f}]" if m.get("sentiment_score") else ""
            formatted.append(f"[{m['created_at']}] [{channel}] {direction}: {m['content']}{sentiment}")

        return "\n".join(formatted)
    except Exception as e:
        return f"Failed to retrieve history: {e}"
