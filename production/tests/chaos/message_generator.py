"""T087: Chaos test message generator.

Produces randomized messages with mix of normal/escalation/edge cases.
"""

import random
import uuid
import string


CATEGORIES = ["billing-inquiry", "technical-issue", "feature-request", "account-help", "general-question"]
CHANNELS = ["webform", "gmail", "whatsapp"]

NORMAL_MESSAGES = [
    "How do I reset my password?",
    "Where can I find my invoice?",
    "Can you help me set up two-factor authentication?",
    "My dashboard is loading slowly.",
    "I want to upgrade my plan.",
    "How do I add a team member?",
    "Where are the API docs?",
    "Can I export my data?",
    "What are your business hours?",
    "How do I change my email address?",
]

ESCALATION_MESSAGES = [
    "I want a full refund immediately!",
    "I'm contacting my lawyer about this.",
    "Your competitor ProductX does this better.",
    "Let me speak to a human right now!",
    "This is the worst service I've ever used, get me a manager!",
    "How much does the enterprise plan cost?",
    "I'll sue if this isn't resolved today.",
]

EDGE_CASE_MESSAGES = [
    "",  # Empty
    "?" * 1000,  # Repeated chars
    "Hello " * 2000,  # Very long
    "refund lawyer human agent manager",  # Multi-guardrail
    "🔥🤬💀",  # Emoji-only
    "SELECT * FROM users; DROP TABLE users;",  # SQL injection attempt
    "<script>alert('xss')</script>",  # XSS attempt
]


class MessageGenerator:
    """Generates randomized test messages for chaos testing."""

    def generate_webform(self) -> dict:
        return {
            "name": f"User_{random.randint(1, 999)}",
            "email": f"user{random.randint(1, 999)}@test.com",
            "category": random.choice(CATEGORIES),
            "message": self._pick_message(),
            "channel": "webform",
        }

    def generate_gmail(self) -> dict:
        return {
            "from_email": f"user{random.randint(1, 999)}@gmail.com",
            "from_name": f"Gmail User {random.randint(1, 999)}",
            "subject": f"Support Request #{random.randint(1000, 9999)}",
            "body": self._pick_message(),
            "channel": "gmail",
        }

    def generate_whatsapp(self) -> dict:
        phone = f"+1{random.randint(2000000000, 9999999999)}"
        return {
            "from_phone": phone,
            "body": self._pick_message(),
            "message_sid": f"SM{''.join(random.choices(string.hexdigits, k=32))}",
            "channel": "whatsapp",
        }

    def generate_batch(self, count: int = 200) -> list[dict]:
        """Generate a batch of mixed messages.

        Distribution: 50% webform, 25% gmail, 25% whatsapp.
        Mix: 60% normal, 25% escalation, 15% edge case.
        """
        messages = []
        for _ in range(count):
            channel = random.choices(
                ["webform", "gmail", "whatsapp"],
                weights=[50, 25, 25],
            )[0]

            if channel == "webform":
                messages.append(self.generate_webform())
            elif channel == "gmail":
                messages.append(self.generate_gmail())
            else:
                messages.append(self.generate_whatsapp())

        return messages

    def _pick_message(self) -> str:
        roll = random.random()
        if roll < 0.60:
            return random.choice(NORMAL_MESSAGES)
        elif roll < 0.85:
            return random.choice(ESCALATION_MESSAGES)
        else:
            return random.choice(EDGE_CASE_MESSAGES)
