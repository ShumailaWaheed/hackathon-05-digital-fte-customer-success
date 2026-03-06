"""Admin routes for approval system and ticket management.

Provides endpoints for:
- Listing pending approval responses
- Approving/rejecting AI-generated responses
- Listing all tickets with filtering
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from production.database import repositories
from production.database.connection import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    reason: str | None = None


class TicketOut(BaseModel):
    ticket_id: str
    customer_name: str
    customer_email: str | None
    channel: str
    issue: str
    priority: str
    status: str
    ai_response: str | None
    created_at: str
    updated_at: str


@router.get("/pending-approvals")
async def get_pending_approvals():
    """List all tickets waiting for admin approval with their AI-generated responses."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            """SELECT t.id as ticket_id, t.channel, t.issue, t.priority,
                      t.status, t.created_at, t.updated_at, t.metadata,
                      c.name as customer_name,
                      ci.identifier_value as customer_email,
                      m.content as ai_response, m.created_at as response_generated_at
               FROM tickets t
               JOIN customers c ON c.id = t.customer_id
               LEFT JOIN customer_identifiers ci
                   ON ci.customer_id = c.id AND ci.identifier_type = 'email'
               LEFT JOIN messages m
                   ON m.ticket_id = t.id AND m.direction = 'outbound'
               WHERE t.status = 'pending_approval'
               ORDER BY t.created_at DESC"""
        )
        return [
            {
                "ticket_id": str(r["ticket_id"]),
                "customer_name": r["customer_name"],
                "customer_email": r["customer_email"],
                "channel": r["channel"],
                "issue": r["issue"],
                "priority": r["priority"],
                "status": r["status"],
                "ai_response": r["ai_response"],
                "response_generated_at": r["response_generated_at"].isoformat() if r["response_generated_at"] else None,
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
                "metadata": dict(r["metadata"]) if r["metadata"] else {},
            }
            for r in rows
        ]


@router.post("/approve/{ticket_id}")
async def approve_response(ticket_id: str):
    """Approve an AI-generated response and send it to the customer."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    ticket = await repositories.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket["status"] != "pending_approval":
        raise HTTPException(status_code=400, detail="Ticket is not pending approval")

    # Get the AI response
    response_text = await repositories.get_ticket_response(tid)
    if not response_text:
        raise HTTPException(status_code=400, detail="No AI response found for this ticket")

    channel = ticket["channel"]

    # Send via the appropriate channel
    if channel == "gmail":
        try:
            from production.channels.gmail_handler import GmailClient
            client = GmailClient()
            email_addr = (ticket.get("metadata") or {}).get("email", "")
            thread_id = (ticket.get("metadata") or {}).get("thread_id")
            if email_addr:
                await client.send_reply(email_addr, response_text, thread_id=thread_id)
                logger.info("Approved: Gmail reply sent to %s", email_addr)
        except Exception as e:
            logger.error("Failed to send approved Gmail response: %s", e)

    elif channel == "whatsapp":
        try:
            from production.channels.whatsapp_handler import TwilioWhatsAppClient
            client = TwilioWhatsAppClient()
            phone = (ticket.get("metadata") or {}).get("phone", "")
            if phone:
                await client.send_reply(phone, response_text)
                logger.info("Approved: WhatsApp reply sent to %s", phone)
        except Exception as e:
            logger.error("Failed to send approved WhatsApp response: %s", e)

    # Update ticket to resolved
    await repositories.update_ticket_status(tid, "resolved")

    return {"status": "approved", "ticket_id": ticket_id, "message": "Response approved and sent"}


@router.post("/reject/{ticket_id}")
async def reject_response(ticket_id: str, body: ApprovalAction | None = None):
    """Reject an AI-generated response. Ticket goes back to open."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID")

    ticket = await repositories.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket["status"] != "pending_approval":
        raise HTTPException(status_code=400, detail="Ticket is not pending approval")

    # Delete the outbound message
    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM messages WHERE ticket_id = $1 AND direction = 'outbound'",
            tid,
        )

    # Set ticket back to open
    await repositories.update_ticket_status(tid, "open")

    return {"status": "rejected", "ticket_id": ticket_id, "message": "Response rejected"}


@router.get("/tickets")
async def list_tickets(status: str | None = None, limit: int = 50):
    """List all tickets with optional status filter."""
    async with get_connection() as conn:
        if status:
            rows = await conn.fetch(
                """SELECT t.id as ticket_id, t.channel, t.issue, t.priority,
                          t.status, t.created_at, t.updated_at,
                          c.name as customer_name,
                          ci.identifier_value as customer_email
                   FROM tickets t
                   JOIN customers c ON c.id = t.customer_id
                   LEFT JOIN customer_identifiers ci
                       ON ci.customer_id = c.id AND ci.identifier_type = 'email'
                   WHERE t.status = $1
                   ORDER BY t.created_at DESC
                   LIMIT $2""",
                status,
                limit,
            )
        else:
            rows = await conn.fetch(
                """SELECT t.id as ticket_id, t.channel, t.issue, t.priority,
                          t.status, t.created_at, t.updated_at,
                          c.name as customer_name,
                          ci.identifier_value as customer_email
                   FROM tickets t
                   JOIN customers c ON c.id = t.customer_id
                   LEFT JOIN customer_identifiers ci
                       ON ci.customer_id = c.id AND ci.identifier_type = 'email'
                   ORDER BY t.created_at DESC
                   LIMIT $1""",
                limit,
            )
        return [
            {
                "ticket_id": str(r["ticket_id"]),
                "customer_name": r["customer_name"],
                "customer_email": r["customer_email"],
                "channel": r["channel"],
                "issue": r["issue"],
                "priority": r["priority"],
                "status": r["status"],
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in rows
        ]


@router.get("/stats")
async def get_stats():
    """Get admin dashboard statistics."""
    async with get_connection() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM tickets")
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE status = 'pending_approval'"
        )
        resolved = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE status = 'resolved'"
        )
        escalated = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE status = 'escalated'"
        )
        open_count = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE status IN ('open', 'in-progress')"
        )

        # Channel breakdown
        channels = await conn.fetch(
            """SELECT channel, COUNT(*) as count
               FROM tickets GROUP BY channel ORDER BY count DESC"""
        )

        # Recent activity (last 24h)
        recent = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE created_at > now() - interval '24 hours'"
        )

        return {
            "total_tickets": total,
            "pending_approval": pending,
            "resolved": resolved,
            "escalated": escalated,
            "open": open_count,
            "recent_24h": recent,
            "channel_breakdown": [
                {"channel": r["channel"], "count": r["count"]} for r in channels
            ],
        }
