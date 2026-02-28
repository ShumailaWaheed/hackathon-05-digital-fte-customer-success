# Quickstart: Customer Success Digital FTE

**Time to first run**: ~10 minutes (Docker) or ~15 minutes (manual)

## Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.11+, Node.js 18+, PostgreSQL 16, Kafka
- OpenAI API key
- Gmail API credentials (OAuth2 service account JSON) — for email channel
- Twilio account SID + auth token + WhatsApp sandbox — for WhatsApp channel

## Option A: Docker Compose (Recommended)

### 1. Configure Environment

```bash
git clone <repo-url> && cd Hackathone-05
cp .env.example .env
# Edit .env with your API keys (at minimum OPENAI_API_KEY)
```

### 2. Start Everything

```bash
docker-compose up -d
```

This starts: PostgreSQL (with pgvector + schema + seed data), Kafka (KRaft), FastAPI API, Message Processor Worker, Next.js Frontend.

### 3. Verify

```bash
# Wait ~30s for services to initialize, then:
curl http://localhost:8000/health | python -m json.tool

# Open web form
# http://localhost:3000
```

### 4. Test

```bash
# Submit a test request via API
curl -X POST http://localhost:8000/api/support \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "category": "general-question",
    "message": "How do I reset my password?"
  }'

# Poll for response (replace TICKET_ID from above response)
curl http://localhost:8000/api/support/TICKET_ID/status | python -m json.tool

# Get daily report
curl http://localhost:8000/api/reports/daily | python -m json.tool
```

## Option B: Manual Setup

### 1. Clone and Configure

```bash
git clone <repo-url> && cd Hackathone-05
cp .env.example .env
# Edit .env with your API keys
```

### Required Environment Variables

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://fte_user:fte_pass@localhost:5432/fte_crm
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
GMAIL_CREDENTIALS_PATH=./credentials/gmail-service-account.json
GMAIL_DELEGATED_USER=support@yourcompany.com
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL and Kafka (or use docker-compose for just infra)
docker-compose up -d postgres kafka
# Wait ~30s for services to be ready
```

### 3. Initialize Database

```bash
docker-compose exec postgres psql -U fte_user -d fte_crm \
  -f /docker-entrypoint-initdb.d/schema.sql
docker-compose exec postgres psql -U fte_user -d fte_crm \
  -f /docker-entrypoint-initdb.d/seed.sql
```

### 4. Start Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1: FastAPI server
uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Message processor (Kafka consumer)
python -m production.workers.message_processor

# Terminal 3: Outbound sender (Kafka consumer)
python -m production.workers.outbound_sender

# Terminal 4 (optional): Gmail poller
python -m production.workers.gmail_poller

# Terminal 5 (optional): Escalation handler
python -m production.workers.escalation_handler
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

## Run Tests

```bash
# Unit + transition tests
pytest production/tests/transition/ -v

# Integration tests
pytest production/tests/integration/ -v

# All tests
pytest production/tests/ -v
```

## Architecture Quick Reference

```
Web Form → POST /api/support ──┐
Gmail    → Poller (15s)       ──┼──→ Kafka: inbound-messages ──→ Agent Workflow
WhatsApp → POST /webhooks/wa  ──┘         │                         │
                                           │                    ┌────┴────┐
                                           │                 Respond   Escalate
                                           │                    │         │
                                           │              outbound    escalations
                                           │              Kafka topic  Kafka topic
                                           │                    │         │
                                           └── PostgreSQL ◄─────┘─────────┘
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/support` | Submit web form |
| GET | `/api/support/{id}/status` | Poll ticket status |
| POST | `/webhooks/gmail` | Gmail Pub/Sub push |
| POST | `/webhooks/whatsapp` | Twilio WhatsApp webhook |
| GET | `/api/reports/daily` | Daily sentiment report |
| GET | `/health` | Health check (DB + Kafka) |

## Workers

| Worker | Command | Purpose |
|--------|---------|---------|
| Message Processor | `python -m production.workers.message_processor` | Process inbound messages |
| Outbound Sender | `python -m production.workers.outbound_sender` | Send responses per channel |
| Gmail Poller | `python -m production.workers.gmail_poller` | Poll Gmail every 15s |
| Escalation Handler | `python -m production.workers.escalation_handler` | Log escalations |
| Ticket Closer | `python -m production.workers.ticket_closer` | Close resolved tickets (hourly) |
| Report Generator | `python -m production.workers.report_generator` | Daily reports |
| Learning Loop | Triggered on ticket resolution | Auto-learn from resolved tickets |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Kafka connection refused | Wait 30s after docker-compose up, check `docker-compose logs kafka` |
| pgvector not found | Run `CREATE EXTENSION IF NOT EXISTS vector;` in psql |
| Gmail API 403 | Enable Gmail API in Google Cloud Console, check service account permissions |
| Twilio webhook 403 | Verify TWILIO_AUTH_TOKEN, check webhook URL in Twilio console |
| OpenAI rate limit | Switch to gpt-4o-mini, add delay between API calls |
| Frontend can't reach API | Check CORS_ORIGINS includes http://localhost:3000 |
| No KB results | Run seed.sql to populate knowledge_base, or check embeddings |
