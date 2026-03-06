# Customer Success Digital FTE

24/7 AI-powered Customer Success agent built for **StreamLine SaaS** — handles customer inquiries across **Web Form**, **Gmail**, and **WhatsApp** with cross-channel identity resolution, semantic knowledge base search, real-time sentiment analysis, and intelligent guardrail-based escalation.

> **Cost**: ~$85/month infrastructure vs $75,000/year human FTE = **98.6% cost reduction**

## What It Does

A customer sends a support message (via web form, email, or WhatsApp) and the system automatically:

1. **Creates a ticket** in the self-built CRM (zero external dependencies)
2. **Retrieves customer history** across all channels (cross-channel identity)
3. **Searches the knowledge base** using semantic similarity (pgvector cosine search)
4. **Analyzes sentiment** in real-time (0.0–1.0 scoring)
5. **Checks guardrails** (pricing, legal, competitor mentions, angry customers)
6. **Sends a channel-appropriate response** (formal for email, casual for WhatsApp, semi-formal for web)
7. **Escalates to a human** when guardrails trigger — with full context, history, and sentiment scores
8. **Learns from resolved tickets** — automatically adds successful Q&A pairs back into the knowledge base

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Groq (free) — `llama-3.1-8b-instant` via OpenAI-compatible API |
| **Agent Framework** | OpenAI Agents SDK (`@function_tool` decorators) |
| **Embeddings** | Local `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dims) — no API key needed |
| **Backend** | FastAPI (Python 3.11) with async/await |
| **Database** | PostgreSQL 16 + pgvector (Neon serverless or local) |
| **Message Queue** | Apache Kafka (KRaft mode, no Zookeeper) |
| **Frontend** | Next.js 14 (React, TypeScript, Zod validation) |
| **Email** | Gmail SMTP/IMAP with App Password auth |
| **WhatsApp** | Twilio WhatsApp Business API |
| **Deployment** | Docker Compose + Kubernetes manifests |

## Architecture

```
Customer Channels                    Processing Pipeline
==================                   ===================

Web Form  --> POST /api/support ──┐
Gmail     --> IMAP Poller (15s)  ──┼──> Kafka: inbound-messages ──> Agent Workflow
WhatsApp  --> POST /webhooks/wa  ──┘         |                         |
                                             |                    ┌────┴────┐
                                             |                 Respond   Escalate
                                             |                    |         |
                                             |              outbound    escalations
                                             |              (topic)     (topic)
                                             |                    |         |
                                             └── PostgreSQL <─────┘─────────┘
                                                  (pgvector)
                                                     |
                                              Learning Loop
                                          (resolved tickets --> KB)
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Free Groq API key ([console.groq.com](https://console.groq.com))
- PostgreSQL with pgvector (or use [Neon](https://neon.tech) — free tier)
- Apache Kafka (optional — system falls back to synchronous processing without it)

### 1. Clone and Configure

```bash
git clone <repo-url> && cd Hackathone-05
cp .env.example .env
```

Edit `.env` with your keys:

```env
# Required
GROQ_API_KEY=gsk_your-groq-api-key
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional (for Gmail channel)
GMAIL_EMAIL=support@yourcompany.com
GMAIL_APP_PASSWORD=your-app-password

# Optional (for WhatsApp channel)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### 2. Install Dependencies

```bash
# Backend
pip install -r production/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### 3. Set Up Database

**Option A: Neon (recommended, free)**
- Create a project at [neon.tech](https://neon.tech)
- Enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`
- Run schema and seed:

```bash
psql $DATABASE_URL -f production/database/schema.sql
psql $DATABASE_URL -f production/database/seed.sql
```

**Option B: Local PostgreSQL**

```bash
createdb fte_crm
psql -d fte_crm -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d fte_crm -f production/database/schema.sql
psql -d fte_crm -f production/database/seed.sql
```

### 4. Start the Backend

```bash
uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify: `curl http://localhost:8000/health`

### 5. Start the Frontend

```bash
cd frontend
npm run dev
```

- Support form: [http://localhost:3000](http://localhost:3000)
- Admin dashboard: [http://localhost:3000/admin](http://localhost:3000/admin)

### 6. Start Workers (Optional — requires Kafka)

```bash
# Message processor (Kafka consumer for inbound messages)
python -m production.workers.message_processor

# Outbound sender (delivers responses to Gmail/WhatsApp with retry)
python -m production.workers.outbound_sender

# Gmail poller (checks inbox every 15s)
python -m production.workers.gmail_poller
```

> Without Kafka, web form submissions are processed synchronously via direct agent call.

## Docker Compose (Full Stack)

```bash
docker-compose up -d
```

Starts all services:
- **PostgreSQL** (pgvector, auto-runs schema + seed)
- **Kafka** (KRaft mode, single broker)
- **API** (FastAPI on port 8000)
- **Worker** (Kafka message processor)
- **Outbound Sender** (response delivery with retry)
- **Frontend** (Next.js on port 3000)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/support` | Submit web form support request |
| `GET` | `/api/support/{id}/status` | Poll ticket status and response |
| `POST` | `/webhooks/gmail` | Gmail Pub/Sub push notification |
| `POST` | `/webhooks/whatsapp` | Twilio WhatsApp webhook |
| `GET` | `/api/reports/daily` | Daily sentiment and metrics report |
| `GET` | `/health` | Health check (DB, Kafka, Gmail, Twilio) |
| `GET` | `/api/admin/pending-approvals` | List tickets awaiting approval |
| `POST` | `/api/admin/approve/{id}` | Approve AI response for delivery |
| `POST` | `/api/admin/reject/{id}` | Reject AI response |
| `GET` | `/api/admin/tickets` | List all tickets (filterable by status) |
| `GET` | `/api/admin/stats` | Dashboard statistics |

## Agent Tools (7 Total — Dual MCP + Production)

Every tool exists in both **MCP Server** (incubation) and **OpenAI Agents SDK** (production) format:

| Tool | Purpose |
|------|---------|
| `create_ticket` | Create support ticket in CRM (status: open) |
| `get_customer_history` | Retrieve full cross-channel conversation history |
| `search_knowledge_base` | Semantic similarity search via pgvector (top 5 results) |
| `analyze_sentiment` | Real-time sentiment scoring (0.0–1.0) via Groq LLM |
| `send_response` | Send channel-formatted response with tone/length rules |
| `escalate_to_human` | Trigger human handoff with ticket, reason, context |
| `generate_daily_report` | Generate daily sentiment/metrics/escalation report |

### Strict Workflow Order (Constitution Principle III)

Every message follows this exact sequence — enforced programmatically, no exceptions:

```
analyze_sentiment → create_ticket → get_customer_history → search_knowledge_base → guardrail_check → send_response | escalate
```

## Guardrails (G1–G9)

| ID | Trigger | Action |
|----|---------|--------|
| G1 | Pricing keywords (`price`, `refund`, `billing`, `cost`, `discount`) | Escalate immediately, no AI response |
| G2 | Legal keywords (`lawyer`, `sue`, `legal`, `lawsuit`, `court`) | Escalate immediately with full context |
| G3 | Competitor brand names (Asana, Trello, Jira, etc.) | Escalate — no comparison or opinion |
| G5 | Angry customer (sentiment < 0.3 or trigger words `human`, `agent`, `manager`) | Escalate with empathy message |
| G6 | Ticket-first mandate | Always create ticket before any processing |
| G7 | Channel length limits | Gmail: 500 words max, WhatsApp: 300 chars (auto-split) |
| G8 | Channel tone enforcement | Gmail: formal, WhatsApp: conversational, Web: semi-formal |
| G9 | Sentiment-before-close | Block ticket closure if last sentiment is negative |

## Channel Formatting

| Channel | Tone | Max Length | Extras |
|---------|------|-----------|--------|
| Gmail | Formal | 500 words | Greeting + signature from config |
| WhatsApp | Conversational | 300 chars | Auto-split at sentence boundaries, 500ms delay |
| Web Form | Semi-formal | No limit | Response displayed on-screen + email fallback |

## Database Schema

8 tables in PostgreSQL with pgvector:

| Table | Purpose |
|-------|---------|
| `customers` | Customer profiles with metadata |
| `customer_identifiers` | Cross-channel identity mapping (email, phone, session) |
| `conversations` | Message threads spanning multiple channels |
| `messages` | All inbound/outbound messages with sentiment scores |
| `tickets` | Support tickets with full lifecycle tracking |
| `knowledge_base` | Searchable KB with vector embeddings (384 dims) |
| `channel_configs` | Per-channel tone, length limits, templates |
| `agent_metrics` | Performance tracking (response time, escalation, accuracy) |

### Ticket Lifecycle

```
open → in-progress → resolved → closed (auto after 24h)
         ↓                         ↑
      escalated → resolved ────────┘
         (human)              G9 blocks if sentiment negative
```

## Admin Dashboard

Access at [http://localhost:3000/admin](http://localhost:3000/admin):

- View pending approval queue (Gmail/WhatsApp responses require admin approval)
- Approve or reject AI-generated responses before delivery
- Browse all tickets with status filtering
- Dashboard stats: total, pending, resolved, escalated, channel breakdown

## Running Tests

```bash
# All tests
pytest production/tests/ -v

# Transition tests (guardrails, workflow order, channel limits, cross-channel)
pytest production/tests/transition/ -v

# Integration tests (full E2E per channel)
pytest production/tests/integration/ -v

# Chaos test (24h stress test with pod kills)
python -m production.tests.chaos.chaos_runner
```

### Test Coverage

- **Transition tests**: Pricing guardrail, angry escalation, channel length limits, tool order, cross-channel continuity, 10+ edge cases
- **Integration tests**: Web form E2E, Gmail E2E, WhatsApp E2E, cross-channel E2E
- **Chaos tests**: 200+ messages, pod kills every 2h, metrics collection

## Workers

| Worker | Command | Purpose |
|--------|---------|---------|
| Message Processor | `python -m production.workers.message_processor` | Kafka consumer for inbound messages |
| Outbound Sender | `python -m production.workers.outbound_sender` | Deliver responses with exponential backoff (1s→4s→16s) |
| Gmail Poller | `python -m production.workers.gmail_poller` | Poll Gmail inbox every 15s via IMAP |
| Escalation Handler | `python -m production.workers.escalation_handler` | Log and track escalations |
| Ticket Closer | `python -m production.workers.ticket_closer` | Auto-close resolved tickets after 24h (G9 check) |
| Report Generator | `python -m production.workers.report_generator` | Daily sentiment/metrics reports |
| Learning Loop | Triggered on ticket resolution | Auto-add resolved Q&A to knowledge base |

## Project Structure

```
Hackathone-05/
├── production/
│   ├── agent/                # AI agent, 7 tools, guardrails, LLM client
│   │   ├── agent.py          # Main agent with strict workflow enforcement
│   │   ├── guardrails.py     # G1-G9 guardrail checks
│   │   ├── system_prompt.txt  # Agent system prompt
│   │   ├── llm_client.py     # Groq LLM + local embeddings client
│   │   └── tools/            # 7 @function_tool implementations
│   ├── api/                  # FastAPI application
│   │   ├── main.py           # App entry point, CORS, lifespan
│   │   ├── routes/           # webhooks, reports, admin, health
│   │   ├── services/         # Identity resolver
│   │   └── middleware/       # Structured JSON logging
│   ├── channels/             # Channel handlers
│   │   ├── gmail_handler.py  # SMTP/IMAP with App Password
│   │   ├── whatsapp_handler.py  # Twilio + auto-split
│   │   └── webform_handler.py   # Form processing + Kafka publish
│   ├── database/             # Data layer
│   │   ├── schema.sql        # 8 tables with pgvector
│   │   ├── seed.sql          # 20+ KB entries + channel configs
│   │   ├── connection.py     # asyncpg connection pool
│   │   ├── models.py         # Pydantic models for all entities
│   │   └── repositories.py   # Async CRUD operations
│   ├── workers/              # Background processors
│   │   ├── message_processor.py  # Kafka inbound consumer
│   │   ├── outbound_sender.py    # Response delivery with retry
│   │   ├── gmail_poller.py       # IMAP polling loop
│   │   ├── escalation_handler.py # Escalation logging
│   │   ├── ticket_closer.py      # Auto-close with G9 check
│   │   ├── report_generator.py   # Daily reports
│   │   ├── learning_loop.py      # KB auto-learning
│   │   └── kafka_config.py       # Producer/consumer setup
│   ├── tests/
│   │   ├── transition/       # 6 transition test suites
│   │   ├── integration/      # 4 integration test suites
│   │   └── chaos/            # Chaos engineering (stress + pod kills)
│   ├── k8s/                  # 9 Kubernetes manifests
│   ├── docs/                 # Runbook, deployment guide, test plan
│   ├── Dockerfile            # Multi-stage Python 3.11-slim
│   └── requirements.txt
├── incubation/
│   └── mcp_server/           # MCP Server with all 7 tools (incubation stage)
├── frontend/                 # Next.js 14
│   └── src/
│       ├── app/
│       │   ├── page.tsx      # Support form page
│       │   └── admin/page.tsx  # Admin dashboard
│       ├── components/       # SupportForm, ResponseDisplay, StatusIndicator, etc.
│       └── lib/api.ts        # Typed API client
├── context/                  # Company profile, product docs, escalation rules
├── specs/                    # Feature specs, plan, tasks (110 tasks, all complete)
├── docker-compose.yml        # Full stack: Postgres, Kafka, API, Worker, Frontend
├── .env.example
└── CLAUDE.md
```

## Key Design Decisions

- **Zero external CRM** — fully self-contained PostgreSQL database (no Salesforce, no HubSpot)
- **Cross-channel identity** — exact match on email/phone via `customer_identifiers` table
- **Programmatic workflow enforcement** — tool order is enforced in code, not just in the prompt
- **Graceful degradation** — works without Kafka (sync fallback), without Gmail, without Twilio
- **Free LLM** — Groq API (no cost) for response generation and sentiment analysis
- **Local embeddings** — `sentence-transformers` runs locally, no embedding API costs
- **Admin approval gate** — Gmail/WhatsApp responses require admin approval before delivery
- **Learning loop** — resolved tickets with positive sentiment auto-generate KB entries
- **Dual tool architecture** — all 7 tools exist as both MCP (incubation) and production versions

## Kubernetes Deployment

```bash
kubectl apply -f production/k8s/namespace.yaml
kubectl apply -f production/k8s/
```

See [production/docs/k8s_deployment_guide.md](production/docs/k8s_deployment_guide.md) for full instructions.

Manifests include: namespace, API deployment (2 replicas), worker deployment, Kafka StatefulSet, PostgreSQL StatefulSet, services, ConfigMap, Secrets template, and HPA (auto-scale 2–5 pods at 70% CPU).

## Documentation

| Document | Path |
|----------|------|
| Operational Runbook | [production/docs/runbook.md](production/docs/runbook.md) |
| Channel Handlers Guide | [production/docs/channel_handlers_overview.md](production/docs/channel_handlers_overview.md) |
| K8s Deployment Guide | [production/docs/k8s_deployment_guide.md](production/docs/k8s_deployment_guide.md) |
| 24-Hour Test Plan | [production/docs/24_hour_test_plan.md](production/docs/24_hour_test_plan.md) |
| Transition Checklist | [production/docs/transition_checklist.md](production/docs/transition_checklist.md) |
| Feature Spec | [specs/001-customer-success-fte/spec.md](specs/001-customer-success-fte/spec.md) |
| Architecture Plan | [specs/001-customer-success-fte/plan.md](specs/001-customer-success-fte/plan.md) |
| Task Tracker (110 tasks) | [specs/001-customer-success-fte/tasks.md](specs/001-customer-success-fte/tasks.md) |

## License

MIT
