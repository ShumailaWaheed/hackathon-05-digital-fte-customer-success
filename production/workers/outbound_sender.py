"""Kafka consumer for outbound-responses topic.

T033: Consumes formatted responses, dispatches to correct channel handler,
implements retry with exponential backoff (1s→4s→16s, max 3 retries).
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import uuid

from production.workers.kafka_config import get_consumer, consume_messages
from production.database import repositories

logger = logging.getLogger(__name__)

_shutdown = False

MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds — 1s, 4s, 16s


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down outbound sender...", signum)
    _shutdown = True


async def dispatch_response(channel: str, ticket_id: str, message: str, metadata: dict | None = None) -> None:
    """Dispatch an outbound response to the correct channel handler.

    Raises on failure so retry logic can catch it.
    """
    if channel == "webform":
        # Webform responses are stored in DB — frontend polls for them.
        # The agent already stored the outbound message. Just log.
        logger.info("Webform response ready for polling: ticket=%s", ticket_id)

    elif channel == "gmail":
        # Phase 4 — Gmail dispatch
        try:
            from production.channels.gmail_handler import GmailClient
            client = GmailClient()
            recipient = metadata.get("email") if metadata else None
            if recipient:
                await client.send_reply(recipient, message, ticket_id)
                logger.info("Gmail response sent: ticket=%s", ticket_id)
            else:
                logger.warning("No email for Gmail dispatch: ticket=%s", ticket_id)
        except ImportError:
            logger.debug("Gmail handler not available yet — ticket=%s", ticket_id)

    elif channel == "whatsapp":
        # Phase 5 — WhatsApp dispatch
        try:
            from production.channels.whatsapp_handler import TwilioWhatsAppClient
            client = TwilioWhatsAppClient()
            phone = metadata.get("phone") if metadata else None
            if phone:
                await client.send_reply(phone, message)
                logger.info("WhatsApp response sent: ticket=%s", ticket_id)
            else:
                logger.warning("No phone for WhatsApp dispatch: ticket=%s", ticket_id)
        except ImportError:
            logger.debug("WhatsApp handler not available yet — ticket=%s", ticket_id)

    else:
        logger.warning("Unknown channel '%s' for ticket=%s", channel, ticket_id)


async def process_outbound_message(msg: dict) -> None:
    """Process a single outbound response with retry logic.

    Exponential backoff: 1s → 4s → 16s (BACKOFF_BASE * 4^attempt).
    """
    ticket_id = msg.get("ticket_id", "unknown")
    channel = msg.get("channel", "unknown")
    message = msg.get("message", "")
    metadata = msg.get("metadata")

    for attempt in range(MAX_RETRIES + 1):
        try:
            await dispatch_response(channel, ticket_id, message, metadata)
            return
        except Exception as e:
            if attempt < MAX_RETRIES:
                delay = BACKOFF_BASE * (4 ** attempt)  # 1, 4, 16
                logger.warning(
                    "Dispatch failed (attempt %d/%d), retrying in %ds: ticket=%s error=%s",
                    attempt + 1, MAX_RETRIES, delay, ticket_id, e,
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Dispatch failed after %d retries: ticket=%s error=%s",
                    MAX_RETRIES, ticket_id, e,
                )
                # Mark ticket as delivery-failed
                try:
                    await repositories.update_ticket_status(
                        uuid.UUID(ticket_id), "delivery-failed"
                    )
                except Exception:
                    pass


async def run_outbound_loop() -> None:
    """Main consumer loop for outbound responses."""
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    consumer = get_consumer(
        group_id="outbound-sender",
        topics=["outbound-responses"],
    )

    logger.info("Outbound sender started — consuming from outbound-responses")

    try:
        while not _shutdown:
            msg = consume_messages(consumer, timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            await process_outbound_message(msg)
    finally:
        consumer.close()
        logger.info("Outbound sender shut down")


def main():
    """Entry point for the outbound sender worker."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_outbound_loop())


if __name__ == "__main__":
    main()
