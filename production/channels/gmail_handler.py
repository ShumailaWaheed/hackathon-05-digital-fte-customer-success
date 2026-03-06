"""Gmail channel handler using SMTP/IMAP (App Password auth).

T041: GmailClient class with SMTP send and IMAP poll for regular Gmail accounts.
Uses App Password authentication instead of Google API service account.
Supports: poll_inbox, send_reply (formal tone, greeting + signature, ≤500 words).
"""

from __future__ import annotations

import asyncio
import email as email_lib
import imaplib
import logging
import os
import re
import smtplib
from datetime import datetime, timezone
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from production.database import repositories

logger = logging.getLogger(__name__)

GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
MAX_WORDS = 500


class GmailClient:
    """Gmail client using SMTP (send) and IMAP (receive) with App Password."""

    def __init__(self):
        self._email = GMAIL_EMAIL
        self._password = GMAIL_APP_PASSWORD

    async def poll_inbox(self, after_timestamp: int | None = None) -> list[dict]:
        """Poll Gmail inbox for unread messages via IMAP.

        Args:
            after_timestamp: Unix epoch seconds. Only fetch messages after this time.

        Returns:
            List of parsed email dicts with keys: message_id, from_email,
            from_name, subject, body, timestamp.
        """
        def _poll():
            results = []
            try:
                mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
                mail.login(self._email, self._password)
                mail.select("INBOX")

                # Search for unseen messages
                if after_timestamp:
                    dt = datetime.fromtimestamp(after_timestamp, tz=timezone.utc)
                    date_str = dt.strftime("%d-%b-%Y")
                    status, data = mail.search(None, f'(UNSEEN SINCE {date_str})')
                else:
                    status, data = mail.search(None, "UNSEEN")

                if status != "OK" or not data[0]:
                    mail.logout()
                    return results

                msg_ids = data[0].split()[-20:]  # Last 20 unread

                for msg_id in msg_ids:
                    try:
                        status, msg_data = mail.fetch(msg_id, "(RFC822)")
                        if status != "OK":
                            continue

                        raw_email = msg_data[0][1]
                        msg = email_lib.message_from_bytes(raw_email)
                        parsed = _parse_email_message(msg)
                        if parsed:
                            parsed["imap_id"] = msg_id.decode()
                            results.append(parsed)

                        # Mark as read
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                    except Exception as e:
                        logger.warning("Failed to parse email %s: %s", msg_id, e)

                mail.logout()
            except Exception as e:
                logger.error("IMAP poll failed: %s", e)
            return results

        return await asyncio.get_event_loop().run_in_executor(None, _poll)

    async def send_reply(
        self,
        to_email: str,
        body: str,
        ticket_id: str | None = None,
        subject: str | None = None,
        thread_id: str | None = None,
    ) -> dict:
        """Send a formal email reply via SMTP with App Password.

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
        mime_msg = MIMEMultipart("alternative")
        mime_msg["From"] = f"AI Support <{self._email}>"
        mime_msg["To"] = to_email

        ticket_ref = f" [{ticket_id[:8]}]" if ticket_id else ""
        mime_msg["Subject"] = subject or f"Re: Support Request{ticket_ref}"

        # Plain text part
        mime_msg.attach(MIMEText(full_body, "plain", "utf-8"))

        # HTML part (basic formatting)
        html_body = full_body.replace("\n", "<br>")
        html_content = f"""<html><body>
<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{html_body}
</div>
</body></html>"""
        mime_msg.attach(MIMEText(html_content, "html", "utf-8"))

        def _send():
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                server.login(self._email, self._password)
                server.send_message(mime_msg)

        try:
            await asyncio.get_event_loop().run_in_executor(None, _send)
            logger.info("Gmail reply sent: to=%s ticket=%s", to_email, ticket_id)
            return {"status": "sent", "to": to_email}
        except Exception as e:
            logger.error("Gmail send failed: to=%s ticket=%s error=%s", to_email, ticket_id, e)
            raise


# --- Module-level helpers ---

def _decode_header_value(value: str) -> str:
    """Decode RFC 2047 encoded header value."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _parse_from_header(from_header: str) -> tuple[str, str]:
    """Parse 'Display Name <email@example.com>' into (name, email)."""
    match = re.match(r"^(.*?)\s*<([^>]+)>$", from_header.strip())
    if match:
        name = match.group(1).strip().strip('"')
        addr = match.group(2).strip()
        return name, addr
    addr = from_header.strip()
    return "", addr


def _parse_email_message(msg) -> dict | None:
    """Parse a Python email.message.Message into a dict."""
    from_header = _decode_header_value(msg.get("From", ""))
    subject = _decode_header_value(msg.get("Subject", "(no subject)"))
    message_id = msg.get("Message-ID", "")

    from_name, from_email = _parse_from_header(from_header)
    if not from_email:
        return None

    # Extract body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
                    break
        # Fallback to HTML if no plain text
        if not body:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html = payload.decode("utf-8", errors="replace")
                        body = re.sub(r"<[^>]+>", "", html)
                        break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="replace")

    if not body:
        return None

    # Parse date
    date_str = msg.get("Date", "")
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        timestamp = dt.isoformat()
    except Exception:
        timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "message_id": message_id,
        "from_email": from_email,
        "from_name": from_name or from_email.split("@")[0],
        "subject": subject,
        "body": body.strip(),
        "timestamp": timestamp,
    }


async def send_email_fallback(to_email: str, body: str, ticket_id: str) -> None:
    """Send an email fallback for web form responses (called by webform_handler)."""
    client = GmailClient()
    await client.send_reply(
        to_email=to_email,
        body=body,
        ticket_id=ticket_id,
        subject=f"Your Support Request [{ticket_id[:8]}]",
    )
