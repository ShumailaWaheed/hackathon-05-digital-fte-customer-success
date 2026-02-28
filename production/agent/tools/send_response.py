"""Send response to customer — auto-detects channel and applies formatting."""
import uuid
from agents import function_tool
from production.database import repositories

@function_tool
async def send_response(ticket_id: str, message: str, channel: str) -> str:
    """Send a response via the appropriate channel. Auto-formats for tone/length."""
    try:
        tid = uuid.UUID(ticket_id)
        config = await repositories.get_channel_config(channel)

        if not config:
            return f"No channel config found for {channel}"

        # Apply channel length limits
        max_length = config["max_length"]
        formatted = message

        if channel == "gmail":
            # Word limit for email
            words = formatted.split()
            if len(words) > max_length:
                formatted = " ".join(words[:max_length])
            # Add greeting/signature
            greeting = config.get("greeting_template", "")
            signature = config.get("signature_template", "")
            if greeting:
                formatted = f"{greeting}\n\n{formatted}"
            if signature:
                formatted = f"{formatted}\n\n{signature}"

        elif channel == "whatsapp":
            # Character limit — actual splitting done by channel handler
            if len(formatted) > max_length:
                formatted = formatted[:max_length]

        # Publish to outbound (handled by outbound_sender worker)
        from production.workers.kafka_config import get_producer, publish_message
        producer = get_producer()
        publish_message(producer, "outbound-responses", {
            "ticket_id": ticket_id,
            "channel": channel,
            "message": formatted,
        })

        # Update ticket status to resolved if sentiment is okay
        ticket = await repositories.get_ticket(tid)
        if ticket:
            sentiment = await repositories.get_latest_sentiment(ticket["customer_id"])
            if sentiment is not None and sentiment >= 0.3:
                await repositories.update_ticket_status(tid, "resolved")

        return f"Response sent via {channel}"
    except Exception as e:
        return f"Failed to send response: {e}"
