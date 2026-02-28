# Transition Checklist: Incubation → Specialization

**Purpose**: Verify all MCP tools have production equivalents, system prompt is formalized, all guardrails encoded, and workflow order enforced.
**Date**: 2026-02-24
**Constitution**: v1.1.0 Principle VII (Agent Maturity Model)

## Tool Parity (Principle VIII)

| # | Tool | MCP Version | Production Version | Parity |
|---|------|-------------|-------------------|--------|
| 1 | search_knowledge_base | incubation/mcp_server/tools/search_knowledge_base.py | production/agent/tools/search_knowledge_base.py | ✅ |
| 2 | create_ticket | incubation/mcp_server/tools/create_ticket.py | production/agent/tools/create_ticket.py | ✅ |
| 3 | get_customer_history | incubation/mcp_server/tools/get_customer_history.py | production/agent/tools/get_customer_history.py | ✅ |
| 4 | escalate_to_human | incubation/mcp_server/tools/escalate_to_human.py | production/agent/tools/escalate_to_human.py | ✅ |
| 5 | send_response | incubation/mcp_server/tools/send_response.py | production/agent/tools/send_response.py | ✅ |
| 6 | analyze_sentiment | incubation/mcp_server/tools/analyze_sentiment.py | production/agent/tools/analyze_sentiment.py | ✅ |
| 7 | generate_daily_report | incubation/mcp_server/tools/generate_daily_report.py | production/agent/tools/generate_daily_report.py | ✅ |

**Result**: 7/7 tools have dual implementations ✅

## Production Enhancements Over MCP

| Enhancement | MCP | Production |
|-------------|-----|-----------|
| Input validation | Basic dict args | Pydantic models with constraints |
| Error handling | Try/except returns string | Structured error responses |
| Connection management | Direct asyncpg.connect() | Connection pool (min=5, max=20) |
| Message queue | None | Kafka publish to topics |
| Logging | print() | Structured JSON to stdout |

## System Prompt Verification

- [x] Strict workflow order encoded (create_ticket → get_history → search_kb → send_response)
- [x] All guardrails G1-G9 documented with keywords and actions
- [x] Channel formatting rules (Gmail=formal/500w, WhatsApp=casual/300ch, Web=semi-formal)
- [x] Escalation format specified (ticket_id, reason, history, sentiment)
- [x] Response guidelines (KB-only, no hallucination, no feature promises)
- [x] Located at: production/agent/system_prompt.txt

## Guardrail Encoding

| # | Guardrail | Encoded In | Enforcement |
|---|-----------|-----------|-------------|
| G1 | No pricing/refund | guardrails.py + system_prompt.txt | Keyword detection |
| G2 | No legal discussion | guardrails.py + system_prompt.txt | Keyword detection |
| G3 | No competitor discussion | guardrails.py + system_prompt.txt | Name matching |
| G4 | No false promises | system_prompt.txt | Agent instruction |
| G5 | Angry customer | guardrails.py + system_prompt.txt | Sentiment + trigger words |
| G6 | Ticket-first | agent.py workflow | Programmatic enforcement |
| G7 | Channel length | send_response.py + system_prompt.txt | Config-based limits |
| G8 | Channel tone | channel_configs table + system_prompt.txt | Config-based tone |
| G9 | Sentiment-before-close | guardrails.py + send_response.py | Programmatic check |

**Result**: All 9 guardrails encoded ✅

## Workflow Order Enforcement

- [x] System prompt specifies exact order
- [x] agent.py `process_message()` enforces order programmatically
- [x] Logs every step with ticket_id for audit trail
- [x] Guardrail pre-check runs before agent response generation

## Database Ready

- [x] schema.sql has all 8 tables with indexes and constraints
- [x] seed.sql has 20 KB entries and 3 channel configs
- [x] connection.py provides async pool with health check
- [x] repositories.py has CRUD for all entities
- [ ] Real embeddings need generation (seed uses zero vectors)

## Transition Tests Required

Before deploying production system, these tests MUST pass:

- [ ] Pricing guardrail test (G1)
- [ ] Angry customer escalation test (G5)
- [ ] Channel length enforcement test (G7)
- [ ] Tool order compliance test (Principle III)
- [ ] Cross-channel continuity test (Principle IV)
- [ ] 10+ edge case tests

## Anti-Pattern Check

- [x] NOT premature specialization — incubation prototype complete first
- [x] NOT perpetual incubation — transitioning to production tools
- [x] NOT skipping incubation — MCP tools were built and tested

## Readiness Decision

**Status**: Ready for Transition ✅
**Rationale**: All 7 tools implemented in dual form. Guardrails encoded. Workflow enforced programmatically. Discovery complete with 12 edge cases documented. Requirements are crystallized.
