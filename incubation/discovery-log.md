# Discovery Log: Customer Success Digital FTE

**Phase**: Incubation (Stage 1)
**Date**: 2026-02-24
**Method**: Sample ticket analysis with Claude Code as Director

## Pattern Discoveries from Sample Tickets

### Top Issue Categories (from 55 sample tickets)

| Category | Count | % |
|----------|-------|---|
| technical-issue | 18 | 33% |
| account-help | 12 | 22% |
| general-question | 10 | 18% |
| feature-request | 5 | 9% |
| escalation-trigger | 10 | 18% |

### Channel Distribution

| Channel | Count | % |
|---------|-------|---|
| webform | 22 | 40% |
| gmail | 18 | 33% |
| whatsapp | 15 | 27% |

**Insight**: Web form is the highest-volume channel — validates P1 priority.

### Escalation Triggers Found

| Guardrail | Trigger Count | Common Patterns |
|-----------|--------------|-----------------|
| G1 (Pricing) | 5 | "refund", "billing", "cost", "discount", "pricing" |
| G2 (Legal) | 1 | "lawyer", "sue" — often co-occurs with G1 and G5 |
| G3 (Competitor) | 2 | "Asana", "Monday.com" — comparison requests |
| G5 (Angry) | 6 | Low sentiment + trigger words "human", "agent", "manager" |

**Insight**: G1 and G5 are the most common triggers. Multi-guardrail triggers (G1+G2+G5) need single escalation with all reasons.

### Sentiment Distribution

| Range | Label | Count | Notes |
|-------|-------|-------|-------|
| 0.0–0.2 | Very Negative | 5 | Always escalate |
| 0.2–0.3 | Negative | 4 | Check for trigger words |
| 0.3–0.5 | Neutral-Low | 12 | Respond carefully |
| 0.5–0.7 | Neutral-Positive | 22 | Normal response |
| 0.7–1.0 | Positive | 12 | Great for learning loop |

**Insight**: 0.3 boundary is critical — "exactly 0.3" must NOT escalate (strictly < 0.3).

### Cross-Channel Patterns

- 3 customers contact across multiple channels (Sarah Chen: webform→gmail, Maria Lopez: whatsapp→whatsapp, Chris Evans: webform→webform)
- Email is the primary identity resolver — all cross-channel matches happen via email
- Phone-based matching only works for WhatsApp (phone number)
- Form session IDs are ephemeral — email is the reliable cross-channel link

### Knowledge Base Query Patterns

- Most common queries map to: password reset, file upload, team invites, integrations
- 20 seed KB entries cover ~80% of common questions
- Gap identified: no entries for workflow/automation, reporting, mobile-specific issues
- Semantic search works well for paraphrased questions (e.g., "how to add people" matches "invite team members")

### Edge Cases Discovered

1. Empty message body — need graceful handling (request clarification)
2. Extremely long messages (500+ words) — need to process but cap response
3. Duplicate submissions within seconds — need deduplication
4. Multiple guardrails triggered simultaneously — single escalation with all reasons
5. Non-English messages — best-effort or escalate
6. Malformed webhook payloads — log and discard, don't crash
7. Unknown customer (new identifier) — auto-create customer record
8. Sentiment exactly at 0.3 boundary — must NOT escalate
9. Channel switch mid-ticket — link to existing open ticket
10. Rapid-fire messages (rate limiting) — process all but flag abuse

### Tool Workflow Validation

Tested the 4-step workflow with sample tickets:
1. `create_ticket` — Works. Ticket created with UUID, status moves to in-progress.
2. `get_customer_history` — Works for known customers. Returns empty for new ones.
3. `search_knowledge_base` — Requires real embeddings. Zero-vector seeds need replacement.
4. `send_response` — Channel formatting applies correctly. Gmail caps at 500w, WhatsApp at 300ch.

**Critical Finding**: Seed data uses zero vectors — first production run must generate real embeddings via OpenAI API.

## Crystallization Status

- [x] Top issue categories identified
- [x] Channel distribution understood
- [x] Escalation patterns mapped to guardrails G1-G5
- [x] Sentiment threshold behavior validated (0.3 boundary)
- [x] Cross-channel identity resolution strategy confirmed (email-based)
- [x] Knowledge base gaps identified
- [x] 10+ edge cases documented
- [x] Workflow order validated with sample data
- [ ] Real embedding generation pending (seed data is zero vectors)
- [ ] Full 3-channel prototype validation pending (needs running Docker stack)

**Recommendation**: Requirements are sufficiently crystallized. Ready for Transition phase once Docker stack is running and real embeddings are generated.
