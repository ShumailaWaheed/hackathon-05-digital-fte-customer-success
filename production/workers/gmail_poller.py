"""Gmail polling worker.

T042: Polls Gmail inbox every 15s, normalizes new emails to unified format,
resolves customer identity, and publishes to inbound-messages Kafka topic.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time

from production.channels.gmail_handler import GmailClient
from production.database import repositories
from production.api.services.identity_resolver import resolve_customer
from production.workers.kafka_config import get_producer, publish_message

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.environ.get("GMAIL_POLL_INTERVAL", "15"))  # seconds
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down Gmail poller...", signum)
    _shutdown = True


async def process_gmail_messages(client: GmailClient, after_timestamp: int) -> int:
    """Poll and process new Gmail messages.

    Returns the number of messages processed.
    """
    emails = await client.poll_inbox(after_timestamp=after_timestamp)
    if not emails:
        return 0

    producer = get_producer()
    count = 0

    for mail in emails:
        try:
            customer = await resolve_customer(
                identifier_type="email",
                identifier_value=mail["from_email"],
                name=mail["from_name"],
                source="gmail",
            )
            customer_id = str(customer["id"])

            # Create ticket immediately
            ticket = await repositories.create_ticket(
                customer_id=customer["id"],
                issue=mail["body"][:500],
                channel="gmail",
                priority="medium",
                metadata={
                    "email": mail["from_email"],
                    "subject": mail["subject"],
                    "gmail_message_id": mail["message_id"],
                },
            )
            ticket_id = str(ticket["id"])

            # Publish to Kafka
            unified_message = {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "channel": "gmail",
                "message": mail["body"],
                "metadata": {
                    "email": mail["from_email"],
                    "name": mail["from_name"],
                    "subject": mail["subject"],
                    "gmail_message_id": mail["message_id"],
                },
            }
            publish_message(producer, "inbound-messages", unified_message, key=customer_id)
            count += 1
            logger.info(
                "Gmail message queued: ticket=%s from=%s subject=%s",
                ticket_id, mail["from_email"], mail["subject"],
            )
        except Exception as e:
            logger.error("Failed to process Gmail message from %s: %s", mail.get("from_email"), e)

    return count


async def run_gmail_poller() -> None:
    """Main polling loop — checks Gmail every 15s."""
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    client = GmailClient()
    last_poll = int(time.time()) - POLL_INTERVAL  # Start from now

    logger.info("Gmail poller started — polling every %ds", POLL_INTERVAL)

    while not _shutdown:
        try:
            count = await process_gmail_messages(client, after_timestamp=last_poll)
            if count:
                logger.info("Processed %d Gmail messages", count)
            last_poll = int(time.time())
        except Exception as e:
            logger.error("Gmail poll cycle failed: %s", e)

        await asyncio.sleep(POLL_INTERVAL)

    logger.info("Gmail poller shut down")


def main():
    """Entry point for the Gmail poller worker."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_gmail_poller())


if __name__ == "__main__":
    main()
