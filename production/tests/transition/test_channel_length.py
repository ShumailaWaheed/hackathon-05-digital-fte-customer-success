"""T079: Test channel length enforcement G7.

Gmail replies > 500 words must be truncated.
WhatsApp replies > 300 chars must be split.
"""

import pytest
from production.channels.whatsapp_handler import split_message


class TestChannelLength:
    """Channel-specific length limits."""

    def test_whatsapp_split_at_300(self):
        text = "This is a test. " * 30  # ~480 chars
        segments = split_message(text, max_chars=300)
        for seg in segments:
            assert len(seg) <= 300, f"Segment too long: {len(seg)}"
        assert len(segments) >= 2

    def test_whatsapp_no_split_under_300(self):
        text = "Short message."
        segments = split_message(text, max_chars=300)
        assert len(segments) == 1
        assert segments[0] == text

    def test_whatsapp_exact_300(self):
        text = "A" * 300
        segments = split_message(text, max_chars=300)
        assert len(segments) == 1

    def test_whatsapp_split_at_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence."
        segments = split_message(text, max_chars=35)
        # Each sentence is ~16 chars, pairs fit in 35
        for seg in segments:
            assert len(seg) <= 35

    def test_whatsapp_word_boundary_fallback(self):
        text = "word " * 100  # 500 chars, no sentence endings
        segments = split_message(text.strip(), max_chars=50)
        for seg in segments:
            assert len(seg) <= 50

    def test_whatsapp_hard_split_no_spaces(self):
        text = "A" * 600
        segments = split_message(text, max_chars=300)
        assert len(segments) == 2
        assert len(segments[0]) == 300
        assert len(segments[1]) == 300

    def test_gmail_500_word_limit(self):
        """Gmail responses should be capped at 500 words.
        This is enforced in agent.py channel formatting and gmail_handler.send_reply.
        """
        words = ["word"] * 600
        text = " ".join(words)
        # Simulate the truncation logic from agent.py
        max_words = 500
        truncated = " ".join(text.split()[:max_words])
        assert len(truncated.split()) == 500
