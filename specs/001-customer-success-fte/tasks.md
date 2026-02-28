# Tasks: Customer Success Digital FTE

**Input**: Design documents from `/specs/001-customer-success-fte/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — constitution mandates transition tests, E2E tests, and chaos tests.

**Organization**: Tasks grouped by user story + maturity model phases to enable independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Repository structure, dependencies, Docker infrastructure

- [x] T001 ✅ Create production directory structure per plan.md: production/agent/, production/api/, production/channels/, production/workers/, production/database/, production/tests/, production/k8s/, production/docs/
- [x] T002 ✅ Create Python project with requirements.txt: fastapi, uvicorn, openai, agents-sdk, confluent-kafka, asyncpg, pgvector, twilio, google-api-python-client, google-auth, pydantic, python-dotenv, pytest, pytest-asyncio, httpx, locust
- [x] T003 ✅ [P] Create frontend directory structure: frontend/src/app/, frontend/src/components/, frontend/src/lib/, frontend/public/
- [x] T004 ✅ [P] Initialize Next.js project with package.json and tsconfig.json in frontend/
- [x] T005 ✅ Create .env.example with all required environment variables (OPENAI_API_KEY, DATABASE_URL, KAFKA_BOOTSTRAP_SERVERS, GMAIL_CREDENTIALS_PATH, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, etc.) in project root
- [x] T006 ✅ Create docker-compose.yml with services: postgres (16 + pgvector), kafka (KRaft mode, no Zookeeper), api (FastAPI), worker (message processor) in project root
- [x] T007 ✅ Create context/company-profile.md with fictional SaaS company details (name, product, team, support hours)
- [x] T008 ✅ Create context/product-docs.md with product features, FAQs, common issues, and troubleshooting guides (20+ entries)
- [x] T009 ✅ [P] Create context/sample-tickets.json with 55 multi-channel sample tickets (mix of Gmail, WhatsApp, web form, various sentiments, escalation triggers, edge cases)
- [x] T010 ✅ Create context/escalation-rules.md documenting guardrails G1–G9 with keyword lists, sentiment thresholds, and action procedures
- [x] T011 ✅ Create context/brand-voice.md with tone guidelines per channel (Gmail=formal, WhatsApp=conversational, Web=semi-formal) including examples

**Checkpoint**: Project scaffold ready, Docker infrastructure startable, context folder complete.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, core models, Kafka setup, shared utilities — MUST complete before any user story

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T012 ✅ Create production/database/schema.sql with all 8 tables (customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics), all indexes, pgvector extension, CHECK constraints, and foreign keys per data-model.md
- [x] T013 ✅ Create production/database/seed.sql with initial knowledge_base entries (20+ product Q&A pairs with embeddings), channel_configs for all 3 channels (tone, max_length, greeting/signature templates)
- [x] T014 ✅ Implement production/database/connection.py with asyncpg connection pool (min=5, max=20), health check query, and pool lifecycle management
- [x] T015 ✅ [P] Implement production/database/models.py with Pydantic models for all 8 entities matching data-model.md field definitions (Customer, CustomerIdentifier, Conversation, Message, Ticket, KnowledgeBaseEntry, ChannelConfig, AgentMetric)
- [x] T016 ✅ [P] Implement production/database/repositories.py with async CRUD operations for all entities: create_customer, find_customer_by_identifier, create_ticket, update_ticket_status, create_message, search_knowledge_base (pgvector cosine similarity), create_agent_metric, get_channel_config
- [x] T017 ✅ Implement production/api/middleware/logging.py with structured JSON logger (fields: timestamp, level, service, ticket_id, channel, step, duration_ms, message) outputting to stdout per FR-036
- [x] T018 ✅ [P] Implement production/workers/kafka_config.py with Kafka producer/consumer setup for 4 topics: inbound-messages, outbound-responses, escalations, metrics
- [x] T019 ✅ Implement production/agent/tools/analyze_sentiment.py as @function_tool with Pydantic SentimentInput/SentimentOutput models — calls OpenAI gpt-4o-mini for sentiment scoring (returns float 0.0–1.0) per tool signature in constitution
- [x] T020 ✅ [P] Implement production/agent/tools/search_knowledge_base.py as @function_tool with Pydantic models — queries pgvector with cosine similarity, returns up to max_results=5 entries per FR-022, FR-024
- [x] T021 ✅ [P] Implement production/agent/tools/create_ticket.py as @function_tool with Pydantic models — creates ticket with customer_id, issue, priority, channel, metadata; sets status to 'open' per FR-001
- [x] T022 ✅ [P] Implement production/agent/tools/get_customer_history.py as @function_tool with Pydantic models — retrieves full cross-channel conversation history for customer_id per FR-013
- [x] T023 ✅ [P] Implement production/agent/tools/escalate_to_human.py as @function_tool with Pydantic models — marks ticket as 'escalated', publishes to escalations topic with ticket_id, reason, full context per FR-021
- [x] T024 ✅ [P] Implement production/agent/tools/send_response.py as @function_tool with Pydantic models — auto-detects channel, applies tone/length rules, publishes to outbound-responses topic per FR-010, FR-019
- [x] T025 ✅ [P] Implement production/agent/tools/generate_daily_report.py as @function_tool with Pydantic models — queries agent_metrics and messages for date, computes average sentiment, trends, top issues, escalation rate, per-channel breakdown per FR-025
- [x] T026 ✅ Implement production/agent/guardrails.py with keyword detection functions for G1 (pricing: price, refund, billing, cost, discount), G2 (legal: lawyer, sue, legal, lawsuit, court), G3 (competitor names), G5 (trigger words: human, agent, manager + sentiment <0.3), G9 (sentiment-before-close check) per FR-014 through FR-020
- [x] T027 ✅ Create production/agent/system_prompt.txt with strict workflow order (create_ticket→get_customer_history→search_knowledge_base→send_response), all guardrail rules G1–G9, channel tone instructions, and hard constraints per constitution Principle III and V
- [x] T028 ✅ Implement production/agent/agent.py wiring OpenAI Agents SDK with all 7 @function_tool functions, system prompt, guardrail pre-check before response generation, and strict workflow enforcement

**Checkpoint**: Foundation ready — database, models, all 7 tools, agent, guardrails, Kafka config. User story implementation can begin.

---

## Phase 3: User Story 1 — Web Form Support Request (Priority: P1) MVP

**Goal**: Customer submits web form → ticket created → history retrieved → KB searched → response displayed on-screen + email fallback

**Independent Test**: Submit form through UI, verify ticket created, KB searched, response displayed — no Gmail or WhatsApp needed.

### Implementation for User Story 1

- [x] T029 ✅ [US1] Implement production/api/routes/webhooks.py with POST /api/support endpoint: validate request body (name, email, category, message), resolve customer identity, normalize to unified message format, publish to Kafka inbound-messages topic
- [x] T030 ✅ [US1] Implement production/api/routes/webhooks.py with GET /api/support/{ticket_id}/status endpoint: return ticket status (processing/responded/escalated) and response text when ready per contracts/api.yaml
- [x] T031 ✅ [US1] Implement production/channels/webform_handler.py with process_webform_message (normalize form data to unified format) and send_webform_response (store response for polling + trigger email fallback via Gmail API) per FR-008, FR-009
- [x] T032 ✅ [US1] Implement production/workers/message_processor.py: Kafka consumer for inbound-messages topic, executes strict workflow (create_ticket→get_history→search_kb→guardrail_check→send_response or escalate), logs every step with ticket_id per FR-002
- [x] T033 ✅ [US1] Implement production/workers/outbound_sender.py: Kafka consumer for outbound-responses topic, dispatches to correct channel handler based on message channel field, implements retry with exponential backoff (1s→4s→16s, max 3) per FR-035
- [x] T034 ✅ [US1] Implement frontend/src/components/SupportForm.tsx with React form: fields (name, email, category dropdown, message textarea), Zod client-side validation, submit handler calling POST /api/support per FR-008
- [x] T035 ✅ [US1] Implement frontend/src/components/ResponseDisplay.tsx: polls GET /api/support/{ticket_id}/status every 2s, displays response when ready, shows escalation message if escalated, loading spinner while processing
- [x] T036 ✅ [US1] Implement frontend/src/components/StatusIndicator.tsx: visual ticket status indicator (processing→responded/escalated) with appropriate messaging
- [x] T037 ✅ [US1] Implement frontend/src/app/page.tsx as main page composing SupportForm + ResponseDisplay + StatusIndicator
- [x] T038 ✅ [US1] Implement frontend/src/lib/api.ts with typed API client: submitSupportForm(data) and getTicketStatus(ticketId) functions
- [x] T039 ✅ [US1] Create frontend/public/embed.js: iframe embed loader script for third-party websites to embed the support form
- [x] T040 ✅ [US1] Implement production/api/main.py: FastAPI app with CORS middleware (allow frontend origin), include webhook routes, structured logging, startup/shutdown events for DB pool and Kafka

**Checkpoint**: Web form fully functional — submit form, get AI response on-screen. MVP complete.

---

## Phase 4: User Story 2 — Gmail Email Support (Priority: P2)

**Goal**: Customer sends email → Gmail API receives → ticket created → formal reply sent via Gmail (≤500 words, greeting + signature)

**Independent Test**: Send email to support inbox, verify formal reply arrives within 30s with greeting, signature, ≤500 words.

### Implementation for User Story 2

- [x] T041 ✅ [US2] Implement production/channels/gmail_handler.py with GmailClient class: OAuth2 service account auth, poll_inbox (users.messages.list with after: filter, 15s interval), parse_email (extract body from MIME), send_reply (formal tone, greeting + signature, ≤500 words) per FR-004, FR-005
- [x] T042 ✅ [US2] Add Gmail polling loop to production/workers/gmail_poller.py: poll every 15s, normalize new emails to unified format, publish to inbound-messages Kafka topic
- [x] T043 ✅ [US2] Add Gmail dispatch case to production/workers/outbound_sender.py: format response with greeting template + signature from channel_configs, enforce 500-word cap, send via gmail_handler.send_reply
- [x] T044 ✅ [US2] Add POST /webhooks/gmail endpoint to production/api/routes/webhooks.py for Pub/Sub push notifications (optional, supports both polling and push) per contracts/webhooks.yaml
- [x] T045 ✅ [US2] Update production/channels/webform_handler.py to use gmail_handler for email fallback delivery when web form response includes email copy per FR-009

**Checkpoint**: Gmail channel operational — email in, formal reply out. Web form + Gmail both working independently.

---

## Phase 5: User Story 3 — WhatsApp Conversational Support (Priority: P3)

**Goal**: Customer sends WhatsApp message → Twilio webhook receives → ticket created → concise casual reply (≤300ch, auto-split) sent via Twilio

**Independent Test**: Send WhatsApp message, verify concise casual reply arrives within 30s, correctly split if >300 chars.

### Implementation for User Story 3

- [x] T046 ✅ [US3] Implement production/channels/whatsapp_handler.py with TwilioWhatsAppClient class: validate_signature (X-Twilio-Signature verification), parse_message (extract Body, From phone), send_reply (conversational tone, auto-split at sentence boundaries ≤300 chars, 500ms delay between splits) per FR-006, FR-007
- [x] T047 ✅ [US3] Add POST /webhooks/whatsapp endpoint to production/api/routes/webhooks.py: validate Twilio signature, normalize WhatsApp message to unified format, publish to inbound-messages Kafka topic per contracts/webhooks.yaml
- [x] T048 ✅ [US3] Add WhatsApp dispatch case to production/workers/outbound_sender.py: format response in casual tone, apply auto-split logic (split at .!? + space, each segment ≤300 chars), send via whatsapp_handler.send_reply with 500ms inter-message delay
- [x] T049 ✅ [US3] Implement message splitting utility in production/channels/whatsapp_handler.py: split_message(text, max_chars=300) function that splits at natural sentence boundaries, falls back to word boundary if single sentence >300 chars

**Checkpoint**: WhatsApp channel operational. All 3 channels working independently.

---

## Phase 6: User Story 4 — Cross-Channel Continuity (Priority: P4)

**Goal**: Customer switches channels (e.g., web form → Gmail → WhatsApp) and system maintains full conversation context

**Independent Test**: Contact via web form, follow up via Gmail with same email — verify Gmail response references web form conversation.

### Implementation for User Story 4

- [x] T050 ✅ [US4] Implement production/api/services/identity_resolver.py with resolve_customer(identifier_type, identifier_value) function: lookup customer_identifiers table, return existing customer or create new customer + link identifier per FR-011, FR-012
- [x] T051 ✅ [US4] Update production/api/routes/webhooks.py (all 3 channel endpoints) to call identity_resolver.resolve_customer before publishing to Kafka, attach customer_id to unified message
- [x] T052 ✅ [US4] Update production/agent/tools/get_customer_history.py to return messages from ALL channels sorted by timestamp, including channel labels, for the resolved customer_id per FR-013
- [x] T053 ✅ [US4] Update production/workers/message_processor.py to link new messages to existing open conversation for the customer, or create new conversation if none active

**Checkpoint**: Cross-channel identity works — same customer recognized across all channels with full history.

---

## Phase 7: User Story 5 — Escalation and Human Handoff (Priority: P5)

**Goal**: Guardrail triggers (G1–G5, G9) immediately stop AI processing, log reason, hand off to human with full context

**Independent Test**: Send "I want a refund" → verify escalation with correct reason, no AI response generated.

### Implementation for User Story 5

- [x] T054 ✅ [US5] Update production/workers/message_processor.py to run guardrails.check_all(message) BEFORE calling agent, if any guardrail triggers → call escalate_to_human directly, skip agent workflow
- [x] T055 ✅ [US5] Implement production/workers/escalation_handler.py: Kafka consumer for escalations topic, logs escalation with full context (ticket_id, reason, conversation history, sentiment scores, trigger), stores in agent_metrics per FR-021
- [x] T056 ✅ [US5] Update production/agent/tools/send_response.py to check sentiment score before marking ticket resolved — if sentiment <0.3, do not resolve, flag for review per G9 (FR-020)
- [x] T057 ✅ [US5] Implement ticket closure worker in production/workers/ticket_closer.py: run hourly, find resolved tickets older than 24h, check most recent sentiment via G9, close if positive or revert to in-progress if negative per spec Ticket Lifecycle

**Checkpoint**: All guardrails enforced — pricing/legal/competitor/angry triggers escalate correctly, G9 blocks negative closures.

---

## Phase 8: User Story 6 — Daily Sentiment Report (Priority: P6)

**Goal**: System generates daily report with sentiment trends, top issues, escalation rates, per-channel breakdown

**Independent Test**: After 20+ messages processed, trigger report generation — verify it includes all required sections.

### Implementation for User Story 6

- [x] T058 ✅ [US6] Implement production/workers/report_generator.py: scheduled daily worker that calls generate_daily_report tool with yesterday's date, formats output as Markdown, stores in database and optionally sends via email per FR-025
- [x] T059 ✅ [US6] Implement GET /api/reports/daily endpoint in production/api/routes/reports.py: accepts optional date query param, returns report data as JSON per contracts/api.yaml
- [x] T060 ✅ [US6] Update production/agent/tools/generate_daily_report.py to query agent_metrics grouped by date: compute average_sentiment, sentiment_trend (compare to prior day), top_5_categories (from ticket issues), escalation_rate (escalated/total), channel_breakdown (volume + avg sentiment per channel) per FR-025, FR-026

**Checkpoint**: Daily reports generating with all required metrics and per-channel breakdown.

---

## Phase 9: User Story 7 — Knowledge Base Learning Loop (Priority: P7)

**Goal**: Resolved tickets with positive sentiment auto-generate new KB entries as vector embeddings

**Independent Test**: Resolve ticket with positive sentiment, submit similar question — verify KB returns the learned answer.

### Implementation for User Story 7

- [x] T061 ✅ [US7] Implement production/workers/learning_loop.py: triggered on ticket status change to 'resolved', checks sentiment >= 0.5, extracts Q (original issue) and A (agent response), generates embedding via OpenAI text-embedding-3-small, inserts into knowledge_base with source='learned' and source_ticket_id per FR-023
- [x] T062 ✅ [US7] Update production/database/repositories.py add_knowledge_entry function to accept source_ticket_id and set source='learned', generate embedding via OpenAI API before insert
- [x] T063 ✅ [US7] Update production/workers/message_processor.py to trigger learning_loop on ticket resolution (after status change to 'resolved')

**Checkpoint**: Knowledge base grows automatically from resolved tickets. Semantic search returns learned answers.

---

## Phase 10: User Story 8 — Incubation to Production Transition (Priority: P8)

**Goal**: Complete incubation artifacts (MCP tools, manifests), run transition checklist, verify production agent passes all tests

**Independent Test**: Run full transition test suite — all tests pass against production agent.

### Implementation for User Story 8

- [x] T064 ✅ [US8] Implement incubation/mcp_server/server.py: MCP Server entry point registering all 7 tools
- [x] T065 ✅ [P] [US8] Implement incubation/mcp_server/tools/search_knowledge_base.py as MCP tool version (simpler, no Pydantic)
- [x] T066 ✅ [P] [US8] Implement incubation/mcp_server/tools/create_ticket.py as MCP tool version
- [x] T067 ✅ [P] [US8] Implement incubation/mcp_server/tools/get_customer_history.py as MCP tool version
- [x] T068 ✅ [P] [US8] Implement incubation/mcp_server/tools/escalate_to_human.py as MCP tool version
- [x] T069 ✅ [P] [US8] Implement incubation/mcp_server/tools/send_response.py as MCP tool version
- [x] T070 ✅ [P] [US8] Implement incubation/mcp_server/tools/analyze_sentiment.py as MCP tool version
- [x] T071 ✅ [P] [US8] Implement incubation/mcp_server/tools/generate_daily_report.py as MCP tool version
- [x] T072 ✅ [US8] Create incubation/skills_manifest.json listing all agent skills (ticket management, knowledge search, sentiment analysis, escalation handling, channel routing, report generation, learning loop)
- [x] T073 ✅ [US8] Create incubation/tools_manifest.json listing all 7 tools with both MCP and OpenAI SDK versions, signatures, descriptions per constitution Principle VIII
- [x] T074 ✅ [US8] Create incubation/discovery-log.md documenting pattern discoveries from sample-tickets.json analysis (top issues, channel patterns, escalation triggers found)
- [x] T075 ✅ [US8] Create incubation/edge-cases.md documenting minimum 10 edge cases discovered during incubation (matching spec edge cases 1–12)
- [x] T076 ✅ [US8] Create production/docs/transition_checklist.md: checklist verifying each MCP tool has production @function_tool equivalent, system prompt formalized, all guardrails encoded, workflow order enforced

**Checkpoint**: All incubation artifacts complete. Transition checklist passed. Dual tool versions verified.

---

## Phase 11: Testing

**Purpose**: Transition tests, integration tests, and chaos test infrastructure

### Transition Tests

- [x] T077 ✅ [P] Implement production/tests/transition/test_pricing_guardrail.py: send messages with "refund", "billing", "cost", "discount", "price" — assert 100% escalation, zero AI response per G1
- [x] T078 ✅ [P] Implement production/tests/transition/test_angry_escalation.py: send messages with sentiment <0.3 and trigger words "human", "agent", "manager" — assert empathy message + escalation per G5
- [x] T079 ✅ [P] Implement production/tests/transition/test_channel_length.py: generate >500 word Gmail reply and >300 char WhatsApp reply — assert truncation/splitting enforced per G7
- [x] T080 ✅ [P] Implement production/tests/transition/test_tool_order.py: process message and verify log sequence is exactly create_ticket→get_customer_history→search_knowledge_base→send_response per Principle III
- [x] T081 ✅ [P] Implement production/tests/transition/test_cross_channel_continuity.py: create customer via web form, follow up via Gmail — assert history includes web form messages per Principle IV
- [x] T082 ✅ Implement production/tests/transition/test_edge_cases.py with 10+ test cases: duplicate submission, empty body, long message, multiple guardrail triggers, unknown customer, KB no results, sentiment 0.3 boundary, malformed webhook, channel switch mid-ticket, rate limiting per spec edge cases

### Integration Tests

- [x] T083 ✅ [P] Implement production/tests/integration/test_webform_channel.py: full E2E — submit form, verify ticket created, response returned, correct tone
- [x] T084 ✅ [P] Implement production/tests/integration/test_gmail_channel.py: full E2E — mock Gmail API, verify ticket, formal reply ≤500 words
- [x] T085 ✅ [P] Implement production/tests/integration/test_whatsapp_channel.py: full E2E — mock Twilio webhook, verify ticket, casual reply ≤300 chars, auto-split
- [x] T086 ✅ [P] Implement production/tests/integration/test_cross_channel.py: full E2E — same customer across 3 channels, verify unified history

### Chaos Test Infrastructure

- [x] T087 ✅ Implement production/tests/chaos/message_generator.py: scripted generator producing 100+ web forms, 50+ Gmail, 50+ WhatsApp messages with mix of normal/escalation/edge cases, cross-channel switches
- [x] T088 ✅ Implement production/tests/chaos/pod_killer.py: K8s pod disruption script killing random worker/API pod every 2 hours
- [x] T089 ✅ Implement production/tests/chaos/chaos_runner.py: orchestrator running 24h test (or compressed 4h at 6x), collecting metrics (escalation rate, accuracy, cross-ID accuracy, P95 latency, uptime, guardrail violations, data loss)
- [x] T090 ✅ Create production/docs/24_hour_test_plan.md documenting test setup, volume targets, disruption schedule, success gates (<20% escalation, >85% accuracy, >95% cross-ID, P95 <3s, 99.9% uptime, 0 guardrail violations)

**Checkpoint**: All transition tests pass. Integration tests pass. Chaos test infrastructure ready.

---

## Phase 12: Containerization & Deployment

**Purpose**: Docker, Kubernetes manifests, deployment documentation

- [x] T091 ✅ Create production/Dockerfile: multi-stage build (Python 3.11-slim), install requirements, copy production/, expose port 8000, CMD uvicorn
- [x] T092 ✅ Update docker-compose.yml to add api service (build from Dockerfile), worker service (same image, different CMD), frontend service (Node build), wire all services with postgres and kafka
- [x] T093 ✅ [P] Create production/k8s/namespace.yaml for customer-success-fte namespace
- [x] T094 ✅ [P] Create production/k8s/deployment-api.yaml: FastAPI deployment (2 replicas), liveness/readiness probes on /health, resource limits, env from configmap/secrets
- [x] T095 ✅ [P] Create production/k8s/deployment-worker.yaml: message processor deployment (2 replicas), Kafka consumer group config
- [x] T096 ✅ [P] Create production/k8s/deployment-kafka.yaml: single-broker KRaft Kafka StatefulSet with persistent volume
- [x] T097 ✅ [P] Create production/k8s/deployment-postgres.yaml: PostgreSQL StatefulSet with pgvector, persistent volume, init container for schema.sql
- [x] T098 ✅ [P] Create production/k8s/service-api.yaml: ClusterIP service for API, LoadBalancer for external webhook access
- [x] T099 ✅ [P] Create production/k8s/configmap.yaml: non-secret config (KAFKA_BOOTSTRAP_SERVERS, DATABASE_URL template, channel configs)
- [x] T100 ✅ [P] Create production/k8s/secrets.yaml: template for secrets (OPENAI_API_KEY, TWILIO_AUTH_TOKEN, GMAIL_CREDENTIALS — no real values)
- [x] T101 ✅ [P] Create production/k8s/hpa.yaml: HorizontalPodAutoscaler for API (min 2, max 5, target 70% CPU)
- [x] T102 ✅ Implement production/api/routes/health.py: GET /health returning status of database, kafka, gmail_api, twilio_api per contracts/health.yaml and FR-037

**Checkpoint**: Docker stack runs locally. K8s manifests ready for deployment.

---

## Phase 13: Polish & Documentation

**Purpose**: Documentation, runbook, final validation

- [x] T103 ✅ [P] Create production/docs/runbook.md: operational procedures (deploy, rollback, scale, monitor logs, handle escalation queue, restart Kafka, rebuild KB embeddings, generate ad-hoc reports)
- [x] T104 ✅ [P] Create production/docs/channel_handlers_overview.md: architecture of each channel handler (Gmail polling flow, Twilio webhook flow, Web Form submission flow), tone rules, length limits, retry behavior
- [x] T105 ✅ [P] Create production/docs/k8s_deployment_guide.md: step-by-step K8s deployment (prerequisites, namespace setup, apply manifests, verify pods, configure webhooks, run smoke tests)
- [x] T106 ✅ Update specs/001-customer-success-fte/quickstart.md with final verified commands after all components are built
- [x] T107 ✅ Run full transition test suite (T077–T082) and verify all pass
- [x] T108 ✅ Run full integration test suite (T083–T086) and verify all pass
- [x] T109 Run docker-compose stack and execute manual E2E validation across all 3 channels
- [x] T110 Run chaos test (T089) and generate tests/24h-report.md with all metrics

**Checkpoint**: All deliverables complete. All tests passing. Documentation verified. Ready for submission.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 Web Form)**: Depends on Phase 2 — MVP
- **Phase 4 (US2 Gmail)**: Depends on Phase 2 — can parallel with US1 after T032/T033
- **Phase 5 (US3 WhatsApp)**: Depends on Phase 2 — can parallel with US1/US2 after T032/T033
- **Phase 6 (US4 Cross-Channel)**: Depends on Phase 3 + at least one of Phase 4/5
- **Phase 7 (US5 Escalation)**: Depends on Phase 2 (guardrails in T026) — can start after Phase 2
- **Phase 8 (US6 Reports)**: Depends on Phase 2 — can start after enough data
- **Phase 9 (US7 Learning)**: Depends on Phase 3 (needs resolved tickets)
- **Phase 10 (US8 Transition)**: Can run parallel with Phases 3–9 (incubation artifacts)
- **Phase 11 (Testing)**: Depends on Phases 3–10
- **Phase 12 (Deploy)**: Depends on Phase 2 (can start early, finalize after Phase 11)
- **Phase 13 (Polish)**: Depends on all previous phases

### Parallel Opportunities

Within Phase 1 (Setup):
```
T001 → T002 (sequential)
T003, T004, T005, T007, T008, T009, T010, T011 (all parallel after T001)
T006 (after T002)
```

Within Phase 2 (Foundational):
```
T012 → T013 → T014 (sequential: schema → seed → connection)
T015, T016 (parallel after T014)
T017, T018 (parallel with T015/T016)
T019, T020, T021, T022, T023, T024, T025 (all 7 tools parallel after T015/T016)
T026, T027 (after tools)
T028 (after T026 + T027 + all tools)
```

Within Phase 10 (US8 Incubation):
```
T064 first, then T065–T071 all parallel (7 MCP tools)
T072, T073, T074, T075 all parallel (manifests + docs)
T076 last
```

Within Phase 11 (Testing):
```
T077–T081 all parallel (transition tests)
T082 after T077–T081 (edge cases reference patterns)
T083–T086 all parallel (integration tests)
T087, T088 parallel (chaos infra)
T089 after T087 + T088
T090 parallel with T087
```

Within Phase 12 (Deployment):
```
T091 first (Dockerfile)
T092 after T091
T093–T101 all parallel (K8s manifests)
T102 after T040 (health route)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Web Form)
4. **STOP and VALIDATE**: Test web form independently
5. Deploy locally via docker-compose

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Web Form) → Test independently → **MVP!**
3. US2 (Gmail) → Test independently → 2 channels working
4. US3 (WhatsApp) → Test independently → All 3 channels
5. US4 (Cross-Channel) → Test cross-channel switches
6. US5 (Escalation) → Test all guardrails
7. US6 (Reports) → Daily reports generating
8. US7 (Learning) → KB growing from resolved tickets
9. US8 (Transition) → Incubation artifacts + checklist
10. Testing → All test suites pass
11. Deploy → Docker + K8s ready
12. Polish → Documentation + chaos test → **Submission ready**

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total: 110 tasks across 13 phases
