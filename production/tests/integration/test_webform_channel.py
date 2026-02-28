"""T083: Integration test — Web Form channel E2E."""

import sys
import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

# Mock external modules that may not be installed in test environment
for mod_name in [
    "agents", "openai", "confluent_kafka",
    "production.workers.kafka_config",
    "production.workers.learning_loop",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

_agents_mod = sys.modules["agents"]
_agents_mod.Agent = MagicMock
_agents_mod.Runner = MagicMock()

_kafka_mod = sys.modules["production.workers.kafka_config"]
_kafka_mod.get_producer = MagicMock()
_kafka_mod.publish_message = MagicMock()


@pytest.mark.asyncio
async def test_submit_webform_returns_202():
    """POST /api/support should return 202 with ticket_id."""
    ticket_id = uuid.uuid4()

    with patch("production.channels.webform_handler.get_producer", return_value=MagicMock()), \
         patch("production.channels.webform_handler.publish_message"), \
         patch("production.api.routes.webhooks.process_webform_message", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = {"ticket_id": str(ticket_id), "customer_id": str(uuid.uuid4())}

        from fastapi.testclient import TestClient
        from production.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/support", json={
            "name": "Test User",
            "email": "test@example.com",
            "category": "general-question",
            "message": "How do I reset my password?",
        })

        assert response.status_code == 202
        data = response.json()
        assert "ticket_id" in data
        assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_submit_webform_validation_error():
    """Invalid form data should return 422."""
    with patch("production.channels.webform_handler.get_producer", return_value=MagicMock()), \
         patch("production.channels.webform_handler.publish_message"):
        from fastapi.testclient import TestClient
        from production.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/api/support", json={
            "name": "",
            "email": "not-an-email",
            "category": "invalid-category",
            "message": "",
        })

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_ticket_status_polling():
    """GET /api/support/{id}/status should return status."""
    ticket_id = uuid.uuid4()

    with patch("production.channels.webform_handler.get_producer", return_value=MagicMock()), \
         patch("production.channels.webform_handler.publish_message"), \
         patch("production.api.routes.webhooks.repositories") as mock_repo:
        mock_repo.get_ticket_by_id = AsyncMock(return_value={
            "id": ticket_id,
            "status": "resolved",
        })
        mock_repo.get_ticket_response = AsyncMock(return_value="Here is your answer.")

        from fastapi.testclient import TestClient
        from production.api.main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get(f"/api/support/{ticket_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "responded"
        assert data["response"] == "Here is your answer."
