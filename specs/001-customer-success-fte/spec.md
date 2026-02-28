# Feature Specification: Customer Success Digital FTE

**Feature Branch**: `001-customer-success-fte`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "Build 24/7 AI Customer Success Digital FTE with omnichannel support per constitution v1.1.0"
**Constitution**: v1.1.0 (all principles enforced)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Web Form Support Request (Priority: P1)

A customer visits the SaaS company website and needs help with a product issue. They fill out a standalone embeddable web support form with their name, email, issue category, and message. The system creates a ticket, retrieves any prior history for this customer, searches the knowledge base for relevant answers, and delivers a semi-formal response on-screen with an email copy as fallback.

**Why this priority**: The web form is the lowest-friction channel for new customers and proves the end-to-end workflow (ticket creation → history → knowledge base → response) without external API dependencies (no Gmail API or Twilio needed). A solo developer can test this locally on day one.

**Independent Test**: Submit a form through the web UI and verify a ticket is created, knowledge base is searched, and a response is displayed — all without Gmail or WhatsApp being configured.

**Acceptance Scenarios**:

1. **Given** the web form is loaded in a browser, **When** a customer fills in all required fields (name, email, category, message) and submits, **Then** a ticket is created in the system before any other processing occurs.
2. **Given** a valid form submission, **When** the system processes the message, **Then** it follows the exact sequence: create_ticket → get_customer_history → search_knowledge_base → send_response.
3. **Given** a customer who previously contacted via Gmail, **When** they submit a web form using the same email address, **Then** the system retrieves their full cross-channel conversation history.
4. **Given** an inbound message containing the word "refund", **When** the system analyzes the content, **Then** it immediately escalates to a human agent with reason "pricing/refund discussion detected" instead of generating an AI response.
5. **Given** any inbound message, **When** the system processes it, **Then** real-time sentiment analysis runs and the score is stored alongside the message.
6. **Given** a form submission with missing required fields, **When** the customer attempts to submit, **Then** client-side validation prevents submission and displays specific error messages.

---

### User Story 2 — Gmail Email Support (Priority: P2)

A customer sends an email to the company support address. The system receives the email via Gmail API, creates a ticket, checks customer history across all channels, searches the knowledge base, and sends a formal detailed reply (up to 500 words) back via Gmail with proper greeting and signature.

**Why this priority**: Email is the most common B2B support channel and validates the Gmail API integration and formal tone formatting. Depends on the core workflow proven in P1.

**Independent Test**: Send an email to the support inbox and verify a formal reply arrives within 30 seconds containing relevant knowledge base content, with proper greeting and signature, capped at 500 words.

**Acceptance Scenarios**:

1. **Given** a customer sends an email to the support address, **When** the system receives it via Gmail API, **Then** a ticket is created before any other action.
2. **Given** a valid support email, **When** the system generates a reply, **Then** the reply is formal in tone, includes a greeting and signature, and does not exceed 500 words.
3. **Given** a customer who previously used WhatsApp, **When** they send an email from the address linked to the same customer record, **Then** their full WhatsApp conversation history is available to the agent.
4. **Given** an email mentioning a competitor product by name, **When** the system detects competitor keywords, **Then** it escalates immediately without providing a comparison or opinion.
5. **Given** an email from an angry customer (sentiment score < 0.3), **When** sentiment analysis completes, **Then** the system escalates with an empathy message and full conversation context.

---

### User Story 3 — WhatsApp Conversational Support (Priority: P3)

A customer sends a WhatsApp message to the company support number. The system receives the message via Twilio webhook, creates a ticket, retrieves cross-channel history, searches the knowledge base, and replies via Twilio API in a conversational, concise style (300 characters preferred, auto-split if longer).

**Why this priority**: WhatsApp adds the real-time conversational channel and validates Twilio integration, message splitting logic, and casual tone formatting. Depends on the core workflow proven in P1 and P2.

**Independent Test**: Send a WhatsApp message to the Twilio number and verify a concise, casual reply arrives within 30 seconds, correctly split if it exceeds 300 characters.

**Acceptance Scenarios**:

1. **Given** a customer sends a WhatsApp message, **When** the Twilio webhook delivers it, **Then** a ticket is created before any other processing.
2. **Given** a knowledge base answer that exceeds 300 characters, **When** the system formats the reply for WhatsApp, **Then** it auto-splits into multiple messages at natural sentence boundaries.
3. **Given** a WhatsApp message containing the word "lawyer", **When** trigger word detection runs, **Then** the system escalates immediately with empathy and context.
4. **Given** a customer who previously contacted via web form, **When** they message on WhatsApp using the phone number linked to the same customer record, **Then** their web form history is included in the context.
5. **Given** any WhatsApp reply, **When** the system sends it, **Then** the tone is conversational and casual, not formal.

---

### User Story 4 — Cross-Channel Continuity (Priority: P4)

A customer starts a conversation on one channel and continues on another. The system recognizes them across channels via their email address, phone number, or form session ID, and maintains full conversation context regardless of which channel they use.

**Why this priority**: Cross-channel continuity is a differentiating feature that proves the unified customer identity system works. Depends on at least two channels being operational (P1 + P2 or P3).

**Independent Test**: Contact support via web form, then send a follow-up via Gmail using the same email. Verify the Gmail response references the web form conversation.

**Acceptance Scenarios**:

1. **Given** a customer who submitted a web form with email "user@example.com", **When** they later send an email from "user@example.com", **Then** the system links both interactions to the same customer record.
2. **Given** a customer with interactions on all 3 channels, **When** any channel receives a new message, **Then** the full history from all channels is available to the agent for context.
3. **Given** two different customers with separate identifiers, **When** their messages arrive, **Then** the system never merges their records or shares cross-customer data.
4. **Given** a customer identifier (email or phone) not yet in the system, **When** a new message arrives, **Then** the system creates a new customer record and links the identifier.

---

### User Story 5 — Escalation and Human Handoff (Priority: P5)

When a conversation triggers any guardrail (pricing, legal, competitor, angry customer, trigger words), the system immediately stops AI processing, logs the reason, and hands off to a human agent with full context including all conversation history, sentiment scores, and the specific trigger.

**Why this priority**: Escalation is a safety-critical feature that protects the company from liability. Depends on the core workflow being operational.

**Independent Test**: Send a message containing "I want a refund" and verify the system escalates instead of responding, with the correct reason logged.

**Acceptance Scenarios**:

1. **Given** a message containing pricing keywords ("price", "refund", "billing", "cost", "discount"), **When** guardrail G1 triggers, **Then** the system escalates with reason "pricing/refund discussion" and does not generate an AI response.
2. **Given** a message containing legal keywords ("lawyer", "sue", "legal", "lawsuit", "court"), **When** guardrail G2 triggers, **Then** the system escalates with reason and full context.
3. **Given** a message with sentiment score below 0.3, **When** guardrail G5 triggers, **Then** the system sends an empathy message before escalating.
4. **Given** a message containing the word "human" or "manager", **When** trigger word detection runs, **Then** the system escalates with acknowledgment.
5. **Given** a ticket being closed, **When** the most recent customer sentiment is negative, **Then** guardrail G9 blocks closure and flags for human review.

---

### User Story 6 — Daily Sentiment Report (Priority: P6)

At the end of each day, the system generates a report summarizing customer sentiment trends, flagging negative patterns, listing top issues, and tracking escalation rates across all channels.

**Why this priority**: Reporting provides business intelligence that justifies the AI FTE's value. Depends on sufficient message volume and sentiment data (P1–P5).

**Independent Test**: After processing 20+ messages, trigger daily report generation and verify it contains sentiment trends, top issues, and escalation stats.

**Acceptance Scenarios**:

1. **Given** a day with 50+ processed messages, **When** the daily report generates, **Then** it includes average sentiment score, sentiment trend (improving/declining), top 5 issue categories, and escalation rate.
2. **Given** messages from all 3 channels, **When** the report generates, **Then** it includes a per-channel breakdown of volume and sentiment.
3. **Given** no messages for a given day, **When** the report generates, **Then** it produces a valid report indicating zero activity.

---

### User Story 7 — Knowledge Base Learning Loop (Priority: P7)

When a ticket is resolved successfully (positive customer sentiment at closure), the system extracts the question-answer pair and adds it as a new vector embedding in the knowledge base, improving future response accuracy.

**Why this priority**: Continuous learning differentiates a production AI FTE from a static chatbot. Depends on the full workflow and resolution flow being operational.

**Independent Test**: Resolve a ticket with positive sentiment. Submit a similar question and verify the knowledge base now returns the learned answer.

**Acceptance Scenarios**:

1. **Given** a ticket resolved with positive customer sentiment (>= 0.5), **When** resolution is confirmed, **Then** the Q&A pair is embedded and added to the knowledge base.
2. **Given** a newly added knowledge base entry, **When** a similar question arrives, **Then** the search returns the learned answer with relevance above the minimum threshold.
3. **Given** a ticket resolved after escalation (not by AI), **When** resolution occurs, **Then** the system still captures the Q&A for learning if the human agent marks it as reusable.

---

### User Story 8 — Incubation to Production Transition (Priority: P8)

The development team completes the incubation phase (MCP prototype), runs the transition checklist to crystallize requirements, converts all tools to production format, and deploys the production system to a container orchestration platform.

**Why this priority**: The maturity model transition is the architectural backbone of the entire project. It runs parallel to feature work and governs how all other stories get deployed.

**Independent Test**: Run the transition test suite (pricing, angry customer, length, order, cross-channel, edge cases) and verify all tests pass against the production agent.

**Acceptance Scenarios**:

1. **Given** the incubation prototype handles all 3 channels, **When** the transition checklist is executed, **Then** every MCP tool has a corresponding production tool with validated input/output models.
2. **Given** the production system prompt, **When** the agent processes any message, **Then** it follows the strict workflow order without exception.
3. **Given** the production deployment, **When** the 24-hour chaos test runs (100+ web forms, 50+ Gmail, 50+ WhatsApp, pod kills every 2 hours), **Then** escalation rate stays below 20%, accuracy exceeds 85%, cross-channel ID accuracy exceeds 95%, P95 latency stays under 3 seconds, and uptime remains at 99.9%.

---

### Edge Cases

1. **Duplicate submissions**: Customer submits the same web form twice within seconds — system deduplicates and links to the same ticket.
2. **Unknown customer**: Message arrives with an identifier not in the system — system creates a new customer record and proceeds normally.
3. **Empty message body**: Customer sends a blank email or WhatsApp message — system creates a ticket and requests clarification instead of crashing.
4. **Extremely long message**: Customer sends a 10,000-word email — system processes it normally but caps the reply at 500 words.
5. **Simultaneous multi-channel**: Customer sends a web form and WhatsApp message at the same time about the same issue — system creates two tickets but links them to the same conversation.
6. **Knowledge base returns no results**: Query finds no relevant answers — system responds honestly ("I don't have an answer for that") and escalates.
7. **Sentiment borderline**: Sentiment score is exactly 0.3 — system treats it as non-escalation (threshold is strictly less than 0.3).
8. **Multiple guardrail triggers**: Message triggers both pricing AND legal guardrails — system escalates once with all reasons listed.
9. **Channel switching mid-ticket**: Customer opens ticket via Gmail, responds on WhatsApp — system links the response to the existing open ticket.
10. **Malformed webhook payload**: Twilio sends a corrupted payload — system logs the error, does not crash, and does not create a partial ticket.
11. **Rate limiting**: Same customer sends 50 messages in 1 minute — system processes all but flags for potential abuse.
12. **Non-English message**: Customer writes in a non-English language — system attempts to respond in the same language or escalates if unsupported.

## Clarifications

### Session 2026-02-23

- Q: What triggers ticket state transitions (open/in-progress/escalated/resolved/closed)? → A: Fully automatic — open→in-progress on workflow start, in-progress→resolved on successful response with non-negative sentiment, resolved→closed after 24h no reply, escalated requires human to resolve. G9 blocks closure if sentiment negative.
- Q: What happens when external channel APIs (Gmail, Twilio) are unavailable? → A: Queue-and-retry with exponential backoff (max 3 attempts). If all fail, mark ticket "delivery-failed" and attempt alternate channel. Log for human review.
- Q: How do operators monitor system health in real-time? → A: Lightweight — structured JSON logs to stdout (container-native) + `/health` endpoint returning DB, Kafka, and channel API status for orchestration probes.

## Requirements *(mandatory)*

### Functional Requirements

**Core Workflow**

- **FR-001**: System MUST create a ticket for every inbound message before any other processing occurs (Guardrail G6).
- **FR-002**: System MUST follow the exact processing sequence: create_ticket → get_customer_history → search_knowledge_base → send_response, with no steps skipped or reordered (Constitution Principle III).
- **FR-003**: System MUST run sentiment analysis on every inbound message and store the score with the message record.

**Channels**

- **FR-004**: System MUST receive and process emails via Gmail API (Pub/Sub or polling).
- **FR-005**: System MUST send email replies in formal tone with greeting and signature, capped at 500 words.
- **FR-006**: System MUST receive WhatsApp messages via Twilio webhook.
- **FR-007**: System MUST send WhatsApp replies in conversational tone, preferring 300 characters, auto-splitting longer messages at sentence boundaries.
- **FR-008**: System MUST provide a standalone embeddable web support form with client-side validation for required fields (name, email, category, message).
- **FR-009**: Web form replies MUST be delivered on-screen via the form interface, with an email copy sent as fallback.
- **FR-010**: System MUST enforce channel-appropriate tone: Gmail=formal, WhatsApp=conversational, Web=semi-formal (Guardrail G8).

**Customer Identity & Continuity**

- **FR-011**: System MUST maintain a unified customer record that maps email addresses, phone numbers, and form session IDs via a customer identifiers table.
- **FR-012**: System MUST resolve customer identity across channels with >95% accuracy.
- **FR-013**: System MUST include full cross-channel conversation history when generating any response.

**Guardrails & Escalation**

- **FR-014**: System MUST immediately escalate (no AI response) when pricing/refund keywords are detected: "price", "refund", "billing", "cost", "discount" (G1).
- **FR-015**: System MUST immediately escalate when legal keywords are detected: "lawyer", "sue", "legal", "lawsuit", "court" (G2).
- **FR-016**: System MUST immediately escalate when competitor brand names are mentioned (G3).
- **FR-017**: System MUST never promise features not documented in the product knowledge base (G4).
- **FR-018**: System MUST escalate with empathy when sentiment < 0.3 or trigger words "human", "agent", "manager", "sue", "lawyer" are detected (G5).
- **FR-019**: System MUST never exceed channel length limits: 500 words for Gmail, 300 characters preferred for WhatsApp (G7).
- **FR-020**: System MUST check customer sentiment before closing any ticket; block closure if sentiment is negative (G9).
- **FR-021**: Every escalation MUST include: ticket ID, reason, full conversation history, sentiment scores, and the specific trigger.

**Knowledge Base & Learning**

- **FR-022**: System MUST search the knowledge base using semantic similarity (vector embeddings) for every inbound message.
- **FR-023**: System MUST add resolved ticket Q&A pairs as new vector embeddings in the knowledge base when ticket sentiment is positive (>= 0.5).
- **FR-024**: Knowledge base search MUST return up to 5 relevant results by default.

**Reporting & Metrics**

- **FR-025**: System MUST generate a daily sentiment report covering: average sentiment, trends, top issues, escalation rate, and per-channel breakdown.
- **FR-026**: System MUST track and store agent performance metrics: response times, resolution rates, escalation rates, accuracy scores.

**Data & Storage**

- **FR-027**: System MUST use a self-built CRM with these entities: customers, customer_identifiers, conversations, messages, tickets, knowledge_base, channel_configs, agent_metrics (Constitution Principle I).
- **FR-028**: System MUST NOT integrate with any external CRM (no Salesforce, no HubSpot, no third-party ticketing).

**Maturity Model**

- **FR-029**: System MUST be developed in two stages: Stage 1 (Incubation with MCP tools) → Stage 2 (Specialization with production tools) per the Agent Maturity Model.
- **FR-030**: Every tool MUST exist in dual form: MCP Server version (incubation) and production version with validated input/output models (Constitution Principle VIII).
- **FR-031**: System MUST include 7 tools in both forms: search_knowledge_base, create_ticket, get_customer_history, escalate_to_human, send_response, analyze_sentiment, generate_daily_report.

**Infrastructure**

- **FR-032**: All channel messages MUST flow through a unified message queue for ingestion.
- **FR-033**: System MUST be deployable to a container orchestration platform with manifests, container definitions, and a local development compose file.
- **FR-034**: System MUST survive infrastructure disruptions (pod kills) without data loss or guardrail violations.
- **FR-035**: When an external channel API (Gmail, Twilio) fails, the system MUST queue the outbound message for retry with exponential backoff (max 3 attempts). If all retries fail, the ticket MUST be marked "delivery-failed" and the system MUST attempt delivery via an alternate channel if available. Failed deliveries MUST be logged for human review.
- **FR-036**: System MUST emit structured JSON logs to stdout for all operations (ticket creation, workflow steps, escalations, errors, API calls) to enable container-native log aggregation.
- **FR-037**: System MUST expose a `/health` endpoint returning current status of core dependencies (database connection, message queue connection, channel API availability) for orchestration liveness/readiness probes.

### Ticket Lifecycle

Ticket state transitions are **automatic** unless escalated:

1. **open** → **in-progress**: When the workflow begins (create_ticket completes).
2. **in-progress** → **escalated**: When any guardrail (G1–G5) triggers. Requires human agent to resolve.
3. **in-progress** → **resolved**: When the AI delivers a successful response and customer sentiment is non-negative (>= 0.3).
4. **resolved** → **closed**: Automatically after 24 hours with no further customer reply. Guardrail G9 blocks closure if most recent sentiment is negative — ticket reverts to in-progress for human review.
5. **escalated** → **resolved**: Only by human agent action.

Human agents may override any transition at any time.

### Key Entities

- **Customer**: A person who contacts support. Has a name, creation date, and one or more identifiers. Central entity linking all interactions across channels.
- **Customer Identifier**: Maps a specific email, phone number, or form session ID to a Customer. Enables cross-channel identity resolution.
- **Conversation**: A thread of related messages for a customer, potentially spanning multiple channels. Groups messages by topic or time window.
- **Message**: A single inbound or outbound communication. Carries content, channel source, timestamp, sentiment score, and a link to its conversation and ticket.
- **Ticket**: A trackable support case created for every inbound message. Has priority, status (open/in-progress/escalated/resolved/closed), channel of origin, and resolution metadata.
- **Knowledge Base Entry**: A searchable article or Q&A pair with vector embedding for semantic similarity search. Grows over time as resolved tickets feed new entries.
- **Channel Config**: Per-channel settings including tone rules, length limits, API credentials reference, and formatting templates.
- **Agent Metric**: A performance data point tracking response time, resolution outcome, escalation reason, and accuracy for a specific interaction.

### Assumptions

- The SaaS company has a Google Workspace account with Gmail API access enabled.
- A Twilio account with WhatsApp Business API sandbox or production number is available.
- The development environment supports Docker and has access to a container registry.
- OpenAI API access is available for the Agents SDK and embedding generation.
- A PostgreSQL instance with pgvector extension is available (local for development, managed for production).
- The 24-hour chaos test will use scripted message generators, not real customer traffic.
- The web support form will be embedded via iframe or script tag, not hosted as a full website.
- Customer identity resolution uses exact match on email/phone; fuzzy matching is out of scope.

### Out of Scope

- Full customer-facing website (only the standalone web support form)
- Integration with any external CRM or ticketing system
- Mobile apps or desktop clients
- Advanced analytics dashboard (only daily sentiment report via tool)
- Multi-tenant support
- Billing or pricing module
- Authentication system beyond basic customer identification
- Production secrets management or CI/CD pipelines
- Multi-language support beyond best-effort detection
- Fuzzy customer identity matching (exact match only)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every inbound message results in a ticket being created before any response is generated — zero exceptions across all channels.
- **SC-002**: Customers receive a response within 30 seconds of submitting a message on any channel.
- **SC-003**: A customer who contacts via web form and later follows up via Gmail receives a response that references their prior web form conversation — cross-channel identity resolution achieves >95% accuracy.
- **SC-004**: The system correctly escalates 100% of messages containing guardrail trigger words (pricing, legal, competitor, anger) without generating an AI response.
- **SC-005**: Knowledge base search returns relevant answers for >85% of common product questions.
- **SC-006**: Less than 20% of all messages result in escalation to a human agent during normal operation.
- **SC-007**: Gmail replies never exceed 500 words; WhatsApp messages auto-split correctly when exceeding 300 characters.
- **SC-008**: Daily sentiment reports generate successfully and include per-channel breakdown, trend data, and top issue categories.
- **SC-009**: After resolving 10 tickets, at least 1 new knowledge base entry is automatically added and retrievable via semantic search.
- **SC-010**: During a 24-hour stress test with 200+ messages across 3 channels and periodic infrastructure disruptions, the system maintains 99.9% uptime with P95 message processing time under 3 seconds.
- **SC-011**: The system operates at less than $85/month infrastructure cost ($1,020/year), representing a 98.6% cost reduction from a $75,000/year human FTE.
- **SC-012**: All 7 tools exist in both incubation (MCP) and production formats, and the transition test suite passes with zero failures.
