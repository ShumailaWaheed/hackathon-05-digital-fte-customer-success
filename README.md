# Customer Success Digital FTE

24/7 AI-powered Customer Success agent with omnichannel support. Handles customer inquiries across **Web Form**, **Gmail**, and **WhatsApp** channels with cross-channel identity resolution, semantic knowledge base search, sentiment analysis, and intelligent escalation.

## What It Does

A customer sends a support message (via web form, email, or WhatsApp) and the system automatically:

1. **Creates a ticket** in the built-in CRM
2. **Retrieves customer history** across all channels
3. **Searches the knowledge base** using semantic similarity (pgvector)
4. **Analyzes sentiment** in real-time
5. **Checks guardrails** (pricing, legal, competitor mentions, angry customers)
6. **Sends a response** tailored to the channel's tone (formal for email, casual for WhatsApp)
7. **Escalates to a human** when guardrails trigger

The system learns from resolved tickets — the learning loop automatically adds successful resolutions back into the knowledge base.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Groq (free) — `llama-3.1-8b-instant` via OpenAI-compatible API |
| **Embeddings** | Local `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dims) — no API key needed |
| **Backend** | FastAPI + OpenAI Agents SDK (`@function_tool`) |
| **Database** | PostgreSQL + pgvector (Neon serverless or local) |
| **Message Queue** | Apache Kafka (KRaft mode, no Zookeeper) |
| **Frontend** | Next.js (embeddable support form) |
| **Channels** | Gmail API, Twilio WhatsApp, Web Form |
| **Deployment** | Docker + Kubernetes manifests |

## Architecture

```
Web Form  --> POST /api/support ──┐
Gmail     --> Poller (15s)       ──┼──> Kafka: inbound-messages ──> Agent Workflow
WhatsApp  --> POST /webhooks/wa  ──┘         |                         |
                                             |                    ┌────┴────┐
                                             |                 Respond   Escalate
                                             |                    |         |
                                             |              outbound    escalations
                                             |              (topic)     (topic)
                                             |                    |         |
                                             └── PostgreSQL <─────┘─────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Free Groq API key ([console.groq.com](https://console.groq.com))
- PostgreSQL with pgvector (or use [Neon](https://neon.tech) — free tier)
- Apache Kafka (optional — system runs without it)

### 1. Clone and Configure

```bash
git clone <repo-url> && cd Hackathone-05
cp .env.example .env
```

Edit `.env` with your keys:

```env
# Required
GROQ_API_KEY=gsk_your-groq-api-key
DATABASE_URL=postgresql://user:pass@host:5432/dbname?sslmode=require

# Optional (for Gmail/WhatsApp channels)
GMAIL_CREDENTIALS_PATH=./credentials/gmail-service-account.json
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
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

Open [http://localhost:3000](http://localhost:3000) to see the support form.

### 6. Start Workers (Optional)

Workers require Kafka. If Kafka is not running, the API still works for web form submissions.

```bash
# Message processor
python -m production.workers.message_processor

# Outbound sender
python -m production.workers.outbound_sender

# Gmail poller (requires Gmail API credentials)
python -m production.workers.gmail_poller
```

## Docker Compose

```bash
docker-compose up -d
```

Starts PostgreSQL (with pgvector + schema + seed), Kafka (KRaft), FastAPI API, Workers, and the Next.js frontend.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/support` | Submit a web form support request |
| `GET` | `/api/support/{id}/status` | Poll ticket status |
| `POST` | `/webhooks/gmail` | Gmail Pub/Sub push notification |
| `POST` | `/webhooks/whatsapp` | Twilio WhatsApp webhook |
| `GET` | `/api/reports/daily` | Daily sentiment and metrics report |
| `GET` | `/health` | Health check (DB + Kafka status) |

## Agent Tools (7 total)

| Tool | Purpose |
|------|---------|
| `create_ticket` | Create a support ticket in the CRM |
| `get_customer_history` | Retrieve cross-channel conversation history |
| `search_knowledge_base` | Semantic search using pgvector embeddings |
| `analyze_sentiment` | Real-time sentiment scoring via Groq LLM |
| `send_response` | Send channel-appropriate response |
| `escalate_to_human` | Trigger human handoff with context |
| `update_ticket` | Update ticket status/priority |

## Guardrails (G1-G9)

| ID | Trigger | Action |
|----|---------|--------|
| G1 | Pricing/refund keywords | Escalate immediately |
| G2 | Legal/compliance terms | Escalate immediately |
| G3 | Competitor mentions | Escalate (no comparison) |
| G5 | Angry customer (sentiment < 0.3) | Escalate with empathy |
| G9 | Low sentiment at close | Prevent auto-close |

## Database Schema

8 tables in PostgreSQL with pgvector:

- `customers` — Customer profiles
- `customer_identifiers` — Cross-channel identity (email, phone, session)
- `tickets` — Support tickets with status tracking
- `messages` — All messages across channels
- `knowledge_base` — Searchable KB with vector embeddings (384 dims)
- `channel_configs` — Per-channel settings and tone
- `escalations` — Human handoff records
- `daily_reports` — Aggregated metrics and sentiment

## Running Tests

```bash
# All tests
pytest production/tests/ -v

# Transition tests only
pytest production/tests/transition/ -v

# Integration tests only
pytest production/tests/integration/ -v
```

## Project Structure

```
Hackathone-05/
├── production/
│   ├── agent/           # AI agent, tools, guardrails, LLM client
│   ├── api/             # FastAPI routes, middleware
│   ├── channels/        # Gmail, WhatsApp, WebForm adapters
│   ├── database/        # Schema, seeds, connection pool
│   ├── workers/         # Kafka consumers, pollers, learning loop
│   ├── tests/           # Transition + integration tests
│   ├── k8s/             # Kubernetes manifests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # Next.js embeddable support form
├── docker-compose.yml
├── .env.example
└── specs/               # Feature specs, plans, tasks
```

## Key Features

- **Zero external CRM** — fully self-contained PostgreSQL database
- **Cross-channel identity** — recognizes customers across web, email, WhatsApp
- **Semantic search** — pgvector embeddings for knowledge base matching
- **Free LLM** — Groq API (no cost) + local embeddings (no API key)
- **Graceful degradation** — works without Kafka, Gmail, or Twilio configured
- **Learning loop** — auto-generates KB entries from resolved tickets
- **Strict workflow** — enforced tool execution order on every message
- **60 tests** — transition + integration test coverage

## License

MIT
