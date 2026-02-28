"""Webhook routes for all inbound channels.

T029: POST /api/support — web form submission
T030: GET /api/support/{ticket_id}/status — poll for response
T044: POST /webhooks/gmail (Phase 4)
T047: POST /webhooks/whatsapp (Phase 5)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from fastapi import Request

from production.database import repositories
from production.channels.webform_handler import process_webform_message

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request / Response schemas ---

class SupportFormRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    category: str = Field(
        ...,
        pattern=r"^(billing-inquiry|technical-issue|feature-request|account-help|general-question)$",
    )
    message: str = Field(..., min_length=1, max_length=10000)


class SupportAccepted(BaseModel):
    ticket_id: str
    status: str = "processing"
    message: str = "Your request has been received and is being processed."


class TicketStatusResponse(BaseModel):
    ticket_id: str
    status: str
    response: str | None = None
    escalated: bool = False


# --- Endpoints ---

@router.post("/api/support", response_model=SupportAccepted, status_code=202)
async def submit_web_form(payload: SupportFormRequest):
    """Accept a web form support request.

    Resolves customer identity, creates ticket, and starts async processing.
    Per contracts/api.yaml — returns 202 with ticket_id.
    """
    try:
        result = await process_webform_message(
            name=payload.name,
            email=payload.email,
            category=payload.category,
            message=payload.message,
        )
        return SupportAccepted(
            ticket_id=result["ticket_id"],
            status="processing",
            message="Your request has been received and is being processed.",
        )
    except Exception as e:
        logger.error("Web form submission failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/support/{ticket_id}/status", response_model=TicketStatusResponse)
async def get_ticket_status(ticket_id: str):
    """Poll for ticket processing status and response.

    Returns current status (processing/responded/escalated) and response text
    when available. Frontend polls every 2s.
    """
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket ID format")

    ticket = await repositories.get_ticket_by_id(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    status = ticket["status"]
    response_text = None
    escalated = False

    if status == "escalated":
        escalated = True
        response_text = (
            "Your request has been escalated to a human agent who will "
            "follow up with you shortly."
        )
    elif status in ("resolved", "closed"):
        # Fetch the outbound message for this ticket
        outbound = await repositories.get_ticket_response(tid)
        response_text = outbound if outbound else "Your request has been processed."
        status = "responded"
    else:
        status = "processing"

    return TicketStatusResponse(
        ticket_id=ticket_id,
        status=status,
        response=response_text,
        escalated=escalated,
    )


# --- Gmail Webhook (T044) ---

@router.post("/webhooks/gmail", status_code=200)
async def receive_gmail_notification(request: Request):
    """Receive Gmail Pub/Sub push notification.

    Supports both Pub/Sub push and manual trigger. When a push notification
    arrives, it triggers an immediate poll cycle via the Gmail poller.
    Per contracts/webhooks.yaml.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Google Pub/Sub wraps data in message.data (base64)
    pub_sub_message = body.get("message", {})
    subscription = body.get("subscription", "")

    logger.info(
        "Gmail webhook received: subscription=%s message_id=%s",
        subscription,
        pub_sub_message.get("messageId", "none"),
    )

    # Trigger an immediate poll cycle
    try:
        from production.channels.gmail_handler import GmailClient
        from production.workers.gmail_poller import process_gmail_messages
        import time

        client = GmailClient()
        count = await process_gmail_messages(client, after_timestamp=int(time.time()) - 60)
        logger.info("Gmail webhook triggered poll: %d messages processed", count)
    except Exception as e:
        logger.error("Gmail webhook poll failed: %s", e)

    # Always acknowledge to prevent redelivery
    return {"status": "ok"}


# --- WhatsApp Webhook (T047) ---

@router.post("/webhooks/whatsapp", status_code=200)
async def receive_whatsapp_message(request: Request):
    """Receive inbound WhatsApp message from Twilio webhook.

    Validates X-Twilio-Signature, normalizes message, resolves customer
    identity, publishes to Kafka inbound-messages topic.
    Per contracts/webhooks.yaml.
    """
    from production.channels.whatsapp_handler import TwilioWhatsAppClient
    from production.api.services.identity_resolver import resolve_customer
    from production.workers.kafka_config import get_producer, publish_message

    # Parse form data (Twilio sends application/x-www-form-urlencoded)
    form_data = dict(await request.form())

    # Validate Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    request_url = str(request.url)

    if not TwilioWhatsAppClient.validate_signature(request_url, form_data, signature):
        logger.warning("Invalid Twilio signature for WhatsApp webhook")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Parse message
    parsed = TwilioWhatsAppClient.parse_message(form_data)
    phone = parsed["from_phone"]
    body = parsed["body"]

    if not body:
        # Return empty TwiML to acknowledge
        return ""

    logger.info("WhatsApp message received: from=%s sid=%s", phone, parsed["message_sid"])

    # Resolve customer by phone (centralized identity resolver)
    customer = await resolve_customer(
        identifier_type="phone",
        identifier_value=phone,
        name=phone,
        source="whatsapp",
    )

    customer_id = str(customer["id"])

    # Create ticket
    ticket = await repositories.create_ticket(
        customer_id=customer["id"],
        issue=body[:500],
        channel="whatsapp",
        priority="medium",
        metadata={
            "phone": phone,
            "twilio_message_sid": parsed["message_sid"],
        },
    )
    ticket_id = str(ticket["id"])

    # Publish to Kafka
    unified_message = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "channel": "whatsapp",
        "message": body,
        "metadata": {
            "phone": phone,
            "twilio_message_sid": parsed["message_sid"],
        },
    }

    try:
        producer = get_producer()
        publish_message(producer, "inbound-messages", unified_message, key=customer_id)
    except Exception as e:
        logger.warning("Kafka publish failed for WhatsApp message: %s", e)
        # Fallback: process directly
        from production.agent.agent import process_message
        await process_message(
            customer_id=customer_id,
            message_content=body,
            channel="whatsapp",
            metadata={"phone": phone},
        )

    # Return empty TwiML response
    return ""
