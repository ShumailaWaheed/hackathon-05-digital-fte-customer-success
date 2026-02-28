"""Gmail channel handler.

T041: GmailClient class with OAuth2 service account auth, poll_inbox,
parse_email (MIME body extraction), and send_reply (formal tone,
greeting + signature, ≤500 words). Per FR-004, FR-005.
"""

from __future__ import annotations

import base64
import email
import logging
import os
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from production.database import repositories

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
DELEGATED_USER = os.environ.get("GMAIL_DELEGATED_USER", "support@example.com")
MAX_WORDS = 500


class GmailClient:
    """Gmail API client with service account authentication."""

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service is None:
            creds = Credentials.from_service_account_file(
                CREDENTIALS_PATH, scopes=SCOPES
            )
            delegated = creds.with_subject(DELEGATED_USER)
            self._service = build("gmail", "v1", credentials=delegated)
        return self._service

    async def poll_inbox(self, after_timestamp: int | None = None) -> list[dict]:
        """Poll Gmail inbox for new messages.

        Args:
            after_timestamp: Unix epoch seconds. Only fetch messages after this time.

        Returns:
            List of parsed email dicts with keys: message_id, from_email,
            from_name, subject, body, timestamp.
        """
        service = self._get_service()

        query = "in:inbox is:unread"
        if after_timestamp:
            query += f" after:{after_timestamp}"

        try:
            result = service.users().messages().list(
                userId="me", q=query, maxResults=20
            ).execute()
        except Exception as e:
            logger.error("Gmail poll failed: %s", e)
            return []

        messages = result.get("messages", [])
        if not messages:
            return []

        parsed = []
        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                parsed_msg = self._parse_email(msg)
                if parsed_msg:
                    parsed.append(parsed_msg)

                # Mark as read
                service.users().messages().modify(
                    userId="me",
                    id=msg_ref["id"],
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute()
            except Exception as e:
                logger.warning("Failed to parse email %s: %s", msg_ref["id"], e)

        return parsed

    def _parse_email(self, msg: dict) -> dict | None:
        """Extract body, sender, subject from Gmail API message."""
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        from_header = headers.get("from", "")
        subject = headers.get("subject", "(no subject)")

        # Parse "Name <email>" format
        from_name, from_email = _parse_from_header(from_header)
        if not from_email:
            return None

        # Extract body
        body = _extract_body(msg.get("payload", {}))
        if not body:
            return None

        # Timestamp
        internal_date = int(msg.get("internalDate", 0)) // 1000
        timestamp = datetime.fromtimestamp(internal_date, tz=timezone.utc).isoformat()

        return {
            "message_id": msg["id"],
            "from_email": from_email,
            "from_name": from_name or from_email.split("@")[0],
            "subject": subject,
            "body": body.strip(),
            "timestamp": timestamp,
        }

    async def send_reply(
        self,
        to_email: str,
        body: str,
        ticket_id: str,
        subject: str | None = None,
    ) -> dict:
        """Send a formal email reply via Gmail API.

        Applies greeting + signature from channel_configs, enforces ≤500 words.
        """
        # Get channel config for formatting
        config = await repositories.get_channel_config("gmail")
        greeting = ""
        signature = ""
        max_words = MAX_WORDS

        if config:
            greeting = config.get("greeting_template") or ""
            signature = config.get("signature_template") or ""
            max_words = config.get("max_length", MAX_WORDS)

        # Enforce word cap
        words = body.split()
        if len(words) > max_words:
            body = " ".join(words[:max_words])

        # Compose with greeting + signature
        full_body = body
        if greeting:
            full_body = f"{greeting}\n\n{full_body}"
        if signature:
            full_body = f"{full_body}\n\n{signature}"

        # Build MIME message
        mime_msg = MIMEText(full_body, "plain", "utf-8")
        mime_msg["to"] = to_email
        mime_msg["from"] = DELEGATED_USER
        mime_msg["subject"] = subject or f"Re: Support Request [{ticket_id[:8]}]"

        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("ascii")

        service = self._get_service()
        try:
            sent = service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            logger.info("Gmail reply sent: to=%s ticket=%s gmail_id=%s", to_email, ticket_id, sent.get("id"))
            return {"status": "sent", "gmail_message_id": sent.get("id")}
        except Exception as e:
            logger.error("Gmail send failed: to=%s ticket=%s error=%s", to_email, ticket_id, e)
            raise


# --- Module-level helpers ---

def _parse_from_header(from_header: str) -> tuple[str, str]:
    """Parse 'Display Name <email@example.com>' into (name, email)."""
    match = re.match(r"^(.*?)\s*<([^>]+)>$", from_header.strip())
    if match:
        name = match.group(1).strip().strip('"')
        addr = match.group(2).strip()
        return name, addr
    # Plain email
    addr = from_header.strip()
    return "", addr


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from Gmail payload."""
    mime_type = payload.get("mimeType", "")

    # Direct text/plain part
    if mime_type == "text/plain" and "body" in payload:
        data = payload["body"].get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Fallback: try first text/html
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                # Strip HTML tags for plain text
                return re.sub(r"<[^>]+>", "", html)

    # Nested multipart
    for part in parts:
        result = _extract_body(part)
        if result:
            return result

    return ""


async def send_email_fallback(to_email: str, body: str, ticket_id: str) -> None:
    """Send an email fallback for web form responses (called by webform_handler)."""
    client = GmailClient()
    await client.send_reply(
        to_email=to_email,
        body=body,
        ticket_id=ticket_id,
        subject=f"Your Support Request [{ticket_id[:8]}]",
    )
