"""WhatsApp channel handler via Twilio.

T046: TwilioWhatsAppClient with signature validation, message parsing,
and send_reply (conversational tone, auto-split ≤300 chars). Per FR-006, FR-007.

T049: split_message() utility — splits at sentence boundaries, fallback
to word boundary if single sentence >300 chars.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import re
from urllib.parse import quote

from production.database import repositories

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
MAX_CHARS = 300
SPLIT_DELAY = 0.5  # 500ms between splits


class TwilioWhatsAppClient:
    """Twilio WhatsApp API client."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from twilio.rest import Client
            self._client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        return self._client

    async def send_reply(self, to_phone: str, message: str) -> list[dict]:
        """Send a WhatsApp reply, auto-splitting if >300 chars.

        Args:
            to_phone: Recipient phone in whatsapp:+NNNN format or plain +NNNN.
            message: The response text.

        Returns:
            List of sent message SIDs.
        """
        if not to_phone.startswith("whatsapp:"):
            to_phone = f"whatsapp:{to_phone}"

        # Get channel config for formatting
        config = await repositories.get_channel_config("whatsapp")
        max_chars = MAX_CHARS
        if config:
            max_chars = config.get("max_length", MAX_CHARS)

        segments = split_message(message, max_chars=max_chars)
        results = []

        client = self._get_client()
        for i, segment in enumerate(segments):
            try:
                sent = client.messages.create(
                    body=segment,
                    from_=TWILIO_WHATSAPP_FROM,
                    to=to_phone,
                )
                results.append({"sid": sent.sid, "status": sent.status})
                logger.info("WhatsApp segment %d/%d sent: sid=%s", i + 1, len(segments), sent.sid)

                # 500ms delay between multi-part messages
                if i < len(segments) - 1:
                    await asyncio.sleep(SPLIT_DELAY)
            except Exception as e:
                logger.error("WhatsApp send failed (segment %d): %s", i + 1, e)
                raise

        return results

    @staticmethod
    def validate_signature(url: str, params: dict, signature: str) -> bool:
        """Validate X-Twilio-Signature for incoming webhooks.

        Args:
            url: The full request URL.
            params: The POST form parameters.
            signature: The X-Twilio-Signature header value.

        Returns:
            True if signature is valid.
        """
        if not TWILIO_AUTH_TOKEN:
            logger.warning("TWILIO_AUTH_TOKEN not set — skipping signature validation")
            return True

        # Build data string: URL + sorted param key/value pairs
        data = url
        for key in sorted(params.keys()):
            data += key + params[key]

        expected = hmac.new(
            TWILIO_AUTH_TOKEN.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        import base64
        expected_b64 = base64.b64encode(expected).decode("ascii")
        return hmac.compare_digest(expected_b64, signature)

    @staticmethod
    def parse_message(form_data: dict) -> dict:
        """Parse Twilio WhatsApp webhook form data into normalized format.

        Args:
            form_data: URL-encoded form fields from Twilio.

        Returns:
            dict with from_phone, body, message_sid, num_media.
        """
        return {
            "from_phone": form_data.get("From", "").replace("whatsapp:", ""),
            "body": form_data.get("Body", ""),
            "message_sid": form_data.get("MessageSid", ""),
            "num_media": int(form_data.get("NumMedia", "0")),
        }


# --- Message Splitting (T049) ---

def split_message(text: str, max_chars: int = 300) -> list[str]:
    """Split text into segments ≤max_chars at natural sentence boundaries.

    Strategy:
    1. Split at sentence endings (.!?)
    2. Greedily combine sentences into segments ≤max_chars
    3. If a single sentence >max_chars, fall back to word boundary

    Args:
        text: The response text to split.
        max_chars: Maximum characters per segment.

    Returns:
        List of text segments, each ≤max_chars.
    """
    if len(text) <= max_chars:
        return [text]

    # Hard fallback: if no spaces at all, chunk by max_chars
    if " " not in text and not re.search(r'[.!?]', text):
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

    # Split into sentences (keep the delimiter)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    segments: list[str] = []
    current = ""

    for sentence in sentences:
        # If single sentence is too long, split by words
        if len(sentence) > max_chars:
            # Flush current buffer
            if current:
                segments.append(current.strip())
                current = ""
            # Word-level splitting
            words = sentence.split()
            chunk = ""
            for word in words:
                test = f"{chunk} {word}".strip() if chunk else word
                if len(test) <= max_chars:
                    chunk = test
                else:
                    if chunk:
                        segments.append(chunk)
                    chunk = word
            if chunk:
                segments.append(chunk)
            continue

        # Try adding sentence to current segment
        test = f"{current} {sentence}".strip() if current else sentence
        if len(test) <= max_chars:
            current = test
        else:
            if current:
                segments.append(current.strip())
            current = sentence

    if current:
        segments.append(current.strip())

    return segments
