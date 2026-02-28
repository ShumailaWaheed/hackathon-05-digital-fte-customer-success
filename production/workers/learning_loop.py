"""Knowledge base learning loop.

T061: Triggered on ticket resolution. If sentiment >= 0.5, extracts Q/A,
generates embedding locally (sentence-transformers), inserts into knowledge_base
with source='learned'. Per FR-023.
"""

from __future__ import annotations

import logging
import uuid

from production.agent.llm_client import generate_embedding_async
from production.database import repositories

logger = logging.getLogger(__name__)

LEARNING_SENTIMENT_THRESHOLD = 0.5  # Only learn from positive interactions


async def maybe_learn_from_ticket(ticket_id: uuid.UUID) -> bool:
    """Check if a resolved ticket qualifies for KB learning.

    Criteria:
    - Ticket is resolved
    - Latest sentiment >= 0.5
    - Has both inbound (question) and outbound (answer) messages

    Returns:
        True if a new KB entry was created.
    """
    ticket = await repositories.get_ticket(ticket_id)
    if not ticket or ticket["status"] != "resolved":
        return False

    customer_id = ticket.get("customer_id")
    if not customer_id:
        return False

    # Check sentiment
    sentiment = await repositories.get_latest_sentiment(customer_id)
    if sentiment is None or sentiment < LEARNING_SENTIMENT_THRESHOLD:
        logger.debug(
            "Skipping learning for ticket %s: sentiment=%.2f (threshold=%.2f)",
            ticket_id, sentiment or 0, LEARNING_SENTIMENT_THRESHOLD,
        )
        return False

    # Get Q (original issue) and A (agent response)
    question = ticket.get("issue", "")
    if not question:
        return False

    # Get the agent's response for this ticket
    answer = await repositories.get_ticket_response(ticket_id)
    if not answer:
        return False

    # Generate embedding locally (free, no API key needed)
    try:
        embedding = await generate_embedding_async(question)
    except Exception as e:
        logger.warning("Failed to generate embedding for learning: %s", e)
        return False

    # Insert into knowledge base
    try:
        entry = await repositories.add_knowledge_entry(
            title=question[:200],
            content=f"Q: {question}\n\nA: {answer}",
            embedding=embedding,
            category="learned",
            source="learned",
            source_ticket_id=ticket_id,
        )
        logger.info(
            "KB entry learned from ticket %s: entry_id=%s sentiment=%.2f",
            ticket_id, entry.get("id"), sentiment,
        )
        return True
    except Exception as e:
        logger.error("Failed to create KB entry from ticket %s: %s", ticket_id, e)
        return False
