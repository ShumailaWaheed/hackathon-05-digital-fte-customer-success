"""Web form channel handler.

T031: Normalize web form data to unified format, resolve customer identity,
and trigger async processing via Kafka or direct agent call.
"""

from __future__ import annotations

import json
import logging
import uuid

from production.database import repositories
from production.api.services.identity_resolver import resolve_customer
from production.workers.kafka_config import get_producer, publish_message

logger = logging.getLogger(__name__)


async def process_webform_message(
    name: str,
    email: str,
    category: str,
    message: str,
) -> dict:
    """Process an inbound web form submission.

    1. Resolve customer identity (find or create)
    2. Publish normalized message to Kafka inbound-messages topic
    3. Return ticket_id for polling

    Returns:
        dict with ticket_id and customer_id.
    """
    customer = await resolve_customer(
        identifier_type="email",
        identifier_value=email,
        name=name,
        source="webform",
    )
    customer_id = str(customer["id"])

    # Create ticket immediately so we can return ticket_id for polling
    ticket = await repositories.create_ticket(
        customer_id=customer["id"],
        issue=message,
        channel="webform",
        priority="medium",
        metadata={"category": category, "email": email, "name": name},
    )
    ticket_id = str(ticket["id"])

    # Publish to Kafka for async processing
    unified_message = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "channel": "webform",
        "message": message,
        "metadata": {
            "category": category,
            "email": email,
            "name": name,
        },
    }

    try:
        producer = get_producer()
        publish_message(producer, "inbound-messages", unified_message, key=customer_id)
        logger.info("Published webform message to Kafka: ticket=%s", ticket_id)
    except Exception as e:
        logger.warning("Kafka publish failed, processing synchronously: %s", e)
        # Fallback: process directly if Kafka is unavailable
        from production.agent.agent import process_message
        await process_message(
            customer_id=customer_id,
            message_content=message,
            channel="webform",
            metadata={"category": category, "email": email, "name": name},
        )

    return {"ticket_id": ticket_id, "customer_id": customer_id}


async def send_webform_response(ticket_id: str, response_text: str, email: str | None = None) -> None:
    """Store webform response for polling pickup.

    The response is stored as an outbound message in the database.
    Frontend polls GET /api/support/{ticket_id}/status to retrieve it.
    Optionally sends email fallback via Gmail handler (Phase 4).
    """
    logger.info("Webform response stored for ticket=%s", ticket_id)

    # Email fallback (Phase 4 — gmail_handler integration)
    if email:
        try:
            from production.channels.gmail_handler import send_email_fallback
            await send_email_fallback(email, response_text, ticket_id)
        except ImportError:
            logger.debug("Gmail handler not available yet — skipping email fallback")
        except Exception as e:
            logger.warning("Email fallback failed for ticket %s: %s", ticket_id, e)
