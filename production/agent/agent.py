"""OpenAI Agents SDK agent with all 7 tools, guardrails, and strict workflow.

Constitution Principle III: create_ticket → get_customer_history →
search_knowledge_base → send_response (no step skipped or reordered).

Workflow is enforced PROGRAMMATICALLY in process_message().
The Agent + Runner is used only for response text generation.
Tools are registered on the Agent for when the Runner calls them.
"""

from __future__ import annotations

import json
import os
import uuid
import logging
from pathlib import Path

from agents import Agent, Runner, RunConfig, OpenAIProvider

from .llm_client import get_chat_client, generate_embedding_async, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from .tools.analyze_sentiment import analyze_sentiment
from .tools.create_ticket import create_ticket
from .tools.get_customer_history import get_customer_history
from .tools.search_knowledge_base import search_knowledge_base
from .tools.escalate_to_human import escalate_to_human
from .tools.send_response import send_response
from .tools.generate_daily_report import generate_daily_report
from production.agent import guardrails
from production.database import repositories
from production.workers.kafka_config import get_producer, publish_message

logger = logging.getLogger(__name__)

# Load system prompt
_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"
SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

# All 7 tools registered on the Agent for SDK usage
TOOLS = [
    analyze_sentiment,
    create_ticket,
    get_customer_history,
    search_knowledge_base,
    escalate_to_human,
    send_response,
    generate_daily_report,
]


def _get_provider() -> OpenAIProvider:
    """Create an OpenAI-compatible provider pointing at Groq."""
    return OpenAIProvider(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        use_responses=False,  # Groq doesn't support the responses API
    )


def create_agent() -> Agent:
    """Create the Customer Success agent with all tools and system prompt."""
    return Agent(
        name="Customer Success FTE",
        instructions=SYSTEM_PROMPT,
        tools=TOOLS,
        model=os.environ.get("LLM_MODEL", LLM_MODEL),
    )


# ---------------------------------------------------------------------------
# Direct helper functions (bypass @function_tool, call repos/APIs directly)
# ---------------------------------------------------------------------------

async def _analyze_sentiment_direct(message: str) -> float:
    """Call Groq (free) for sentiment score. Returns 0.0-1.0."""
    try:
        client = get_chat_client()
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sentiment analyzer. Respond with ONLY a "
                        "number between 0.0 and 1.0. 0.0 = extremely negative, "
                        "0.5 = neutral, 1.0 = extremely positive."
                    ),
                },
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=10,
        )
        score = float(response.choices[0].message.content.strip())
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("Sentiment analysis failed: %s", e)
        return 0.5


async def _search_kb_direct(query: str, max_results: int = 5) -> str:
    """Generate embedding locally and search pgvector. Returns formatted results."""
    try:
        embedding = await generate_embedding_async(query)
        results = await repositories.search_knowledge_base(embedding, max_results)
        if not results:
            return "No relevant knowledge base entries found."
        return "\n\n".join(
            f"[{r.get('similarity', 0):.2f}] {r['title']}: {r['content']}"
            for r in results
        )
    except Exception as e:
        logger.warning("KB search failed: %s", e)
        return "Knowledge base search unavailable."


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

async def process_message(
    customer_id: str,
    message_content: str,
    channel: str,
    metadata: dict | None = None,
    existing_ticket_id: str | None = None,
) -> dict:
    """Process an inbound message through the strict workflow.

    Enforces Constitution Principle III order programmatically:
      analyze_sentiment → create_ticket → get_customer_history →
      search_knowledge_base → (guardrail gate) → send_response | escalate

    Args:
        existing_ticket_id: If provided, reuses this ticket instead of creating a new one.

    Returns:
        dict with 'action', 'ticket_id', and details.
    """
    cid = uuid.UUID(customer_id)
    workflow_steps: list[str] = []

    # Step 0: Analyze sentiment (every message — Principle VI)
    sentiment_score = await _analyze_sentiment_direct(message_content)
    workflow_steps.append("analyze_sentiment")

    # Pre-check guardrails
    triggered = guardrails.check_all(message_content, sentiment_score)

    # Step 1: create_ticket (G6 — ticket-first mandate)
    try:
        if existing_ticket_id:
            ticket_id = uuid.UUID(existing_ticket_id)
        else:
            ticket = await repositories.create_ticket(
                customer_id=cid,
                issue=message_content,
                channel=channel,
                priority="high" if triggered else "medium",
                metadata=metadata,
            )
            ticket_id = ticket["id"]  # UUID
        await repositories.update_ticket_status(ticket_id, "in-progress")
    except Exception as e:
        logger.error("Failed to create ticket: %s", e)
        return {"action": "error", "error": str(e), "workflow_steps": workflow_steps}
    workflow_steps.append("create_ticket")

    # Step 2: get_customer_history
    try:
        history_rows = await repositories.get_customer_messages(cid, limit=50)
        if history_rows:
            history = "\n".join(
                f"[{m['created_at']}] [{m['channel']}] "
                f"{'Customer' if m['direction'] == 'inbound' else 'Agent'}: "
                f"{m['content']}"
                for m in history_rows
            )
        else:
            history = "No previous conversation history."
    except Exception as e:
        logger.warning("Failed to get history: %s", e)
        history = "History unavailable."
    workflow_steps.append("get_customer_history")

    # Step 3: search_knowledge_base
    kb_results = await _search_kb_direct(message_content, max_results=5)
    workflow_steps.append("search_knowledge_base")

    # Store inbound message with sentiment
    try:
        conv = await repositories.get_active_conversation(cid)
        if not conv:
            conv = await repositories.create_conversation(cid, subject=message_content[:200])
        await repositories.create_message(
            conversation_id=conv["id"],
            direction="inbound",
            channel=channel,
            content=message_content,
            ticket_id=ticket_id,
            sentiment_score=sentiment_score,
            metadata=metadata,
        )
    except Exception as e:
        logger.warning("Failed to store message: %s", e)

    # --- Guardrail gate ---
    if triggered:
        reasons = "; ".join(t["reason"] for t in triggered)
        logger.info("Guardrails triggered for ticket %s: %s", ticket_id, reasons)

        await repositories.update_ticket_status(
            ticket_id, "escalated", escalation_reason=reasons
        )

        # Publish to escalations Kafka topic
        try:
            producer = get_producer()
            publish_message(producer, "escalations", {
                "ticket_id": str(ticket_id),
                "reason": reasons,
                "customer_id": customer_id,
                "channel": channel,
                "sentiment": sentiment_score,
            })
        except Exception as e:
            logger.warning("Kafka escalation publish failed: %s", e)

        # Send empathy message directly to customer
        empathy_msg = (
            "I understand your frustration and I'm sorry for the inconvenience. "
            "Your request has been escalated to a human agent who will follow up "
            "with you shortly. We want to make sure you get the best possible help."
        )
        try:
            if channel == "whatsapp":
                phone = (metadata or {}).get("phone", "")
                if phone:
                    from production.channels.whatsapp_handler import TwilioWhatsAppClient
                    client = TwilioWhatsAppClient()
                    await client.send_reply(phone, empathy_msg)
                    logger.info("Escalation empathy message sent via WhatsApp to %s", phone)
            elif channel == "gmail":
                email_addr = (metadata or {}).get("email", "")
                if email_addr:
                    from production.channels.gmail_handler import GmailClient
                    client = GmailClient()
                    await client.send_reply(email_addr, empathy_msg)
                    logger.info("Escalation empathy message sent via Gmail to %s", email_addr)
        except Exception as de:
            logger.error("Escalation direct delivery failed: %s", de)

        # Store escalation message in DB
        try:
            conv = await repositories.get_active_conversation(cid)
            if conv:
                await repositories.create_message(
                    conversation_id=conv["id"],
                    direction="outbound",
                    channel=channel,
                    content=empathy_msg,
                    ticket_id=ticket_id,
                )
        except Exception:
            pass

        # Record metric
        await repositories.create_agent_metric(
            ticket_id=ticket_id,
            channel=channel,
            escalated=True,
            escalation_reason=reasons,
            sentiment_score=sentiment_score,
            workflow_steps=workflow_steps,
        )

        workflow_steps.append("escalate_to_human")
        return {
            "action": "escalated",
            "ticket_id": str(ticket_id),
            "reason": reasons,
            "sentiment": sentiment_score,
            "workflow_steps": workflow_steps,
        }

    # Step 4: Generate response via Agent SDK
    agent = create_agent()
    context_prompt = (
        f"Customer message ({channel}): {message_content}\n\n"
        f"Sentiment: {sentiment_score:.2f}\n\n"
        f"Customer history:\n{history}\n\n"
        f"Knowledge base results:\n{kb_results}\n\n"
        f"Ticket ID: {ticket_id}\n"
        f"Channel: {channel}\n\n"
        f"Generate an appropriate {channel} response following channel "
        f"formatting rules. Do NOT call any tools — just generate the "
        f"response text."
    )

    try:
        run_config = RunConfig(model_provider=_get_provider())
        result = await Runner.run(agent, context_prompt, run_config=run_config)
        response_text = result.final_output or "I'll look into this for you."
    except Exception as e:
        logger.error("Agent response generation failed: %s", e)
        response_text = "Thank you for reaching out. A team member will follow up shortly."

    # Apply channel formatting
    try:
        config = await repositories.get_channel_config(channel)
        if config:
            max_length = config["max_length"]
            if channel == "gmail":
                words = response_text.split()
                if len(words) > max_length:
                    response_text = " ".join(words[:max_length])
                greeting = config.get("greeting_template") or ""
                signature = config.get("signature_template") or ""
                if greeting:
                    response_text = f"{greeting}\n\n{response_text}"
                if signature:
                    response_text = f"{response_text}\n\n{signature}"
            elif channel == "whatsapp" and len(response_text) > max_length:
                response_text = response_text[:max_length]
    except Exception as e:
        logger.warning("Channel formatting failed: %s", e)

    # Publish to outbound Kafka topic, fallback to direct channel delivery
    sent_via_kafka = False
    try:
        producer = get_producer()
        publish_message(producer, "outbound-responses", {
            "ticket_id": str(ticket_id),
            "channel": channel,
            "message": response_text,
            "metadata": metadata or {},
        })
        sent_via_kafka = True
    except Exception as e:
        logger.warning("Kafka outbound publish failed, sending directly: %s", e)

    if not sent_via_kafka:
        try:
            if channel == "whatsapp":
                phone = (metadata or {}).get("phone", "")
                if phone:
                    from production.channels.whatsapp_handler import TwilioWhatsAppClient
                    client = TwilioWhatsAppClient()
                    await client.send_reply(phone, response_text)
                    logger.info("WhatsApp reply sent directly to %s", phone)
            elif channel == "gmail":
                email_addr = (metadata or {}).get("email", "")
                if email_addr:
                    from production.channels.gmail_handler import GmailClient
                    client = GmailClient()
                    await client.send_reply(email_addr, response_text)
                    logger.info("Gmail reply sent directly to %s", email_addr)
        except Exception as de:
            logger.error("Direct channel delivery failed: %s", de)

    # Resolve ticket if sentiment is non-negative
    if sentiment_score >= 0.3:
        await repositories.update_ticket_status(ticket_id, "resolved")

        # T063: Trigger learning loop on resolution
        try:
            from production.workers.learning_loop import maybe_learn_from_ticket
            await maybe_learn_from_ticket(ticket_id)
        except Exception as e:
            logger.debug("Learning loop skipped: %s", e)

    # Store outbound message
    try:
        conv = await repositories.get_active_conversation(cid)
        if conv:
            await repositories.create_message(
                conversation_id=conv["id"],
                direction="outbound",
                channel=channel,
                content=response_text,
                ticket_id=ticket_id,
            )
    except Exception as e:
        logger.warning("Failed to store outbound message: %s", e)

    # Record metric
    await repositories.create_agent_metric(
        ticket_id=ticket_id,
        channel=channel,
        escalated=False,
        sentiment_score=sentiment_score,
        kb_results_count=len(kb_results.split("\n\n")) if kb_results else 0,
        workflow_steps=workflow_steps,
    )

    workflow_steps.append("send_response")
    return {
        "action": "responded",
        "ticket_id": str(ticket_id),
        "response": response_text,
        "sentiment": sentiment_score,
        "workflow_steps": workflow_steps,
    }
