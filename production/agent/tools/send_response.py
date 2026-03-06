"""Send response to customer — auto-detects channel and applies formatting."""
import logging
import uuid
from agents import function_tool
from production.database import repositories

logger = logging.getLogger(__name__)

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

        # For gmail/whatsapp: require admin approval before sending
        # For webform: auto-resolve (response shown via polling)
        if channel in ("gmail", "whatsapp"):
            # Set ticket to pending_approval — admin must approve before delivery
            await repositories.update_ticket_status(tid, "pending_approval")
            logger.info("Response queued for approval: ticket=%s channel=%s", ticket_id, channel)
            return f"Response queued for admin approval via {channel}"
        else:
            # Webform: auto-resolve (no external delivery needed)
            ticket = await repositories.get_ticket(tid)
            if ticket:
                sentiment = await repositories.get_latest_sentiment(ticket["customer_id"])
                if sentiment is not None and sentiment >= 0.3:
                    await repositories.update_ticket_status(tid, "resolved")

            return f"Response sent via {channel}"
    except Exception as e:
        return f"Failed to send response: {e}"
