"""Shared test fixtures for all test suites."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def sample_customer():
    return {
        "id": uuid.uuid4(),
        "name": "Test User",
        "created_at": "2026-02-25T00:00:00Z",
        "updated_at": "2026-02-25T00:00:00Z",
        "metadata": {"source": "webform"},
    }


@pytest.fixture
def sample_ticket(sample_customer):
    return {
        "id": uuid.uuid4(),
        "customer_id": sample_customer["id"],
        "conversation_id": None,
        "channel": "webform",
        "issue": "How do I reset my password?",
        "priority": "medium",
        "status": "open",
        "created_at": "2026-02-25T00:00:00Z",
        "updated_at": "2026-02-25T00:00:00Z",
    }


@pytest.fixture
def mock_repositories():
    with patch("production.database.repositories") as mock:
        mock.create_customer = AsyncMock()
        mock.find_customer_by_identifier = AsyncMock(return_value=None)
        mock.link_identifier = AsyncMock()
        mock.create_ticket = AsyncMock()
        mock.update_ticket_status = AsyncMock()
        mock.get_ticket = AsyncMock()
        mock.get_ticket_by_id = AsyncMock()
        mock.get_ticket_response = AsyncMock()
        mock.create_message = AsyncMock()
        mock.get_customer_messages = AsyncMock(return_value=[])
        mock.search_knowledge_base = AsyncMock(return_value=[])
        mock.get_channel_config = AsyncMock(return_value=None)
        mock.create_agent_metric = AsyncMock()
        mock.get_active_conversation = AsyncMock(return_value=None)
        mock.create_conversation = AsyncMock()
        mock.get_latest_sentiment = AsyncMock(return_value=0.7)
        mock.get_metrics_for_date = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def mock_kafka():
    with patch("production.workers.kafka_config.get_producer") as mock_prod, \
         patch("production.workers.kafka_config.publish_message") as mock_pub:
        mock_prod.return_value = MagicMock()
        yield {"get_producer": mock_prod, "publish_message": mock_pub}
