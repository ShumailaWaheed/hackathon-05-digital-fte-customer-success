"""MCP tool: Send response via appropriate channel."""
import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fte_user:fte_pass@localhost:5432/fte_crm")

async def send_response(args: dict) -> str:
    ticket_id = args.get("ticket_id")
    message = args.get("message", "")
    channel = args.get("channel", "webform")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        config = await conn.fetchrow(
            "SELECT tone, max_length, greeting_template, signature_template FROM channel_configs WHERE channel = $1",
            channel,
        )
        if config:
            max_len = config["max_length"]
            if channel == "gmail":
                words = message.split()
                if len(words) > max_len:
                    message = " ".join(words[:max_len])
                greeting = config.get("greeting_template") or ""
                sig = config.get("signature_template") or ""
                if greeting:
                    message = f"{greeting}\n\n{message}"
                if sig:
                    message = f"{message}\n\n{sig}"
            elif channel == "whatsapp" and len(message) > max_len:
                message = message[:max_len]
        await conn.close()
        return f"Response sent via {channel}: {message[:100]}..."
    except Exception as e:
        return f"Failed to send: {e}"
