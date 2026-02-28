"""Kafka consumer for inbound-messages topic.

T032: Consumes messages from Kafka, executes the strict workflow via
agent.process_message(), and logs every step with ticket_id.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import os

from production.workers.kafka_config import get_consumer, consume_messages
from production.agent.agent import process_message
from production.database import repositories

logger = logging.getLogger(__name__)

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down message processor...", signum)
    _shutdown = True


async def process_single_message(msg: dict) -> None:
    """Process a single inbound message through the agent workflow.

    Expected msg format (unified):
        ticket_id: str
        customer_id: str
        channel: str (webform|gmail|whatsapp)
        message: str
        metadata: dict (optional)
    """
    ticket_id = msg.get("ticket_id")
    customer_id = msg.get("customer_id")
    channel = msg.get("channel")
    message_content = msg.get("message")
    metadata = msg.get("metadata")

    if not all([ticket_id, customer_id, channel, message_content]):
        logger.error("Invalid inbound message — missing required fields: %s", msg)
        return

    logger.info(
        "Processing message: ticket=%s customer=%s channel=%s",
        ticket_id, customer_id, channel,
    )

    try:
        result = await process_message(
            customer_id=customer_id,
            message_content=message_content,
            channel=channel,
            metadata=metadata,
        )

        action = result.get("action", "unknown")
        logger.info(
            "Message processed: ticket=%s action=%s steps=%s",
            ticket_id, action, result.get("workflow_steps", []),
        )
    except Exception as e:
        logger.error(
            "Failed to process message: ticket=%s error=%s",
            ticket_id, e,
        )
        # Mark ticket as failed so status endpoint reflects it
        try:
            import uuid
            await repositories.update_ticket_status(
                uuid.UUID(ticket_id), "delivery-failed"
            )
        except Exception:
            pass


async def run_consumer_loop() -> None:
    """Main consumer loop — polls Kafka for inbound messages.

    Runs indefinitely until SIGINT/SIGTERM.
    """
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    consumer = get_consumer(
        group_id="message-processor",
        topics=["inbound-messages"],
    )

    logger.info("Message processor started — consuming from inbound-messages")

    try:
        while not _shutdown:
            msg = consume_messages(consumer, timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            await process_single_message(msg)
    finally:
        consumer.close()
        logger.info("Message processor shut down")


def main():
    """Entry point for the message processor worker."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_consumer_loop())


if __name__ == "__main__":
    main()
