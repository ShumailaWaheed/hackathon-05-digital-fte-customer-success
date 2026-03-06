-- Customer Success Digital FTE — Database Schema
-- PostgreSQL 16 + pgvector
-- Constitution v1.1.0 Principle I: Own CRM — Zero External Dependencies

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- Core CRM Tables
-- ============================================================

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE customer_identifiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type VARCHAR(20) NOT NULL CHECK (identifier_type IN ('email', 'phone', 'form_session')),
    identifier_value VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (identifier_type, identifier_value)
);

CREATE INDEX idx_customer_identifiers_customer ON customer_identifiers(customer_id);

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    subject VARCHAR(500),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived'))
);

CREATE INDEX idx_conversations_customer ON conversations(customer_id);

CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('gmail', 'whatsapp', 'webform')),
    issue TEXT NOT NULL,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in-progress', 'escalated', 'resolved', 'closed', 'delivery-failed', 'pending_approval')),
    escalation_reason TEXT,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tickets_customer_status ON tickets(customer_id, status);
CREATE INDEX idx_tickets_status_created ON tickets(status, created_at);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    ticket_id UUID REFERENCES tickets(id),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('gmail', 'whatsapp', 'webform')),
    content TEXT NOT NULL,
    sentiment_score FLOAT CHECK (sentiment_score >= 0.0 AND sentiment_score <= 1.0),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_ticket ON messages(ticket_id);

-- ============================================================
-- Knowledge Base (pgvector for semantic search)
-- ============================================================

CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    embedding vector(384) NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'seed' CHECK (source IN ('seed', 'learned')),
    source_ticket_id UUID REFERENCES tickets(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_knowledge_base_embedding ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);

-- ============================================================
-- Configuration & Metrics
-- ============================================================

CREATE TABLE channel_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel VARCHAR(20) UNIQUE NOT NULL CHECK (channel IN ('gmail', 'whatsapp', 'webform')),
    tone VARCHAR(20) NOT NULL CHECK (tone IN ('formal', 'conversational', 'semi-formal')),
    max_length INTEGER NOT NULL,
    greeting_template TEXT,
    signature_template TEXT,
    api_config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id),
    channel VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    workflow_steps JSONB,
    escalated BOOLEAN NOT NULL DEFAULT false,
    escalation_reason VARCHAR(255),
    kb_results_count INTEGER,
    kb_relevant BOOLEAN,
    sentiment_score FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_agent_metrics_ticket ON agent_metrics(ticket_id);
CREATE INDEX idx_agent_metrics_created ON agent_metrics(created_at);
