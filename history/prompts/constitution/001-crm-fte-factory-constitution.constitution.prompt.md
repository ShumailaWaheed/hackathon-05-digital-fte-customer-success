---
id: 001
title: CRM FTE Factory Constitution
stage: constitution
date: 2026-02-23
surface: agent
model: claude-opus-4-6
feature: none
branch: main
user: Shumaila Waheed
command: /sp.constitution
labels: ["constitution", "hackathon-5", "crm-fte", "project-setup"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
tests:
  - none
---

## Prompt

Project: The CRM Digital FTE Factory Final Hackathon 5
Full Title: Build Your First 24/7 AI Employee - Customer Success Digital FTE (From Incubation to Production)

Core Identity & Purpose:
- Build a complete, production-grade, 24/7 Autonomous Customer Success Digital FTE (Full-Time Equivalent) AI Employee
- This is the FINAL Hackathon 5 of "The CRM Digital FTE Factory"
- Must fully implement the entire Agent Maturity Model (Stage 1: Incubation → Stage 2: Specialization)
- Goal: Replace a human Customer Success FTE costing $75,000+/year with an AI FTE that runs at <$1,000/year with 24/7 availability

Business Problem:
- SaaS company drowning in customer inquiries
- Must handle routine support 24/7 across 3 channels
- Track everything in its OWN PostgreSQL-based CRM/Ticket System (NO Salesforce, NO HubSpot)

Mandatory Channels (All 3 must be fully implemented):
1. Gmail (Email) - Gmail API + Pub/Sub or Polling webhook, formal detailed replies (max 500 words)
2. WhatsApp - Twilio Webhook + Twilio API replies (conversational, concise, max 300 chars preferred, auto-split long messages)
3. Web Support Form - MUST build COMPLETE standalone embeddable form UI (Next.js/HTML) with validation, not just backend

Core Requirements (Sab must be present):
- Build your OWN complete PostgreSQL CRM system (customers, customer_identifiers, conversations, messages, tickets, knowledge_base with pgvector embedding, channel_configs, agent_metrics tables)
- Full cross-channel conversation continuity (customer can switch Gmail ↔ WhatsApp ↔ Web Form and context remains)
- Always follow strict workflow: create_ticket → get_customer_history → search_knowledge_base → send_response
- Real-time sentiment analysis on every message
- Escalation rules + human handoff
- Daily customer sentiment report generation
- Learn from resolved tickets
- Multi-channel unified ticket ingestion via Kafka
- Production architecture: FastAPI + OpenAI Agents SDK + Kafka + PostgreSQL + Kubernetes

Incubation Phase (Stage 1):
- Use Claude Code as Agent Factory
- Create /context folder with company-profile.md, product-docs.md, sample-tickets.json, escalation-rules.md, brand-voice.md
- Build MCP Server with 5+ tools
- Define Agent Skills manifest
- Create full specs/customer-success-fte-spec.md + discovery-log.md

Transition Phase (Hours 15-18):
- Extract all discoveries into transition-checklist.md
- Convert MCP tools → OpenAI Agents SDK @function_tool with Pydantic models + full error handling
- Formalize system prompt with hard constraints and exact workflow order
- Create complete transition test suite

Specialization Phase (Stage 2 - Production):
- Full production folder structure
- Complete database schema.sql with all tables, indexes, pgvector
- Channel handlers: Gmail, WhatsApp (Twilio), Web Form (FastAPI + UI)
- Kafka message processor worker
- Kubernetes ready manifests + Dockerfile + docker-compose
- Metrics collection + daily reports

Hard Guardrails:
- Never discuss pricing, refunds, legal, competitors → immediate escalate
- Never promise features not in product-docs
- Never respond without creating a ticket first
- Never exceed channel max length
- Angry customer (sentiment < 0.3) or words like "human", "agent", "lawyer", "sue" → escalate
- Always use channel-appropriate tone and formatting

Tools (Both MCP and OpenAI SDK versions):
- search_knowledge_base, create_ticket, get_customer_history, escalate_to_human, send_response, analyze_sentiment, generate_daily_report

Success Criteria:
- Working Incubation prototype + all checklists
- Full production system on Kubernetes
- Complete Web Support Form UI
- All transition + E2E tests passing
- 24-hour multi-channel chaos test (100+ web forms, 50+ Gmail, 50+ WhatsApp, pod kills every 2 hours, <25% escalation, <3s P95 latency)
- Documentation + runbook

## Response snapshot

Created constitution v1.0.0 for "The CRM Digital FTE Factory — Hackathon 5" with 10 core principles:
I. Own Your CRM, II. Tri-Channel Mandate, III. Strict Workflow Order, IV. Cross-Channel Continuity, V. Guardrails & Escalation, VI. Sentiment-Driven Intelligence, VII. Agent Maturity Model Compliance, VIII. Dual Tool Implementation, IX. Production-Grade Architecture, X. Test-First & Chaos Readiness. Includes guardrails table, tech stack table, 3-phase workflow, and governance section.

## Outcome

- Impact: Established project constitution governing all development for the CRM Digital FTE Factory Hackathon 5
- Tests: none (constitution is a governance document)
- Files: .specify/memory/constitution.md (created v1.0.0)
- Next prompts: /sp.specify to create feature spec, /sp.plan for architecture
- Reflection: Comprehensive constitution covering all hackathon requirements; 10 principles map 1:1 to the major requirement areas

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Run /sp.specify to validate constitution principles translate into testable spec requirements
