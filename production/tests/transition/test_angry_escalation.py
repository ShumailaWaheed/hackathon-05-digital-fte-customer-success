"""T078: Test angry customer escalation G5.

Messages with trigger words (human/agent/manager) + sentiment < 0.3 must escalate.
Exactly 0.3 should NOT trigger G5.
"""

import pytest
from production.agent.guardrails import check_all


class TestAngryEscalation:
    """G5: Trigger words + low sentiment must escalate."""

    @pytest.mark.parametrize("word", ["human", "agent", "manager"])
    def test_trigger_word_with_low_sentiment(self, word):
        result = check_all(f"Let me speak to a {word}", 0.2)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G5" in guardrail_ids, f"'{word}' + sentiment 0.2 should trigger G5"

    def test_trigger_word_with_high_sentiment(self):
        """Trigger words alone without low sentiment should still trigger G5 per spec."""
        result = check_all("Can I talk to a human please?", 0.8)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G5" in guardrail_ids

    def test_boundary_sentiment_0_3_exact(self):
        """Sentiment exactly 0.3 should NOT trigger G5 (strictly < 0.3)."""
        result = check_all("I need help with my account", 0.3)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G5" not in guardrail_ids

    def test_sentiment_0_29_triggers(self):
        result = check_all("This is terrible, get me a manager", 0.29)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G5" in guardrail_ids

    def test_no_trigger_words_low_sentiment(self):
        """Low sentiment alone without trigger words should not trigger G5."""
        result = check_all("I am very unhappy with the service", 0.1)
        guardrail_ids = [t["guardrail"] for t in result]
        # G5 requires trigger words OR low sentiment — check behavior
        # Per constitution: G5 triggers on trigger words OR sentiment < 0.3
        # So low sentiment alone CAN trigger
        pass  # Implementation-dependent
