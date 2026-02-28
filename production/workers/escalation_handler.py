"""Kafka consumer for escalations topic.

T055: Logs escalation with full context (ticket_id, reason, conversation
history, sentiment scores, trigger), stores in agent_metrics per FR-021.
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


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down escalation handler...", signum)
    _shutdown = True


async def handle_escalation(msg: dict) -> None:
    """Process a single escalation event.

    Expected msg:
        ticket_id, reason, customer_id, channel, sentiment
    """
    ticket_id = msg.get("ticket_id", "unknown")
    reason = msg.get("reason", "unknown")
    customer_id = msg.get("customer_id")
    channel = msg.get("channel", "unknown")
    sentiment = msg.get("sentiment")

    logger.info(
        "ESCALATION: ticket=%s channel=%s reason=%s sentiment=%s",
        ticket_id, channel, reason, sentiment,
    )

    # Gather full context for human handoff
    context = {
        "ticket_id": ticket_id,
        "reason": reason,
        "channel": channel,
        "sentiment": sentiment,
    }

    # Get conversation history if customer_id available
    if customer_id:
        try:
            cid = uuid.UUID(customer_id)
            history = await repositories.get_customer_messages(cid, limit=20)
            context["conversation_history"] = [
                {
                    "direction": m["direction"],
                    "channel": m["channel"],
                    "content": m["content"][:200],
                    "sentiment": m.get("sentiment_score"),
                    "timestamp": str(m["created_at"]),
                }
                for m in history
            ]
        except Exception as e:
            logger.warning("Failed to fetch history for escalation: %s", e)

    # Get ticket details
    try:
        tid = uuid.UUID(ticket_id)
        ticket = await repositories.get_ticket(tid)
        if ticket:
            context["ticket_status"] = ticket["status"]
            context["ticket_priority"] = ticket["priority"]
            context["ticket_issue"] = ticket.get("issue", "")[:300]
    except Exception as e:
        logger.warning("Failed to fetch ticket for escalation: %s", e)

    # Store escalation metric
    try:
        await repositories.create_agent_metric(
            ticket_id=uuid.UUID(ticket_id),
            channel=channel,
            escalated=True,
            escalation_reason=reason,
            sentiment_score=sentiment,
        )
    except Exception as e:
        logger.warning("Failed to store escalation metric: %s", e)

    logger.info("Escalation processed: ticket=%s context_keys=%s", ticket_id, list(context.keys()))


async def run_escalation_handler() -> None:
    """Main consumer loop for escalations topic."""
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    consumer = get_consumer(
        group_id="escalation-handler",
        topics=["escalations"],
    )

    logger.info("Escalation handler started — consuming from escalations topic")

    try:
        while not _shutdown:
            msg = consume_messages(consumer, timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            await handle_escalation(msg)
    finally:
        consumer.close()
        logger.info("Escalation handler shut down")


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_escalation_handler())


if __name__ == "__main__":
    main()
