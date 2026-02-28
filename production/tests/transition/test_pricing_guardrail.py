"""T077: Test pricing guardrail G1.

Messages with refund/billing/cost/discount/price must escalate 100%.
Clean messages must not trigger.
"""

import pytest
from production.agent.guardrails import check_all


class TestPricingGuardrail:
    """G1: Pricing keywords must always trigger escalation."""

    @pytest.mark.parametrize("keyword", ["refund", "billing", "cost", "discount", "price"])
    def test_pricing_keyword_triggers_g1(self, keyword):
        result = check_all(f"I need help with {keyword} for my account", 0.6)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G1" in guardrail_ids, f"'{keyword}' should trigger G1"

    def test_pricing_keyword_with_punctuation(self):
        result = check_all("I want a refund!", 0.6)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G1" in guardrail_ids

    def test_clean_message_no_trigger(self):
        result = check_all("How do I reset my password?", 0.7)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G1" not in guardrail_ids

    def test_multiple_pricing_keywords(self):
        result = check_all("What is the cost and can I get a refund or discount?", 0.6)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G1" in guardrail_ids

    def test_pricing_case_insensitive(self):
        result = check_all("REFUND my account NOW", 0.5)
        guardrail_ids = [t["guardrail"] for t in result]
        assert "G1" in guardrail_ids
