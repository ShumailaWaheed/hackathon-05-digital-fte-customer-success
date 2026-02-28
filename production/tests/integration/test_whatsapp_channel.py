"""T085: Integration test — WhatsApp channel E2E."""

import sys
import pytest
from unittest.mock import MagicMock

# Mock external modules that may not be installed in test environment
for mod_name in [
    "agents", "openai", "confluent_kafka",
    "production.workers.kafka_config",
    "production.workers.learning_loop",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

_kafka_mod = sys.modules["production.workers.kafka_config"]
_kafka_mod.get_producer = MagicMock()
_kafka_mod.publish_message = MagicMock()

from production.channels.whatsapp_handler import TwilioWhatsAppClient, split_message


class TestWhatsAppParsing:

    def test_parse_message(self):
        form_data = {
            "From": "whatsapp:+1234567890",
            "Body": "Hello, I need help",
            "MessageSid": "SM123abc",
            "NumMedia": "0",
        }
        result = TwilioWhatsAppClient.parse_message(form_data)
        assert result["from_phone"] == "+1234567890"
        assert result["body"] == "Hello, I need help"
        assert result["message_sid"] == "SM123abc"
        assert result["num_media"] == 0

    def test_parse_message_empty(self):
        form_data = {"From": "", "Body": "", "MessageSid": "", "NumMedia": "0"}
        result = TwilioWhatsAppClient.parse_message(form_data)
        assert result["body"] == ""


class TestMessageSplitting:

    def test_short_message(self):
        assert split_message("Hello!", 300) == ["Hello!"]

    def test_split_at_sentences(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        segments = split_message(text, max_chars=40)
        assert all(len(s) <= 40 for s in segments)
        assert len(segments) >= 2

    def test_preserves_all_content(self):
        text = "One. Two. Three. Four. Five."
        segments = split_message(text, max_chars=15)
        rejoined = " ".join(segments)
        # All words should be present
        for word in ["One.", "Two.", "Three.", "Four.", "Five."]:
            assert word in rejoined

    def test_word_boundary_fallback(self):
        text = "word " * 100
        segments = split_message(text.strip(), max_chars=30)
        assert all(len(s) <= 30 for s in segments)

    def test_no_space_hard_split(self):
        text = "X" * 900
        segments = split_message(text, max_chars=300)
        assert len(segments) == 3

    @pytest.mark.asyncio
    async def test_webhook_endpoint(self):
        """WhatsApp webhook should accept Twilio form data via TestClient."""
        from unittest.mock import patch, AsyncMock
        import uuid

        with patch("production.channels.webform_handler.get_producer", return_value=MagicMock()), \
             patch("production.channels.webform_handler.publish_message"), \
             patch("production.channels.whatsapp_handler.TwilioWhatsAppClient") as mock_client, \
             patch("production.api.services.identity_resolver.resolve_customer", new_callable=AsyncMock) as mock_resolve, \
             patch("production.database.repositories.create_ticket", new_callable=AsyncMock) as mock_ticket, \
             patch("production.database.repositories.create_agent_metric", new_callable=AsyncMock):

            mock_client.validate_signature.return_value = True
            mock_client.parse_message.return_value = {
                "from_phone": "+1234567890",
                "body": "Help me",
                "message_sid": "SM123",
                "num_media": 0,
            }
            mock_resolve.return_value = {"id": uuid.uuid4(), "name": "Test"}
            mock_ticket.return_value = {"id": uuid.uuid4()}

            from fastapi.testclient import TestClient
            from production.api.main import app

            client = TestClient(app)
            response = client.post(
                "/webhooks/whatsapp",
                data={"From": "whatsapp:+1234567890", "Body": "Help me", "MessageSid": "SM123", "NumMedia": "0"},
                headers={"X-Twilio-Signature": "test-sig"},
            )

            # Endpoint should accept the request (200 or 202)
            assert response.status_code in (200, 202)
