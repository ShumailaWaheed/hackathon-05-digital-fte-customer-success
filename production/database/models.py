"""Pydantic models for all 8 CRM entities.

Maps directly to data-model.md and production/database/schema.sql.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- Enums ---

class IdentifierType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    FORM_SESSION = "form_session"


class ChannelType(str, Enum):
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    WEBFORM = "webform"


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    DELIVERY_FAILED = "delivery-failed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ToneType(str, Enum):
    FORMAL = "formal"
    CONVERSATIONAL = "conversational"
    SEMI_FORMAL = "semi-formal"


class KBSource(str, Enum):
    SEED = "seed"
    LEARNED = "learned"


# --- Models ---

class Customer(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomerIdentifier(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    customer_id: uuid.UUID
    identifier_type: IdentifierType
    identifier_value: str = Field(..., max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    customer_id: uuid.UUID
    subject: str | None = Field(default=None, max_length=500)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)
    status: ConversationStatus = ConversationStatus.ACTIVE


class Message(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: uuid.UUID
    ticket_id: uuid.UUID | None = None
    direction: MessageDirection
    channel: ChannelType
    content: str
    sentiment_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("sentiment_score")
    @classmethod
    def validate_sentiment(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("sentiment_score must be between 0.0 and 1.0")
        return v


class Ticket(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    customer_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    channel: ChannelType
    issue: str
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    escalation_reason: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeBaseEntry(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str = Field(..., max_length=500)
    content: str
    category: str | None = Field(default=None, max_length=100)
    embedding: list[float] = Field(..., min_length=1536, max_length=1536)
    source: KBSource = KBSource.SEED
    source_ticket_id: uuid.UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChannelConfig(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    channel: ChannelType
    tone: ToneType
    max_length: int
    greeting_template: str | None = None
    signature_template: str | None = None
    api_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AgentMetric(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    ticket_id: uuid.UUID
    channel: ChannelType
    response_time_ms: int | None = None
    workflow_steps: list[str] | None = None
    escalated: bool = False
    escalation_reason: str | None = None
    kb_results_count: int | None = None
    kb_relevant: bool | None = None
    sentiment_score: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
