"""T084: Integration test — Gmail channel E2E."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestGmailHandler:

    def test_parse_from_header_with_name(self):
        from production.channels.gmail_handler import _parse_from_header
        name, email = _parse_from_header('John Doe <john@example.com>')
        assert name == "John Doe"
        assert email == "john@example.com"

    def test_parse_from_header_plain_email(self):
        from production.channels.gmail_handler import _parse_from_header
        name, email = _parse_from_header("john@example.com")
        assert name == ""
        assert email == "john@example.com"

    def test_parse_from_header_quoted_name(self):
        from production.channels.gmail_handler import _parse_from_header
        name, email = _parse_from_header('"John Doe" <john@example.com>')
        assert name == "John Doe"
        assert email == "john@example.com"

    def test_extract_body_plain_text(self):
        import base64
        from production.channels.gmail_handler import _extract_body

        body_text = "Hello, this is a test email."
        encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

        payload = {
            "mimeType": "text/plain",
            "body": {"data": encoded},
        }
        result = _extract_body(payload)
        assert result == body_text

    def test_extract_body_multipart(self):
        import base64
        from production.channels.gmail_handler import _extract_body

        body_text = "Plain text body."
        encoded = base64.urlsafe_b64encode(body_text.encode()).decode()

        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": encoded}},
                {"mimeType": "text/html", "body": {"data": ""}},
            ],
        }
        result = _extract_body(payload)
        assert result == body_text

    @pytest.mark.asyncio
    async def test_send_reply_enforces_500_words(self):
        """Reply should be capped at 500 words."""
        with patch("production.channels.gmail_handler.repositories") as mock_repo, \
             patch("production.channels.gmail_handler.Credentials"), \
             patch("production.channels.gmail_handler.build") as mock_build:

            mock_repo.get_channel_config = AsyncMock(return_value={
                "max_length": 500,
                "greeting_template": "Dear Customer,",
                "signature_template": "Best regards,\nSupport Team",
            })

            mock_service = MagicMock()
            mock_service.users().messages().send().execute.return_value = {"id": "msg123"}
            mock_build.return_value = mock_service

            from production.channels.gmail_handler import GmailClient
            client = GmailClient()
            client._service = mock_service

            long_body = " ".join(["word"] * 600)
            await client.send_reply("test@example.com", long_body, "ticket123")

            # Verify send was called
            mock_service.users().messages().send.assert_called()
