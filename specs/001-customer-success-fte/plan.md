# Implementation Plan: Customer Success Digital FTE

**Branch**: `main` | **Date**: 2026-02-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-customer-success-fte/spec.md`
**Constitution**: v1.1.0 (all principles enforced)

## Summary

Build a 24/7 autonomous Customer Success Digital FTE that handles
omnichannel support (Gmail, WhatsApp, Web Form) with its own PostgreSQL
CRM, strict workflow enforcement, guardrails G1–G9, sentiment analysis,
and a learning knowledge base. Development follows the Agent Maturity
Model: Incubation (Claude Code + MCP) → Transition → Specialization
(OpenAI Agents SDK + FastAPI + Kafka + Kubernetes).

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript/Next.js (web form)
**Primary Dependencies**: FastAPI, OpenAI Agents SDK, openai (embeddings),
  confluent-kafka, asyncpg, pgvector, Twilio SDK, Google API Client
**Storage**: PostgreSQL 16 + pgvector extension
**Testing**: pytest + pytest-asyncio (unit/integration/E2E), Locust (chaos)
**Target Platform**: Linux containers (Docker → Kubernetes)
**Project Type**: Web application (backend API + frontend form)
**Performance Goals**: <3s message processing, <30s response delivery,
  >85% KB accuracy, <20% escalation rate, 99.9% uptime
**Constraints**: P95 <3s, <$85/month infra cost, 3 channels concurrent
**Scale/Scope**: 200+ messages/day across 3 channels, single-tenant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Gate | Status |
|---|-----------|------|--------|
| I | Own CRM — Zero External | All 8 tables in PostgreSQL, no external CRM | PASS |
| II | Tri-Channel Mandate | Gmail + WhatsApp + Web Form all planned | PASS |
| III | Strict Workflow Order | create_ticket → get_history → search_kb → send_response enforced | PASS |
| IV | Cross-Channel Continuity | customer_identifiers table, unified identity | PASS |
| V | Guardrails & Escalation | G1–G9 all mapped to FR-014 through FR-021 | PASS |
| VI | Sentiment-Driven Intel | analyze_sentiment on every message, daily reports | PASS |
| VII | Maturity Model | 3-phase plan: Incubation → Transition → Specialization | PASS |
| VIII | Dual Tool Implementation | 7 tools × 2 forms (MCP + @function_tool) | PASS |
| IX | Production Architecture | FastAPI + Agents SDK + Kafka + PostgreSQL + K8s | PASS |
| X | Test-First & Chaos Ready | Transition tests + 24h chaos test planned | PASS |

**Result**: All gates PASS. Proceed to Phase 0.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INBOUND CHANNELS                         │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  Gmail    │    │   WhatsApp   │    │   Web Support Form    │  │
│  │  API /    │    │   Twilio     │    │   (Next.js embed)     │  │
│  │  Pub/Sub  │    │   Webhook    │    │   POST /api/support   │  │
│  └────┬─────┘    └──────┬───────┘    └──────────┬────────────┘  │
│       │                 │                        │               │
└───────┼─────────────────┼────────────────────────┼───────────────┘
        │                 │                        │
        ▼                 ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Webhook Layer                        │
│                                                                 │
│  POST /webhooks/gmail    POST /webhooks/whatsapp                │
│  POST /api/support       GET  /health                           │
│                                                                 │
│  → Normalize message → Resolve customer identity                │
│  → Publish to Kafka topic: "inbound-messages"                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Apache Kafka                                  │
│                                                                 │
│  Topics:                                                        │
│    inbound-messages    → unified ingestion from all channels     │
│    outbound-responses  → formatted replies per channel           │
│    escalations         → human handoff queue                     │
│    metrics             → agent performance events                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Kafka Worker: Message Processor                     │
│                                                                 │
│  Consumes: inbound-messages                                     │
│  Strict Workflow (Constitution III):                             │
│                                                                 │
│  1. create_ticket(customer_id, issue, priority, channel, meta)  │
│  2. get_customer_history(customer_id)                           │
│  3. search_knowledge_base(query, max_results=5)                 │
│  4. ── Guardrail Check (G1-G5) ──                               │
│     │  IF trigger → escalate_to_human(ticket_id, reason)        │
│     │  ELSE → analyze_sentiment(message) + send_response(...)   │
│  5. Publish to: outbound-responses OR escalations               │
│                                                                 │
│  Engine: OpenAI Agents SDK + @function_tool (7 tools)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Gmail Reply  │  │ WhatsApp     │  │ Web Form     │
│ (formal,     │  │ Reply        │  │ Response     │
│  500w max,   │  │ (casual,     │  │ (semi-formal │
│  greeting +  │  │  300ch pref, │  │  on-screen + │
│  signature)  │  │  auto-split) │  │  email copy) │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PostgreSQL + pgvector                           │
│                                                                 │
│  customers ──┐                                                  │
│  customer_identifiers ──┤  CRM Core                             │
│  conversations ──┤                                              │
│  messages (+ sentiment_score) ──┘                               │
│                                                                 │
│  tickets (status: open→in-progress→resolved→closed|escalated)   │
│  knowledge_base (content + embedding vector(1536))              │
│  channel_configs (tone, limits, API refs)                       │
│  agent_metrics (response_time, accuracy, escalation_reason)     │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

### Documentation

```text
specs/001-customer-success-fte/
├── spec.md              # Feature specification (done)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
│   ├── webhooks.yaml
│   ├── api.yaml
│   └── health.yaml
└── checklists/
    └── requirements.md  # Spec quality checklist (done)
```

### Source Code

```text
context/                          # Incubation Phase artifacts
├── company-profile.md
├── product-docs.md
├── sample-tickets.json           # 50+ multi-channel samples
├── escalation-rules.md
└── brand-voice.md

incubation/                       # Stage 1 - MCP prototype
├── mcp_server/
│   ├── server.py                 # MCP Server with 7 tools
│   └── tools/
│       ├── search_knowledge_base.py
│       ├── create_ticket.py
│       ├── get_customer_history.py
│       ├── escalate_to_human.py
│       ├── send_response.py
│       ├── analyze_sentiment.py
│       └── generate_daily_report.py
├── skills_manifest.json
├── tools_manifest.json
├── discovery-log.md
└── edge-cases.md                 # Min 10 documented

production/                       # Stage 2 - Specialization
├── agent/
│   ├── agent.py                  # OpenAI Agents SDK agent
│   ├── system_prompt.txt         # Strict workflow + guardrails
│   └── tools/
│       ├── search_knowledge_base.py  # @function_tool + Pydantic
│       ├── create_ticket.py
│       ├── get_customer_history.py
│       ├── escalate_to_human.py
│       ├── send_response.py
│       ├── analyze_sentiment.py
│       └── generate_daily_report.py
├── api/
│   ├── main.py                   # FastAPI app entry
│   ├── routes/
│   │   ├── webhooks.py           # Gmail + Twilio + Web Form
│   │   ├── health.py             # /health endpoint
│   │   └── reports.py            # Daily report endpoint
│   └── middleware/
│       └── logging.py            # Structured JSON logging
├── channels/
│   ├── gmail_handler.py          # Gmail API send/receive
│   ├── whatsapp_handler.py       # Twilio send/receive + split
│   └── webform_handler.py        # Form processing + email fallback
├── workers/
│   ├── message_processor.py      # Kafka consumer → agent workflow
│   ├── outbound_sender.py        # Kafka consumer → channel dispatch
│   └── report_generator.py       # Daily cron → generate_daily_report
├── database/
│   ├── schema.sql                # All tables + indexes + pgvector
│   ├── seed.sql                  # Initial knowledge base entries
│   └── connection.py             # asyncpg pool management
├── tests/
│   ├── unit/
│   │   ├── test_guardrails.py
│   │   ├── test_sentiment.py
│   │   ├── test_workflow_order.py
│   │   └── test_message_splitting.py
│   ├── integration/
│   │   ├── test_gmail_channel.py
│   │   ├── test_whatsapp_channel.py
│   │   ├── test_webform_channel.py
│   │   └── test_cross_channel.py
│   ├── transition/
│   │   ├── test_pricing_guardrail.py
│   │   ├── test_angry_escalation.py
│   │   ├── test_channel_length.py
│   │   ├── test_tool_order.py
│   │   ├── test_cross_channel_continuity.py
│   │   └── test_edge_cases.py    # 10+ edge cases
│   └── chaos/
│       ├── chaos_runner.py       # 24h test orchestrator
│       ├── message_generator.py  # Scripted multi-channel load
│       └── pod_killer.py         # K8s pod disruption script
├── k8s/
│   ├── namespace.yaml
│   ├── deployment-api.yaml
│   ├── deployment-worker.yaml
│   ├── deployment-kafka.yaml
│   ├── deployment-postgres.yaml
│   ├── service-api.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml              # Template (no real values)
│   └── hpa.yaml                  # Horizontal pod autoscaler
├── Dockerfile
├── docker-compose.yml            # Local dev: API + Kafka + PG + form
├── requirements.txt
└── docs/
    ├── runbook.md
    ├── channel_handlers_overview.md
    ├── k8s_deployment_guide.md
    ├── transition_checklist.md
    └── 24_hour_test_plan.md

frontend/                         # Web Support Form (embeddable)
├── src/
│   ├── app/
│   │   └── page.tsx              # Main form page
│   ├── components/
│   │   ├── SupportForm.tsx       # Form with validation
│   │   ├── ResponseDisplay.tsx   # On-screen response
│   │   └── StatusIndicator.tsx   # Ticket status
│   └── lib/
│       └── api.ts                # POST to /api/support
├── public/
│   └── embed.js                  # Iframe/script embed loader
├── package.json
├── tsconfig.json
└── next.config.js
```

**Structure Decision**: Web application layout — Python backend (`production/`)
with separate Next.js frontend (`frontend/`). Incubation artifacts in
`incubation/` and `context/` directories at repo root.

## Phase 1 Status Tracker (Incubation)

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | context/company-profile.md | ✅ DONE | 28 lines |
| 2 | context/product-docs.md | ✅ DONE | 69 lines, 20+ entries |
| 3 | context/escalation-rules.md | ✅ DONE | G1-G9 documented |
| 4 | context/brand-voice.md | ✅ DONE | 3 channel tones |
| 5 | context/sample-tickets.json | ❌ TODO | 50+ multi-channel needed |
| 6 | docker-compose.yml | ✅ DONE | PG+Kafka+API+Worker+Frontend |
| 7 | production/database/schema.sql | ✅ DONE | All 8 tables + indexes |
| 8 | production/database/seed.sql | ✅ DONE | 20 KB entries + channel configs |
| 9 | production/requirements.txt | ✅ DONE | All dependencies |
| 10 | production/database/connection.py | ❌ TODO | asyncpg pool |
| 11 | production/database/models.py | ❌ TODO | Pydantic models |
| 12 | production/database/repositories.py | ❌ TODO | Async CRUD |
| 13 | incubation/mcp_server/server.py | ❌ TODO | MCP entry point |
| 14 | incubation/mcp_server/tools/* (7) | ❌ TODO | All 7 MCP tools |
| 15 | incubation/skills_manifest.json | ❌ TODO | Agent skills |
| 16 | incubation/tools_manifest.json | ❌ TODO | Dual tool listing |
| 17 | incubation/discovery-log.md | ❌ TODO | Pattern discoveries |
| 18 | incubation/edge-cases.md | ❌ TODO | Min 10 cases |
| 19 | MCP prototype validation | ❌ TODO | All 3 channels in MCP |

## Phase Timeline (72 Hours)

### Phase 1 — Incubation (Hours 1–16)

| Hour | Task | Deliverable |
|------|------|-------------|
| 1–2 | Project setup: repo structure, Python env, Docker Compose (PG + Kafka) | docker-compose.yml, requirements.txt |
| 2–4 | Create `/context` folder: company-profile.md, product-docs.md, sample-tickets.json (50+), escalation-rules.md, brand-voice.md | context/*.md, context/sample-tickets.json |
| 4–6 | Exercise 1.1: Pattern discovery — analyze sample tickets with Claude Code, identify top issue categories, channel patterns, edge cases | discovery-log.md |
| 6–8 | Exercise 1.2: Core loop iteration — build basic ticket creation + KB search prototype with Claude Code | Prototype working locally |
| 8–10 | Exercise 1.3: Memory & state — implement conversation continuity, customer identity resolution, sentiment tracking | Cross-channel identity working |
| 10–13 | Exercise 1.4: Build MCP Server with all 7 tools | incubation/mcp_server/ complete |
| 13–15 | Exercise 1.5: Skills & tools manifests, edge-cases.md (min 10) | skills_manifest.json, tools_manifest.json, edge-cases.md |
| 15–16 | Validate prototype handles all 3 channels in MCP mode; finalize discovery log | All MCP tools verified |

### Phase 2 — Transition (Hours 15–20)

| Hour | Task | Deliverable |
|------|------|-------------|
| 15–16 | Crystallize discoveries → transition-checklist.md | transition_checklist.md |
| 16–17 | Convert MCP tools → OpenAI Agents SDK @function_tool with Pydantic models | production/agent/tools/*.py (7 files) |
| 17–18 | Write system_prompt.txt with strict workflow + guardrails G1–G9 | production/agent/system_prompt.txt |
| 18–19 | Build transition test suite (pricing, angry, length, order, cross-channel, 10+ edge cases) | production/tests/transition/*.py |
| 19–20 | Run and pass all transition tests | All tests GREEN |

### Phase 3 — Specialization (Hours 20–72)

| Hour | Task | Deliverable |
|------|------|-------------|
| 20–23 | Database: schema.sql (all 8 tables + indexes + pgvector), seed.sql, connection pool | production/database/*.sql, connection.py |
| 23–27 | FastAPI core: main.py, webhook routes (Gmail, Twilio, Web Form), /health endpoint, structured JSON logging middleware | production/api/ complete |
| 27–30 | Channel handlers: Gmail API send/receive, Twilio WhatsApp send/receive + auto-split, Web Form processing + email fallback | production/channels/*.py |
| 30–33 | Kafka integration: message_processor worker (strict workflow), outbound_sender worker, topic setup | production/workers/*.py |
| 33–36 | OpenAI Agent: wire agent.py with all 7 @function_tool, guardrail checks, tone adaptation per channel | production/agent/agent.py |
| 36–40 | Web Support Form: Next.js embeddable UI with validation, response display, embed script | frontend/ complete |
| 40–44 | Knowledge base: pgvector semantic search, embedding generation, learning loop (resolved tickets → new vectors) | KB search + learning working |
| 44–47 | Daily report generation, agent metrics collection | production/workers/report_generator.py |
| 47–50 | Unit tests + integration tests for all channels | production/tests/unit/, integration/ |
| 50–54 | Docker: Dockerfile, docker-compose with all services, local E2E validation | Docker stack running |
| 54–58 | Kubernetes: all manifests, HPA, configmaps, deployment guide | production/k8s/*.yaml |
| 58–62 | Documentation: runbook.md, channel_handlers_overview.md, k8s_deployment_guide.md | production/docs/*.md |
| 62–66 | 24-hour chaos test setup: message generators, pod killer, metrics collection | production/tests/chaos/*.py |
| 66–70 | Run chaos test (compressed simulation), collect metrics, generate report | tests/24h-report.md |
| 70–72 | Final validation, fix any failures, polish documentation | All deliverables complete |

## Research & Exploration Approach (Incubation)

### Director Role (Claude Code as Agent Factory)

1. **Pattern Discovery** (Hours 4–6):
   - Feed sample-tickets.json to Claude Code
   - Identify: top 10 issue categories, channel distribution,
     common customer frustrations, escalation triggers
   - Document in discovery-log.md

2. **Core Loop Iteration** (Hours 6–8):
   - Prototype the 4-step workflow locally
   - Test with real sample tickets across simulated channels
   - Record which KB queries work, which fail

3. **Memory & State** (Hours 8–10):
   - Test cross-channel identity resolution with sample data
   - Discover edge cases in customer matching
   - Validate sentiment scoring calibration

4. **MCP Server Build** (Hours 10–13):
   - Implement each tool iteratively with Claude Code
   - Test against sample-tickets.json scenarios
   - Log edge cases discovered during testing

5. **Crystallization** (Hours 13–16):
   - Review all discoveries
   - Ensure min 10 edge cases documented
   - Validate all guardrails triggered correctly
   - Decision: requirements stable → proceed to Transition

### Anti-Pattern Avoidance

- **Hours 1–14**: Stay firmly in Incubation. Do NOT start writing
  production FastAPI or SDK code.
- **Hour 15–16**: Explicit checkpoint — are requirements crystallized?
  If not, extend Incubation (not Transition).
- **Post-Transition**: Never use Claude Code MCP tools in production.
  All production traffic goes through OpenAI Agents SDK.

## Decisions & Tradeoffs

| # | Decision | Options Considered | Selected | Rationale |
|---|----------|-------------------|----------|-----------|
| D1 | Gmail ingestion | Pub/Sub vs Polling | **Polling** (15s interval) | Simpler setup for hackathon; Pub/Sub requires domain verification and Cloud project. Polling is sufficient for <50 emails/day volume. |
| D2 | Knowledge base search | pgvector vs simple text LIKE | **pgvector** (cosine similarity) | Constitution mandates semantic search. pgvector with OpenAI text-embedding-3-small provides >85% accuracy target. Small overhead for massive relevance gain. |
| D3 | Message ingestion | Kafka vs direct processing | **Kafka** | Constitution mandates unified queue. Kafka provides: channel decoupling, replay on failure, backpressure handling during chaos test, and audit trail. |
| D4 | Web Form UI | Next.js vs plain HTML | **Next.js** | Constitution allows Next.js/HTML/React. Next.js provides: SSR for SEO-free embed, built-in form validation via React, TypeScript type safety, easy iframe embedding. |
| D5 | Sentiment analysis | OpenAI API vs rule-based | **OpenAI API** (gpt-4o-mini) | Higher accuracy than keyword rules, handles sarcasm/nuance, aligns with existing OpenAI dependency. Cost: ~$0.001/message at volume. |
| D6 | WhatsApp long messages | Auto-split vs truncate | **Auto-split** at sentence boundaries | Constitution says "auto-split". Truncation loses information. Split at period/question mark boundaries preserves readability. |
| D7 | Embedding model | text-embedding-3-small vs 3-large | **text-embedding-3-small** (1536 dims) | Sufficient accuracy for KB search at 5x lower cost. Upgrade path to 3-large exists if >85% accuracy not met. |
| D8 | Ticket auto-close window | 12h vs 24h vs 48h | **24 hours** | Spec clarification confirmed 24h. Balances prompt resolution tracking with allowing customer time to follow up. |
| D9 | Kafka deployment | Managed vs self-hosted | **Self-hosted** (KRaft mode, no Zookeeper) | Hackathon cost constraint (<$85/mo). KRaft eliminates Zookeeper dependency. Single-broker sufficient for volume. |
| D10 | Container orchestration | K8s vs Docker Swarm | **Kubernetes** | Constitution mandates K8s. Manifests are a required deliverable. Minikube for local dev, real cluster for chaos test. |

## Testing Strategy

### Test Pyramid

```
        ┌─────────────┐
        │  Chaos Test  │  1 suite: 24h stress + pod kills
        │  (66-70h)    │
        ├─────────────┤
        │ Integration  │  4 suites: per-channel + cross-channel
        │  (47-50h)    │
        ├─────────────┤
        │ Transition   │  6 suites: guardrails + workflow + edges
        │  (18-20h)    │
        ├─────────────┤
        │  Unit Tests  │  4 suites: guardrails, sentiment, workflow,
        │  (47-50h)    │  message splitting
        └─────────────┘
```

### Transition Test Suite (Must Pass Before Specialization)

| Test | What It Validates | Pass Criteria |
|------|-------------------|---------------|
| Pricing guardrail | G1: "refund", "billing", "cost" → escalation | 100% escalation, zero AI response |
| Angry escalation | G5: sentiment <0.3 + trigger words → escalation | Empathy message + escalation logged |
| Channel length | G7: Gmail ≤500w, WhatsApp ≤300ch | No oversize messages sent |
| Tool order | Principle III: create→history→search→respond | Exact sequence in logs for every message |
| Cross-channel | Principle IV: email→WhatsApp same customer | History includes prior channel data |
| Edge case 1 | Duplicate submission dedup | Same ticket, no duplicate |
| Edge case 2 | Empty message body | Ticket created, clarification requested |
| Edge case 3 | Extremely long message (10k words) | Processed, reply ≤500w |
| Edge case 4 | Multiple guardrail triggers | Single escalation, all reasons listed |
| Edge case 5 | Unknown customer | New record created automatically |
| Edge case 6 | KB returns no results | Honest response + escalation |
| Edge case 7 | Sentiment exactly 0.3 | NOT escalated (threshold is strictly <0.3) |
| Edge case 8 | Malformed webhook | Error logged, no crash, no partial ticket |
| Edge case 9 | Channel switch mid-ticket | Response linked to existing ticket |
| Edge case 10 | Rate limiting (50 msgs/min) | All processed, abuse flagged |

### 24-Hour Chaos Test Plan

**Volume**: 100+ web forms, 50+ Gmail, 50+ WhatsApp (scripted generators)
**Disruptions**: Pod kills every 2 hours (random worker/API pod)
**Cross-channel**: 20+ customers switching channels mid-conversation

**Success Gates**:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Escalation rate | < 20% | escalated / total messages |
| KB accuracy | > 85% | relevant responses / total non-escalated |
| Cross-channel ID | > 95% | correct identity / total cross-channel |
| P95 latency | < 3 seconds | message received → response sent |
| Uptime | 99.9% | healthy checks / total checks |
| Guardrail violations | 0 | trigger messages that got AI response |
| Data loss | 0 | messages received – messages processed |

**Output**: `tests/24h-report.md` with metrics, timestamps, failures.

## Technical Implementation Notes

### Database (pgvector)

- Use `vector(1536)` column type for knowledge_base embeddings
- Index: `CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`
- Learning loop: on ticket resolve with sentiment >= 0.5, generate
  embedding for Q&A pair via OpenAI API, INSERT into knowledge_base
- Connection: asyncpg pool (min=5, max=20) with health check

### Channel Specifics

- **Gmail**: OAuth2 service account, `users.messages.list` polling every
  15s, `users.messages.send` for replies. Parse MIME for body extraction.
- **WhatsApp/Twilio**: Webhook signature validation (X-Twilio-Signature),
  auto-split at sentence boundaries (regex on `.!?` followed by space),
  each split sent as separate Twilio message with 500ms delay.
- **Web Form**: Next.js form with Zod validation, POST to `/api/support`,
  SSE or polling for response delivery, email fallback via Gmail API.

### Kafka Topics

- `inbound-messages`: all channels → normalized message format
- `outbound-responses`: agent → channel-specific formatted reply
- `escalations`: agent → human handoff queue
- `metrics`: all components → agent_metrics table

### Structured Logging (FR-036)

- JSON format: `{"timestamp", "level", "service", "ticket_id", "channel", "step", "duration_ms", "message"}`
- Every workflow step logged with ticket_id for traceability
- Errors include stack trace and recovery action taken

### Retry Logic (FR-035)

- Exponential backoff: 1s → 4s → 16s (max 3 attempts)
- On final failure: mark ticket "delivery-failed", attempt alternate
  channel (Gmail→Web email, WhatsApp→Gmail if email known)
- Dead letter queue in Kafka for failed outbound messages

### Claude Code as Development Partner

Claude Code remains the primary tool across all phases:
- **Incubation**: Prototype tools, discover patterns, generate sample data
- **Transition**: Convert MCP→SDK, generate Pydantic models, write tests
- **Specialization**: Generate FastAPI routes, SQL schema, K8s manifests,
  debug integration issues, write documentation

## Risk & Contingency

| # | Risk | Impact | Probability | Mitigation |
|---|------|--------|-------------|------------|
| R1 | Gmail API OAuth setup delays | Blocks email channel (P2) | Medium | Use Twilio sandbox first; Gmail can be added in hours 27-30. Fallback: simulated Gmail via direct DB insert for chaos test. |
| R2 | Twilio WhatsApp sandbox limitations | Blocks WhatsApp channel (P3) | Low | Sandbox supports testing. If blocked: use Twilio SMS as proxy, same webhook pattern. |
| R3 | pgvector accuracy below 85% target | Blocks KB accuracy (SC-005) | Low | Upgrade embedding model to text-embedding-3-large. Add re-ranking step with gpt-4o-mini. Increase seed KB entries. |
| R4 | Kafka setup complexity for solo dev | Delays message queue | Medium | Start with KRaft mode (no Zookeeper). Fallback: Redis Streams as simpler queue, swap to Kafka before K8s deploy. |
| R5 | 24h chaos test infrastructure cost | Exceeds budget during test | Low | Run compressed 4h simulation at 6x rate. Use Minikube locally. Only use cloud K8s for final 24h if budget allows. |
| R6 | OpenAI API rate limits during chaos | Throttled responses | Medium | Use gpt-4o-mini (higher rate limits, lower cost). Implement token bucket rate limiter. Cache common KB responses. |
| R7 | Cross-channel identity mismatches | Below 95% accuracy target | Low | Exact match on email/phone (spec assumption). Only risk: typos in web form email. Mitigation: email confirmation step. |

## Complexity Tracking

> No constitution violations detected. All complexity justified by
> constitutional requirements.

| Complexity | Why Needed | Constitution Reference |
|------------|-----------|----------------------|
| Kafka message queue | Required for unified multi-channel ingestion | Principle IX, FR-032 |
| Dual tool versions (MCP + SDK) | Required by maturity model | Principle VIII, FR-030 |
| Kubernetes manifests | Required production platform | Principle IX, FR-033 |
| pgvector embeddings | Required for semantic KB search | Principle I, FR-022 |
| 3 separate channel handlers | Required tri-channel mandate | Principle II |

## Required Deliverables Tracking

| # | Artifact | Phase | Status |
|---|----------|-------|--------|
| 1 | Full Specification (spec.md) | Pre-plan | DONE |
| 2 | skills_manifest.json | Incubation (H13-15) | Planned |
| 3 | tools_manifest.json | Incubation (H13-15) | Planned |
| 4 | system_prompt.txt | Transition (H17-18) | Planned |
| 5 | database_schema.sql | Specialization (H20-23) | Planned |
| 6 | transition_checklist.md | Transition (H15-16) | Planned |
| 7 | production_folder_structure.txt | Specialization (H20) | Planned |
| 8 | channel_handlers_overview.md | Specialization (H58-62) | Planned |
| 9 | k8s_deployment_guide.md | Specialization (H58-62) | Planned |
| 10 | 24_hour_test_plan.md | Specialization (H62-66) | Planned |
| 11 | Guardrails & Escalation table | Constitution v1.1.0 | DONE |
| 12 | Incubation vs Specialization table | Constitution v1.1.0 | DONE |
