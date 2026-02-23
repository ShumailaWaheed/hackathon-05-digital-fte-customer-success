<!--
Sync Impact Report
===================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — materially expanded all principles with
  Agent Maturity Model reference, Director/Builder roles,
  anti-patterns, explicit tool signatures, performance budgets,
  new guardrail G9 (sentiment-before-close), edge-case minimums,
  99.9% uptime target. No principles removed or redefined.

Modified principles (expanded, not redefined):
  - II. Tri-Channel Mandate: added React option for Web Form,
    semi-formal tone (was "professional"), email fallback
  - V. Guardrails & Escalation: added G9 sentiment-before-close
  - VII. Agent Maturity Model: added reference URL, Director/
    Builder roles, anti-patterns, transition criteria
  - VIII. Dual Tool Implementation: added explicit tool signatures
  - X. Test-First & Chaos Readiness: added performance budgets,
    cross-channel switch tests, 99.9% uptime target

Added sections:
  - Anti-Patterns (under Principle VII)
  - Performance Budgets table
  - Tool Signatures table
  - Incubation vs Specialization comparison table
  - Required Deliverables checklist

Removed sections: None

Templates requiring updates:
  - .specify/templates/plan-template.md — ⚠ pending
  - .specify/templates/spec-template.md — ✅ compatible
  - .specify/templates/tasks-template.md — ✅ compatible

Follow-up TODOs: None
-->

# The CRM Digital FTE Factory — Hackathon 5 Constitution

## Core Principles

### I. Own Your CRM — Zero External Dependencies

The system MUST use a self-built PostgreSQL CRM with pgvector.
Tables MUST include: `customers`, `customer_identifiers`,
`conversations`, `messages`, `tickets`, `knowledge_base`
(pgvector embeddings), `channel_configs`, `agent_metrics`.
NO Salesforce, NO HubSpot, NO third-party CRM. Every data
entity lives in our database. The `knowledge_base` MUST use
pgvector for semantic search and MUST be updated when tickets
are resolved (add resolved Q&A pairs as new embedding vectors).

### II. Tri-Channel Mandate

All three channels MUST be fully implemented and production-ready:

1. **Gmail (Email)** — Gmail API + Pub/Sub or polling webhook;
   formal, detailed replies capped at 500 words; proper
   greeting and signature; professional tone.
2. **WhatsApp** — Twilio webhook ingest + Twilio API reply;
   conversational, concise (300-char preferred limit);
   auto-split for longer messages; casual tone.
3. **Web Support Form** — Complete standalone embeddable UI
   (Next.js/HTML/React) with client-side validation; NOT just
   a backend endpoint; semi-formal tone; API response with
   email fallback delivery.

### III. Strict Workflow Order (Non-Negotiable)

Every inbound message MUST follow this exact sequence:
`create_ticket` → `get_customer_history` →
`search_knowledge_base` → `send_response`.
No step may be skipped or reordered. The agent MUST NOT
respond without first creating a ticket. This order ensures
audit trail, context awareness, and accurate answers on
every single interaction.

### IV. Cross-Channel Conversation Continuity

A customer MUST be able to switch between Gmail, WhatsApp,
and Web Form without losing context. The `customer_identifiers`
table maps emails, phone numbers, and form session IDs to a
single `customer` record. Cross-channel identity resolution
MUST achieve >95% accuracy. Every response MUST include prior
cross-channel history to maintain conversation continuity.

### V. Guardrails & Escalation (Non-Negotiable)

Hard rules that MUST never be violated:
- Never discuss pricing, refunds, legal matters, or competitors
  — immediately escalate with reason and full context.
- Never promise features absent from `product-docs.md`.
- Never exceed channel character/word limits.
- Angry customer (sentiment < 0.3) OR trigger words ("human",
  "agent", "lawyer", "sue", "manager") → immediate escalation
  via `escalate_to_human` with empathy message.
- Always use channel-appropriate tone and formatting.
- MUST check sentiment before closing any ticket; do NOT close
  if customer sentiment is negative.

### VI. Sentiment-Driven Intelligence

Real-time sentiment analysis MUST run on every inbound message
via `analyze_sentiment`. Sentiment scores are stored on the
`messages` row. Daily sentiment reports MUST be generated via
`generate_daily_report` covering trends, scores, and flagged
issues. The system MUST learn from resolved tickets by adding
resolved Q&A pairs as new vectors in the `knowledge_base`
table to continuously improve response accuracy.

### VII. Agent Maturity Model Compliance

Reference: https://agentfactory.panaversity.org/docs/General-Agents-Foundations/agent-factory-paradigm/the-2025-inflection-point#the-agent-maturity-model

The project MUST implement both maturity stages in order:

- **Stage 1 — Incubation** (Director Role):
  Claude Code as Agent Factory. Director sets intent, provides
  context, reviews output, course-corrects. Build `/context`
  folder (company-profile, product-docs, sample-tickets 50+,
  escalation-rules, brand-voice). MCP Server with 7+ tools.
  Skills manifest + discovery log + edge-cases (min 10).
  Working prototype handling all 3 channels.

- **Stage 2 — Specialization** (Builder Role):
  Define precise purpose, build guardrails, deploy as product.
  Full production system: OpenAI Agents SDK with `@function_tool`
  + Pydantic models; formalized system prompt; Kafka workers;
  Kubernetes deployment. Claude Code remains primary development
  partner (writes SDK code, generates endpoints, schema, K8s
  manifests, debugs production).

- **Transition Criteria**: Crystallize requirements FIRST.
  Move when: requirements are stable, high-volume is needed,
  reliability/cost/latency become critical.

**Anti-Patterns (MUST avoid):**
1. **Premature Specialization** — Building production agent
   before requirements are crystallized through incubation.
2. **Perpetual Incubation** — Using General Agent (Claude Code)
   in production instead of transitioning to Custom Agent.
3. **Skipping Incubation** — Jumping directly to OpenAI SDK
   without exploration and requirement discovery.

### VIII. Dual Tool Implementation

Every tool MUST exist in two forms:
1. **MCP Server version** (Incubation phase).
2. **OpenAI Agents SDK `@function_tool`** (Production phase)
   with Pydantic input/output models and full error handling.

**Required Tool Signatures:**

| Tool | Signature |
|------|-----------|
| search_knowledge_base | `(query: str, max_results: int = 5)` |
| create_ticket | `(customer_id: str, issue: str, priority: str, channel: str, metadata: dict)` |
| get_customer_history | `(customer_id: str)` |
| escalate_to_human | `(ticket_id: str, reason: str)` |
| send_response | `(ticket_id: str, message: str, channel: str)` — auto-detect/format |
| analyze_sentiment | `(message: str)` → float 0.0–1.0 |
| generate_daily_report | `(date: str)` |

### IX. Production-Grade Architecture

The production stack MUST be:
FastAPI + OpenAI Agents SDK + Kafka + PostgreSQL (pgvector) +
Kubernetes. Multi-channel ingestion MUST flow through Kafka
topics. The system MUST include Dockerfile, docker-compose,
and k8s manifests. Target: <$1,000/year operational cost to
replace a $75,000+/year human FTE.

**Production Folder Structure:**
```
production/
├── agent/          # OpenAI Agents SDK agent + system prompt
├── channels/       # Gmail, WhatsApp, Web Form handlers
├── workers/        # Kafka message processor
├── api/            # FastAPI endpoints + webhooks
├── database/       # schema.sql + migrations
├── k8s/            # Kubernetes manifests
├── tests/          # Transition + E2E + chaos tests
├── Dockerfile
├── docker-compose.yml
└── docs/           # Runbook + deployment guide
```

### X. Test-First & Chaos Readiness

All transition tests MUST pass before production deploy.
End-to-end tests MUST cover: pricing guardrail, angry customer
escalation, channel length enforcement, tool order compliance,
cross-channel continuity, and minimum 10 documented edge cases.

**Performance Budgets:**

| Metric | Target |
|--------|--------|
| Message processing time | < 3 seconds |
| Response delivery time | < 30 seconds |
| Knowledge base accuracy | > 85% |
| Escalation rate | < 20% |
| Cross-channel ID accuracy | > 95% |
| P95 latency (chaos test) | < 3 seconds |
| Uptime (chaos test) | 99.9% |

**24-Hour Chaos Test Requirements:**
- 100+ web form submissions
- 50+ Gmail messages
- 50+ WhatsApp messages
- Cross-channel switches (same customer, different channels)
- Pod kills every 2 hours
- Zero guardrail violations
- All performance budgets met throughout

## Hard Guardrails & Escalation Rules

| # | Rule | Trigger | Action |
|---|------|---------|--------|
| G1 | No pricing/refund discussion | Keywords: price, refund, billing, cost, discount | `escalate_to_human` with reason + context |
| G2 | No legal discussion | Keywords: lawyer, sue, legal, lawsuit, court | `escalate_to_human` with reason + context |
| G3 | No competitor discussion | Any competitor brand name mentioned | `escalate_to_human` with reason + context |
| G4 | No false feature promises | Feature not in product-docs.md | "Let me check with the team" + escalate |
| G5 | Angry customer escalation | sentiment < 0.3 OR words: human, agent, manager | `escalate_to_human` with empathy + context |
| G6 | Ticket-first mandate | Any inbound message | MUST `create_ticket` before any other action |
| G7 | Channel length limits | Gmail > 500 words; WhatsApp > 300 chars | Truncate or split; never exceed |
| G8 | Channel tone compliance | Channel detection | Gmail=formal; WhatsApp=conversational; Web=semi-formal |
| G9 | Sentiment-before-close | Ticket closure attempt | MUST check sentiment; block close if negative |

## Technology Stack & Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API Framework | FastAPI | REST endpoints, webhook handlers |
| AI Agent SDK | OpenAI Agents SDK | Production agent with @function_tool |
| Agent Factory | Claude Code (MCP) | Incubation phase tooling + dev partner |
| Message Queue | Apache Kafka | Unified multi-channel message ingestion |
| Database | PostgreSQL + pgvector | CRM, tickets, knowledge base embeddings |
| Email Channel | Gmail API + Pub/Sub | Inbound/outbound email |
| Chat Channel | Twilio (WhatsApp API) | Inbound/outbound WhatsApp |
| Web Channel | Next.js / HTML / React | Embeddable support form UI |
| Containerization | Docker + docker-compose | Local development & CI |
| Orchestration | Kubernetes | Production deployment + monitoring |
| Language | Python 3.11+ | Backend services |
| Frontend | Next.js / TypeScript | Web support form |

## Incubation vs Specialization Comparison

| Aspect | Stage 1 — Incubation | Stage 2 — Specialization |
|--------|----------------------|--------------------------|
| Agent Type | General (Claude Code) | Custom (OpenAI Agents SDK) |
| Role | Director: set intent, review | Builder: precise purpose, guardrails |
| Tool Format | MCP Server tools | @function_tool + Pydantic |
| Architecture | Claude Code + local prototype | FastAPI + Kafka + K8s |
| Database | Local PostgreSQL | Production PostgreSQL + pgvector |
| Channels | Simulated/basic handlers | Full Gmail API + Twilio + Web UI |
| Testing | Discovery + edge cases | Transition + E2E + chaos tests |
| System Prompt | Exploratory, flexible | Formalized, hard constraints |
| Deployment | Local development | Kubernetes cluster |
| Goal | Crystallize requirements | Production reliability |
| Anti-Pattern | Skipping this phase | Perpetual incubation |
| Transition Signal | Requirements stable | N/A (final stage) |

## Required Deliverables

All 12 artifacts MUST be generated during the project:

- [ ] 1. Full Customer Success FTE Specification (Markdown)
- [ ] 2. `skills_manifest.json`
- [ ] 3. `tools_manifest.json` (MCP + OpenAI SDK versions)
- [ ] 4. `system_prompt.txt` (production, strict workflow)
- [ ] 5. `database_schema.sql` (complete CRM + pgvector)
- [ ] 6. `transition_checklist.md`
- [ ] 7. `production_folder_structure.txt`
- [ ] 8. `channel_handlers_overview.md`
- [ ] 9. `k8s_deployment_guide.md`
- [ ] 10. `24_hour_test_plan.md`
- [ ] 11. Guardrails & Escalation Rules table (in constitution)
- [ ] 12. Incubation vs Specialization comparison table (in constitution)

## Development Workflow (3-Phase Maturity Model)

### Phase 1 — Incubation (Stage 1, Hours 1–16)

1. Create `/context` folder: company-profile.md, product-docs.md,
   sample-tickets.json (50+ multi-channel), escalation-rules.md,
   brand-voice.md.
2. Build MCP Server with 7+ tools (all 7 required tools).
3. Define `skills_manifest.json` and `tools_manifest.json`.
4. Create `specs/customer-success-fte/spec.md` +
   `discovery-log.md` + `edge-cases.md` (min 10 documented).
5. Validate working prototype handles all 3 channels in MCP mode.

### Phase 2 — Transition (Hours 15–18, Critical)

1. Crystallize discoveries into `transition-checklist.md`.
2. Convert every MCP tool → OpenAI Agents SDK `@function_tool`
   with Pydantic input/output models and full error handling.
3. Formalize `system_prompt.txt` with hard constraints and
   exact workflow order.
4. Create and pass transition test suite:
   - Pricing guardrail test
   - Angry customer escalation test
   - Channel length enforcement test
   - Tool order compliance test
   - Cross-channel continuity test
   - Minimum 10 edge case tests.

### Phase 3 — Specialization (Stage 2 — Production)

1. Build full production folder structure under `production/`.
2. Complete `database/schema.sql` with all tables + indexes +
   pgvector extensions.
3. Implement channel handlers: Gmail, WhatsApp (Twilio),
   Web Form (full UI).
4. Implement Kafka message processor worker.
5. Create Kubernetes manifests, Dockerfile, docker-compose.
6. Implement metrics collection + daily report generation.
7. Pass 24-hour multi-channel chaos test meeting all
   performance budgets.
8. Complete documentation + runbook.

## Governance

- This constitution is the supreme authority for all project
  decisions. All PRs and code reviews MUST verify compliance
  with these principles.
- Amendments require: (1) written proposal, (2) impact analysis
  on existing code, (3) updated constitution version, and
  (4) propagation to all dependent templates.
- Version follows semantic versioning: MAJOR for principle
  removal/redefinition, MINOR for new principles or material
  expansion, PATCH for clarifications and typos.
- Compliance review MUST occur at each phase transition
  (Incubation → Transition → Specialization).
- Guardrails (G1–G9) are NON-NEGOTIABLE and MUST NOT be
  weakened without unanimous team consent.
- Claude Code remains the primary development partner across
  all phases — writing SDK code, generating endpoints, schema,
  K8s manifests, and debugging production issues.

**Version**: 1.1.0 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23
