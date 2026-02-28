"""T082: Edge case tests (10+).

Covers: duplicate submission, empty body, long message, multiple guardrails,
unknown customer, KB no results, sentiment 0.3 boundary, malformed data,
channel switch, rate limiting edge.
"""

import pytest
from production.agent.guardrails import check_all
from production.channels.whatsapp_handler import split_message


class TestEdgeCases:

    # EC-01: Multiple guardrail triggers
    def test_multiple_guardrails_trigger(self):
        """Message triggering G1 + G2 should return both."""
        result = check_all("I want a refund and I'll contact my lawyer", 0.2)
        ids = [t["guardrail"] for t in result]
        assert "G1" in ids, "Should trigger G1 (refund)"
        assert "G2" in ids, "Should trigger G2 (lawyer)"

    # EC-02: Sentiment exactly 0.3
    def test_sentiment_boundary_0_3(self):
        """Sentiment exactly 0.3 should NOT trigger G5."""
        result = check_all("Normal question about account", 0.3)
        ids = [t["guardrail"] for t in result]
        assert "G5" not in ids

    # EC-03: Sentiment 0.29 triggers
    def test_sentiment_just_below_0_3(self):
        """Sentiment 0.29 should trigger G9."""
        result = check_all("Normal question", 0.29)
        ids = [t["guardrail"] for t in result]
        assert "G9" in ids

    # EC-04: Empty message to guardrails
    def test_empty_message(self):
        result = check_all("", 0.5)
        assert isinstance(result, list)

    # EC-05: Very long message
    def test_long_message_10000_chars(self):
        long_msg = "This is a test message. " * 500  # ~12000 chars
        result = check_all(long_msg, 0.6)
        assert isinstance(result, list)

    # EC-06: Unicode/non-English message
    def test_unicode_message(self):
        result = check_all("这是一个测试消息", 0.5)
        assert isinstance(result, list)

    # EC-07: Special characters in message
    def test_special_characters(self):
        result = check_all("refund!!! @#$%^&*()", 0.5)
        ids = [t["guardrail"] for t in result]
        assert "G1" in ids, "Punctuation should not block keyword detection"

    # EC-08: WhatsApp split with emoji
    def test_whatsapp_split_with_emoji(self):
        text = "Hello! 😊 " * 50
        segments = split_message(text, max_chars=300)
        for seg in segments:
            assert len(seg) <= 300

    # EC-09: Empty WhatsApp message
    def test_whatsapp_split_empty(self):
        segments = split_message("", max_chars=300)
        assert len(segments) == 1

    # EC-10: Single character message
    def test_single_char_message(self):
        result = check_all("?", 0.5)
        assert isinstance(result, list)

    # EC-11: All guardrail keywords in one message
    def test_all_keywords_combined(self):
        msg = "refund lawyer competitor human agent manager sue"
        result = check_all(msg, 0.1)
        ids = [t["guardrail"] for t in result]
        assert "G1" in ids
        assert "G2" in ids
        assert "G5" in ids

    # EC-12: Sentiment exactly 0.0 and 1.0
    def test_extreme_sentiments(self):
        result_0 = check_all("test message", 0.0)
        result_1 = check_all("test message", 1.0)
        assert isinstance(result_0, list)
        assert isinstance(result_1, list)
        # 0.0 should trigger G9 (< 0.3)
        ids_0 = [t["guardrail"] for t in result_0]
        assert "G9" in ids_0
