"""T080: Test strict workflow order (Constitution Principle III).

Process message must follow: analyze_sentiment → create_ticket →
get_customer_history → search_knowledge_base → send_response/escalate.
"""

import sys
import types
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

# Patch agents module with required classes
_agents_mod = sys.modules["agents"]
_agents_mod.Agent = MagicMock
_agents_mod.Runner = MagicMock()

# Patch kafka_config exports
_kafka_mod = sys.modules["production.workers.kafka_config"]
_kafka_mod.get_producer = MagicMock()
_kafka_mod.publish_message = MagicMock()


@pytest.mark.asyncio
async def test_workflow_step_order():
    """Verify workflow_steps order in process_message result."""
    customer_id = str(uuid.uuid4())

    with patch("production.agent.agent._analyze_sentiment_direct", new_callable=AsyncMock) as mock_sent, \
         patch("production.agent.agent._search_kb_direct", new_callable=AsyncMock) as mock_kb, \
         patch("production.agent.agent.repositories") as mock_repo, \
         patch("production.agent.agent.guardrails") as mock_guard, \
         patch("production.agent.agent.Runner") as mock_runner, \
         patch("production.agent.agent.get_producer") as mock_prod, \
         patch("production.agent.agent.publish_message"):

        # Setup mocks
        mock_sent.return_value = 0.7  # Positive sentiment
        mock_kb.return_value = "Some KB result"
        mock_guard.check_all.return_value = []  # No guardrails triggered

        ticket_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_repo.create_ticket = AsyncMock(return_value={"id": ticket_id})
        mock_repo.update_ticket_status = AsyncMock(return_value={})
        mock_repo.get_customer_messages = AsyncMock(return_value=[])
        mock_repo.get_active_conversation = AsyncMock(return_value={"id": conv_id})
        mock_repo.create_conversation = AsyncMock(return_value={"id": conv_id})
        mock_repo.create_message = AsyncMock()
        mock_repo.get_channel_config = AsyncMock(return_value=None)
        mock_repo.create_agent_metric = AsyncMock()
        mock_prod.return_value = MagicMock()

        # Mock Runner.run
        mock_result = MagicMock()
        mock_result.final_output = "Here is your answer."
        mock_runner.run = AsyncMock(return_value=mock_result)

        from production.agent.agent import process_message
        result = await process_message(
            customer_id=customer_id,
            message_content="How do I reset my password?",
            channel="webform",
        )

        steps = result["workflow_steps"]
        assert steps[0] == "analyze_sentiment"
        assert steps[1] == "create_ticket"
        assert steps[2] == "get_customer_history"
        assert steps[3] == "search_knowledge_base"
        assert "send_response" in steps


@pytest.mark.asyncio
async def test_workflow_escalation_order():
    """When guardrails trigger, workflow should still follow order up to escalation."""
    customer_id = str(uuid.uuid4())

    with patch("production.agent.agent._analyze_sentiment_direct", new_callable=AsyncMock) as mock_sent, \
         patch("production.agent.agent._search_kb_direct", new_callable=AsyncMock) as mock_kb, \
         patch("production.agent.agent.repositories") as mock_repo, \
         patch("production.agent.agent.guardrails") as mock_guard, \
         patch("production.agent.agent.get_producer") as mock_prod, \
         patch("production.agent.agent.publish_message"):

        mock_sent.return_value = 0.2
        mock_kb.return_value = ""
        mock_guard.check_all.return_value = [{"guardrail": "G1", "reason": "pricing"}]

        ticket_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_repo.create_ticket = AsyncMock(return_value={"id": ticket_id})
        mock_repo.update_ticket_status = AsyncMock(return_value={})
        mock_repo.get_customer_messages = AsyncMock(return_value=[])
        mock_repo.get_active_conversation = AsyncMock(return_value={"id": conv_id})
        mock_repo.create_message = AsyncMock()
        mock_repo.create_agent_metric = AsyncMock()
        mock_prod.return_value = MagicMock()

        from production.agent.agent import process_message
        result = await process_message(
            customer_id=customer_id,
            message_content="I want a refund",
            channel="webform",
        )

        assert result["action"] == "escalated"
        steps = result["workflow_steps"]
        assert "analyze_sentiment" in steps
        assert "create_ticket" in steps
        assert "escalate_to_human" in steps
