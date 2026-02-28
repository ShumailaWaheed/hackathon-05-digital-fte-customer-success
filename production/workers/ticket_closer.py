"""Scheduled ticket closure worker.

T057: Runs hourly, finds resolved tickets older than 24h, checks most
recent sentiment via G9, closes if positive or reverts to in-progress
if negative. Per spec Ticket Lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import uuid

from production.database import repositories

logger = logging.getLogger(__name__)

CHECK_INTERVAL = int(os.environ.get("TICKET_CLOSER_INTERVAL", "3600"))  # 1 hour
RESOLVED_HOURS = 24  # Close tickets resolved for >24h
SENTIMENT_THRESHOLD = 0.3  # G9: don't close if sentiment < 0.3

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down ticket closer...", signum)
    _shutdown = True


async def close_eligible_tickets() -> dict:
    """Find resolved tickets older than 24h and process them.

    Returns:
        dict with counts: closed, reverted, errors.
    """
    stats = {"closed": 0, "reverted": 0, "errors": 0}

    try:
        tickets = await repositories.get_resolved_tickets_older_than(hours=RESOLVED_HOURS)
    except Exception as e:
        logger.error("Failed to fetch resolved tickets: %s", e)
        return stats

    for ticket in tickets:
        ticket_id = ticket["id"]
        customer_id = ticket.get("customer_id")

        try:
            # G9 check: get latest sentiment for this customer
            sentiment = None
            if customer_id:
                sentiment = await repositories.get_latest_sentiment(customer_id)

            if sentiment is not None and sentiment < SENTIMENT_THRESHOLD:
                # Negative sentiment — revert to in-progress for review
                await repositories.update_ticket_status(ticket_id, "in-progress")
                stats["reverted"] += 1
                logger.info(
                    "Ticket reverted (G9 negative sentiment %.2f): ticket=%s",
                    sentiment, ticket_id,
                )
            else:
                # Positive or neutral — close
                await repositories.update_ticket_status(ticket_id, "closed")
                stats["closed"] += 1
                logger.info("Ticket closed: ticket=%s sentiment=%s", ticket_id, sentiment)

        except Exception as e:
            stats["errors"] += 1
            logger.error("Failed to process ticket %s: %s", ticket_id, e)

    return stats


async def run_ticket_closer() -> None:
    """Main loop — checks for closable tickets every hour."""
    global _shutdown

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("Ticket closer started — checking every %ds", CHECK_INTERVAL)

    while not _shutdown:
        try:
            stats = await close_eligible_tickets()
            total = stats["closed"] + stats["reverted"]
            if total > 0:
                logger.info(
                    "Ticket closer cycle: closed=%d reverted=%d errors=%d",
                    stats["closed"], stats["reverted"], stats["errors"],
                )
        except Exception as e:
            logger.error("Ticket closer cycle failed: %s", e)

        await asyncio.sleep(CHECK_INTERVAL)

    logger.info("Ticket closer shut down")


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(run_ticket_closer())


if __name__ == "__main__":
    main()
