# Channel Handlers Architecture

## Overview

Three inbound channels feed into a unified message pipeline:

```
Gmail (polling 15s)  ──┐
WhatsApp (webhook)   ──┼──→ Kafka: inbound-messages ──→ Agent Workflow ──→ Kafka: outbound-responses
Web Form (POST API)  ──┘                                                          │
                                                                                   ├──→ Gmail (send_reply)
                                                                                   ├──→ WhatsApp (Twilio)
                                                                                   └──→ Web (DB polling)
```

## Web Form Flow

**File**: `production/channels/webform_handler.py`

1. Customer submits form → `POST /api/support`
2. `webhooks.py` validates with Pydantic (name, email, category, message)
3. `webform_handler.process_webform_message()`:
   - Resolves customer via `identity_resolver.resolve_customer("email", ...)`
   - Creates ticket immediately (returns ticket_id for polling)
   - Publishes unified message to Kafka `inbound-messages`
   - Fallback: if Kafka unavailable, calls `agent.process_message()` directly
4. Frontend polls `GET /api/support/{ticket_id}/status` every 2s
5. Response returned when ticket status = `resolved` or `escalated`

**Tone**: Semi-formal
**Length**: No hard limit (web display)
**Retry**: Kafka publish only; frontend retries via polling

## Gmail Flow

**File**: `production/channels/gmail_handler.py`

1. `gmail_poller.py` runs every 15s, calls `GmailClient.poll_inbox(after_timestamp)`
2. Gmail API: `users.messages.list` with `in:inbox is:unread after:{timestamp}`
3. For each new email:
   - `GmailClient._parse_email()` extracts body from MIME (text/plain → text/html fallback)
   - `_parse_from_header()` splits "Name \<email\>" format
   - Marks message as read
4. `gmail_poller.process_gmail_messages()`:
   - Resolves customer via `identity_resolver.resolve_customer("email", ...)`
   - Creates ticket
   - Publishes to Kafka `inbound-messages`
5. Outbound: `GmailClient.send_reply()`:
   - Gets greeting + signature from `channel_configs` table
   - Enforces ≤500 word cap
   - Sends via Gmail API `users.messages.send`

**Tone**: Formal (greeting + signature)
**Length**: ≤500 words
**Auth**: OAuth2 service account with domain-wide delegation

## WhatsApp Flow

**File**: `production/channels/whatsapp_handler.py`

1. Twilio sends POST to `/webhooks/whatsapp` (form-urlencoded)
2. `webhooks.py`:
   - Validates `X-Twilio-Signature` via HMAC-SHA1
   - `TwilioWhatsAppClient.parse_message()` extracts From, Body, MessageSid
3. Resolves customer via `identity_resolver.resolve_customer("phone", ...)`
4. Creates ticket, publishes to Kafka
5. Outbound: `TwilioWhatsAppClient.send_reply()`:
   - `split_message()` splits at sentence boundaries (`.!?`)
   - Fallback: word boundary if sentence >300 chars
   - Fallback: hard char split if no spaces
   - 500ms delay between segments
   - Sends via Twilio `client.messages.create`

**Tone**: Conversational/casual
**Length**: ≤300 chars per segment (auto-split)
**Auth**: Twilio Account SID + Auth Token

## Identity Resolution

**File**: `production/api/services/identity_resolver.py`

All three channels use `resolve_customer(identifier_type, identifier_value, name, source)`:
- Looks up `customer_identifiers` table
- If found: returns existing customer (cross-channel continuity)
- If not found: creates customer + links identifier

Identifier types: `email` (webform, gmail), `phone` (whatsapp), `form_session`

## Outbound Dispatch

**File**: `production/workers/outbound_sender.py`

Kafka consumer on `outbound-responses` topic:
- Routes to correct channel handler based on `channel` field
- Retry: exponential backoff 1s → 4s → 16s (max 3 attempts)
- On failure: marks ticket as `delivery-failed`

## Guardrail Enforcement

Guardrails run at two points:
1. **Pre-workflow** (in `agent.py`): `guardrails.check_all()` before any processing
2. **Pre-close** (G9): sentiment check before ticket resolution (sentiment ≥ 0.3 required)
