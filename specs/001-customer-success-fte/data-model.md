# Data Model: Customer Success Digital FTE

**Date**: 2026-02-23 | **Plan**: [plan.md](./plan.md)

## Entity Relationship Diagram

```
customers 1──* customer_identifiers
customers 1──* conversations
conversations 1──* messages
messages *──1 tickets
tickets *──1 customers
knowledge_base (standalone, grows via learning loop)
channel_configs (standalone, per-channel settings)
agent_metrics (standalone, per-interaction tracking)
```

## Entities

### customers

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Unique customer identifier |
| name | VARCHAR(255) | NOT NULL | Customer display name |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Record creation |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | Last modification |
| metadata | JSONB | default '{}' | Extensible customer data |

### customer_identifiers

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Unique identifier record |
| customer_id | UUID | FK→customers.id, NOT NULL | Parent customer |
| identifier_type | VARCHAR(20) | NOT NULL, CHECK IN ('email','phone','form_session') | Channel type |
| identifier_value | VARCHAR(255) | NOT NULL | The actual email/phone/session ID |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | When linked |

**Unique constraint**: (identifier_type, identifier_value) — one identity maps to one customer.

### conversations

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Conversation thread ID |
| customer_id | UUID | FK→customers.id, NOT NULL | Owner customer |
| subject | VARCHAR(500) | | Topic summary |
| started_at | TIMESTAMPTZ | NOT NULL, default now() | Thread start |
| last_activity_at | TIMESTAMPTZ | NOT NULL, default now() | Last message time |
| status | VARCHAR(20) | NOT NULL, default 'active' | active / archived |

### messages

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Message ID |
| conversation_id | UUID | FK→conversations.id, NOT NULL | Parent thread |
| ticket_id | UUID | FK→tickets.id | Associated ticket |
| direction | VARCHAR(10) | NOT NULL, CHECK IN ('inbound','outbound') | Message direction |
| channel | VARCHAR(20) | NOT NULL, CHECK IN ('gmail','whatsapp','webform') | Source channel |
| content | TEXT | NOT NULL | Message body |
| sentiment_score | FLOAT | CHECK 0.0–1.0 | Sentiment analysis result |
| metadata | JSONB | default '{}' | Channel-specific metadata |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Message timestamp |

### tickets

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Ticket ID |
| customer_id | UUID | FK→customers.id, NOT NULL | Ticket owner |
| conversation_id | UUID | FK→conversations.id | Parent conversation |
| channel | VARCHAR(20) | NOT NULL | Originating channel |
| issue | TEXT | NOT NULL | Customer issue description |
| priority | VARCHAR(10) | NOT NULL, default 'medium' | low/medium/high/urgent |
| status | VARCHAR(20) | NOT NULL, default 'open' | Lifecycle state |
| escalation_reason | TEXT | | Why escalated (if applicable) |
| resolved_at | TIMESTAMPTZ | | When resolved |
| closed_at | TIMESTAMPTZ | | When auto-closed |
| metadata | JSONB | default '{}' | Channel metadata |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Ticket creation |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() | Last update |

**Status values**: open → in-progress → resolved → closed | escalated
**Lifecycle**: Per spec clarification — automatic transitions with G9 sentiment-before-close.

### knowledge_base

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Entry ID |
| title | VARCHAR(500) | NOT NULL | Q&A title or article name |
| content | TEXT | NOT NULL | Full answer/article body |
| category | VARCHAR(100) | | Issue category for grouping |
| embedding | VECTOR(1536) | NOT NULL | text-embedding-3-small vector |
| source | VARCHAR(20) | NOT NULL, default 'seed' | seed / learned |
| source_ticket_id | UUID | FK→tickets.id | If learned, source ticket |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Entry creation |

**Index**: IVFFlat on embedding with cosine similarity, lists=100.

### channel_configs

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Config ID |
| channel | VARCHAR(20) | UNIQUE, NOT NULL | gmail/whatsapp/webform |
| tone | VARCHAR(20) | NOT NULL | formal/conversational/semi-formal |
| max_length | INTEGER | NOT NULL | Word limit (Gmail) or char limit (WhatsApp) |
| greeting_template | TEXT | | Channel-specific greeting |
| signature_template | TEXT | | Channel-specific signature |
| api_config | JSONB | NOT NULL, default '{}' | API credentials reference (key names only) |
| is_active | BOOLEAN | NOT NULL, default true | Channel enabled flag |

### agent_metrics

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default gen | Metric record ID |
| ticket_id | UUID | FK→tickets.id, NOT NULL | Associated ticket |
| channel | VARCHAR(20) | NOT NULL | Channel of interaction |
| response_time_ms | INTEGER | | Time from receive to respond |
| workflow_steps | JSONB | | Ordered list of steps executed |
| escalated | BOOLEAN | NOT NULL, default false | Was this escalated? |
| escalation_reason | VARCHAR(255) | | Guardrail that triggered |
| kb_results_count | INTEGER | | Knowledge base hits |
| kb_relevant | BOOLEAN | | Was KB answer relevant? |
| sentiment_score | FLOAT | | Final customer sentiment |
| created_at | TIMESTAMPTZ | NOT NULL, default now() | Metric timestamp |

## Key Indexes

- `customer_identifiers`: UNIQUE(identifier_type, identifier_value), INDEX(customer_id)
- `messages`: INDEX(conversation_id, created_at), INDEX(ticket_id)
- `tickets`: INDEX(customer_id, status), INDEX(status, created_at)
- `knowledge_base`: IVFFlat(embedding vector_cosine_ops, lists=100), INDEX(category)
- `agent_metrics`: INDEX(ticket_id), INDEX(created_at)

## State Machine: Ticket Lifecycle

```
        ┌───────────┐
        │   open    │  (create_ticket)
        └─────┬─────┘
              │ workflow begins
              ▼
        ┌───────────┐
        │in-progress│  (get_history + search_kb)
        └─────┬─────┘
              │
     ┌────────┴────────┐
     │                 │
     ▼                 ▼
┌──────────┐    ┌───────────┐
│escalated │    │ resolved  │  (successful response + sentiment >= 0.3)
│(G1-G5)   │    └─────┬─────┘
└─────┬────┘          │ 24h no reply + sentiment check (G9)
      │               ▼
      │         ┌───────────┐
      │         │  closed   │
      │         └───────────┘
      │
      ▼
  Human resolves → resolved → closed
```
