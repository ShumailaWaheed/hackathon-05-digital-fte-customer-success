"""Async CRUD operations for all CRM entities.

Uses asyncpg directly for performance. All functions accept
an asyncpg connection or pool.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import asyncpg

from .connection import get_connection


# --- Customer ---

async def create_customer(name: str, metadata: dict | None = None) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO customers (name, metadata)
               VALUES ($1, $2::jsonb)
               RETURNING id, name, created_at, updated_at, metadata""",
            name,
            __json(metadata),
        )
        return dict(row)


async def find_customer_by_identifier(
    identifier_type: str, identifier_value: str
) -> dict | None:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """SELECT c.id, c.name, c.created_at, c.updated_at, c.metadata
               FROM customers c
               JOIN customer_identifiers ci ON ci.customer_id = c.id
               WHERE ci.identifier_type = $1
                 AND ci.identifier_value = $2""",
            identifier_type,
            identifier_value,
        )
        return dict(row) if row else None


async def link_identifier(
    customer_id: uuid.UUID, identifier_type: str, identifier_value: str
) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO customer_identifiers (customer_id, identifier_type, identifier_value)
               VALUES ($1, $2, $3)
               ON CONFLICT (identifier_type, identifier_value) DO NOTHING
               RETURNING id, customer_id, identifier_type, identifier_value, created_at""",
            customer_id,
            identifier_type,
            identifier_value,
        )
        return dict(row) if row else {}


# --- Conversation ---

async def create_conversation(
    customer_id: uuid.UUID, subject: str | None = None
) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO conversations (customer_id, subject)
               VALUES ($1, $2)
               RETURNING id, customer_id, subject, started_at, last_activity_at, status""",
            customer_id,
            subject,
        )
        return dict(row)


async def get_active_conversation(customer_id: uuid.UUID) -> dict | None:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """SELECT id, customer_id, subject, started_at, last_activity_at, status
               FROM conversations
               WHERE customer_id = $1 AND status = 'active'
               ORDER BY last_activity_at DESC LIMIT 1""",
            customer_id,
        )
        return dict(row) if row else None


async def update_conversation_activity(conversation_id: uuid.UUID) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE conversations SET last_activity_at = now() WHERE id = $1",
            conversation_id,
        )


# --- Ticket ---

async def create_ticket(
    customer_id: uuid.UUID,
    issue: str,
    channel: str,
    priority: str = "medium",
    conversation_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO tickets (customer_id, conversation_id, channel, issue, priority, metadata)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb)
               RETURNING id, customer_id, conversation_id, channel, issue,
                         priority, status, created_at, updated_at""",
            customer_id,
            conversation_id,
            channel,
            issue,
            priority,
            __json(metadata),
        )
        return dict(row)


async def update_ticket_status(
    ticket_id: uuid.UUID,
    status: str,
    escalation_reason: str | None = None,
) -> dict:
    async with get_connection() as conn:
        now = datetime.utcnow()
        extra_fields = ""
        params: list[Any] = [status, now, ticket_id]

        if status == "resolved":
            extra_fields = ", resolved_at = $4"
            params.append(now)
        elif status == "closed":
            extra_fields = ", closed_at = $4"
            params.append(now)
        elif status == "escalated" and escalation_reason:
            extra_fields = ", escalation_reason = $4"
            params.append(escalation_reason)

        row = await conn.fetchrow(
            f"""UPDATE tickets
                SET status = $1, updated_at = $2{extra_fields}
                WHERE id = $3
                RETURNING id, status, updated_at, escalation_reason, resolved_at, closed_at""",
            *params,
        )
        return dict(row) if row else {}


async def get_ticket(ticket_id: uuid.UUID) -> dict | None:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tickets WHERE id = $1", ticket_id
        )
        return dict(row) if row else None


# Alias for API layer
get_ticket_by_id = get_ticket


async def get_ticket_response(ticket_id: uuid.UUID) -> str | None:
    """Get the latest outbound message for a ticket (used by status polling)."""
    async with get_connection() as conn:
        return await conn.fetchval(
            """SELECT m.content
               FROM messages m
               WHERE m.ticket_id = $1 AND m.direction = 'outbound'
               ORDER BY m.created_at DESC LIMIT 1""",
            ticket_id,
        )


async def get_open_tickets_for_customer(customer_id: uuid.UUID) -> list[dict]:
    async with get_connection() as conn:
        rows = await conn.fetch(
            """SELECT * FROM tickets
               WHERE customer_id = $1 AND status IN ('open', 'in-progress')
               ORDER BY created_at DESC""",
            customer_id,
        )
        return [dict(r) for r in rows]


async def get_resolved_tickets_older_than(hours: int = 24) -> list[dict]:
    from datetime import timedelta
    async with get_connection() as conn:
        rows = await conn.fetch(
            """SELECT * FROM tickets
               WHERE status = 'resolved'
                 AND resolved_at < now() - $1::interval""",
            timedelta(hours=hours),
        )
        return [dict(r) for r in rows]


# --- Message ---

async def create_message(
    conversation_id: uuid.UUID,
    direction: str,
    channel: str,
    content: str,
    ticket_id: uuid.UUID | None = None,
    sentiment_score: float | None = None,
    metadata: dict | None = None,
) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO messages
                   (conversation_id, ticket_id, direction, channel, content,
                    sentiment_score, metadata)
               VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
               RETURNING id, conversation_id, ticket_id, direction, channel,
                         content, sentiment_score, created_at""",
            conversation_id,
            ticket_id,
            direction,
            channel,
            content,
            sentiment_score,
            __json(metadata),
        )
        return dict(row)


async def get_customer_messages(
    customer_id: uuid.UUID, limit: int = 50
) -> list[dict]:
    """Get all messages across all channels for a customer, sorted by time."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """SELECT m.id, m.direction, m.channel, m.content,
                      m.sentiment_score, m.created_at, t.id as ticket_id,
                      t.status as ticket_status
               FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               LEFT JOIN tickets t ON t.id = m.ticket_id
               WHERE c.customer_id = $1
               ORDER BY m.created_at DESC
               LIMIT $2""",
            customer_id,
            limit,
        )
        return [dict(r) for r in rows]


async def get_latest_sentiment(customer_id: uuid.UUID) -> float | None:
    async with get_connection() as conn:
        return await conn.fetchval(
            """SELECT m.sentiment_score
               FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.customer_id = $1
                 AND m.direction = 'inbound'
                 AND m.sentiment_score IS NOT NULL
               ORDER BY m.created_at DESC LIMIT 1""",
            customer_id,
        )


# --- Knowledge Base ---

async def search_knowledge_base(
    embedding: list[float], max_results: int = 5
) -> list[dict]:
    """Semantic search using pgvector cosine similarity."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """SELECT id, title, content, category, source,
                      1 - (embedding <=> $1::vector) AS similarity
               FROM knowledge_base
               ORDER BY embedding <=> $1::vector
               LIMIT $2""",
            str(embedding),
            max_results,
        )
        return [dict(r) for r in rows]


async def add_knowledge_entry(
    title: str,
    content: str,
    embedding: list[float],
    category: str | None = None,
    source: str = "seed",
    source_ticket_id: uuid.UUID | None = None,
) -> dict:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO knowledge_base
                   (title, content, category, embedding, source, source_ticket_id)
               VALUES ($1, $2, $3, $4::vector, $5, $6)
               RETURNING id, title, category, source, created_at""",
            title,
            content,
            category,
            str(embedding),
            source,
            source_ticket_id,
        )
        return dict(row)


# --- Channel Config ---

async def get_channel_config(channel: str) -> dict | None:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM channel_configs WHERE channel = $1", channel
        )
        return dict(row) if row else None


# --- Agent Metrics ---

async def create_agent_metric(
    ticket_id: uuid.UUID,
    channel: str,
    response_time_ms: int | None = None,
    workflow_steps: list[str] | None = None,
    escalated: bool = False,
    escalation_reason: str | None = None,
    kb_results_count: int | None = None,
    kb_relevant: bool | None = None,
    sentiment_score: float | None = None,
) -> dict:
    async with get_connection() as conn:
        import json
        row = await conn.fetchrow(
            """INSERT INTO agent_metrics
                   (ticket_id, channel, response_time_ms, workflow_steps,
                    escalated, escalation_reason, kb_results_count,
                    kb_relevant, sentiment_score)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9)
               RETURNING id, ticket_id, channel, escalated, created_at""",
            ticket_id,
            channel,
            response_time_ms,
            json.dumps(workflow_steps) if workflow_steps else None,
            escalated,
            escalation_reason,
            kb_results_count,
            kb_relevant,
            sentiment_score,
        )
        return dict(row)


async def get_metrics_for_date(date_str: str) -> list[dict]:
    """Get all agent metrics for a given date (YYYY-MM-DD)."""
    from datetime import date as date_type
    async with get_connection() as conn:
        # Parse string to date object for asyncpg type compatibility
        d = date_type.fromisoformat(date_str)
        rows = await conn.fetch(
            """SELECT * FROM agent_metrics
               WHERE created_at::date = $1
               ORDER BY created_at""",
            d,
        )
        return [dict(r) for r in rows]


# --- Helpers ---

def __json(data: dict | None) -> str:
    import json
    return json.dumps(data or {})
