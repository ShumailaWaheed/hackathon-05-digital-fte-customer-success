"""Guardrail detection functions for G1-G5, G9.

Constitution v1.1.0 — Non-negotiable rules.
All checks return (triggered: bool, reason: str | None).
"""

from __future__ import annotations

# G1: Pricing/refund keywords
PRICING_KEYWORDS = {"price", "pricing", "refund", "billing", "cost", "discount"}

# G2: Legal keywords
LEGAL_KEYWORDS = {"lawyer", "sue", "legal", "lawsuit", "court"}

# G3: Competitor names (extend as needed)
COMPETITOR_NAMES = {
    "asana", "monday.com", "monday", "trello", "jira", "clickup",
    "basecamp", "notion", "wrike", "smartsheet", "todoist",
}

# G5: Trigger words for human escalation
TRIGGER_WORDS = {"human", "agent", "manager"}

# Sentiment threshold (strictly less than)
SENTIMENT_ESCALATION_THRESHOLD = 0.3


def _extract_words(text: str) -> set[str]:
    """Extract lowercase words, stripping punctuation."""
    import re
    return set(re.findall(r'[a-z]+(?:\.[a-z]+)*', text.lower()))


def check_pricing(message: str) -> tuple[bool, str | None]:
    """G1: Detect pricing/refund/billing keywords."""
    words = _extract_words(message)
    found = words & PRICING_KEYWORDS
    if found:
        return True, f"G1 - pricing/refund discussion detected: {', '.join(found)}"
    return False, None


def check_legal(message: str) -> tuple[bool, str | None]:
    """G2: Detect legal keywords."""
    words = _extract_words(message)
    found = words & LEGAL_KEYWORDS
    if found:
        return True, f"G2 - legal discussion detected: {', '.join(found)}"
    return False, None


def check_competitor(message: str) -> tuple[bool, str | None]:
    """G3: Detect competitor brand names."""
    lower = message.lower()
    found = [name for name in COMPETITOR_NAMES if name in lower]
    if found:
        return True, f"G3 - competitor mention detected: {', '.join(found)}"
    return False, None


def check_angry_customer(
    message: str, sentiment_score: float | None = None
) -> tuple[bool, str | None]:
    """G5: Detect angry customer via sentiment or trigger words."""
    reasons = []

    # Check sentiment threshold (strictly less than 0.3)
    if sentiment_score is not None and sentiment_score < SENTIMENT_ESCALATION_THRESHOLD:
        reasons.append(f"sentiment {sentiment_score:.2f} < {SENTIMENT_ESCALATION_THRESHOLD}")

    # Check trigger words
    words = _extract_words(message)
    # Include legal trigger words that also trigger G5
    g5_triggers = TRIGGER_WORDS | {"sue", "lawyer"}
    found = words & g5_triggers
    if found:
        reasons.append(f"trigger words: {', '.join(found)}")

    if reasons:
        return True, f"G5 - angry customer escalation: {'; '.join(reasons)}"
    return False, None


def check_sentiment_before_close(sentiment_score: float | None) -> tuple[bool, str | None]:
    """G9: Block ticket closure if customer sentiment is negative."""
    if sentiment_score is not None and sentiment_score < SENTIMENT_ESCALATION_THRESHOLD:
        return True, f"G9 - cannot close ticket: sentiment {sentiment_score:.2f} is negative"
    return False, None


def check_all(message: str, sentiment_score: float | None = None) -> list[dict]:
    """Run all guardrail checks. Returns list of triggered guardrails.

    Returns:
        List of dicts with 'guardrail' and 'reason' keys.
        Empty list means no guardrails triggered.
    """
    triggered = []

    checks = [
        ("G1", check_pricing(message)),
        ("G2", check_legal(message)),
        ("G3", check_competitor(message)),
        ("G5", check_angry_customer(message, sentiment_score)),
        ("G9", check_sentiment_before_close(sentiment_score)),
    ]

    for guardrail_id, (is_triggered, reason) in checks:
        if is_triggered:
            triggered.append({"guardrail": guardrail_id, "reason": reason})

    return triggered
