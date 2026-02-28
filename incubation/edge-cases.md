# Edge Cases: Customer Success Digital FTE

**Phase**: Incubation
**Minimum Required**: 10 (Constitution Principle VII)
**Documented**: 12

---

## EC-01: Duplicate Submissions

**Scenario**: Customer submits the same web form twice within seconds.
**Expected**: System deduplicates — second submission links to same ticket.
**Detection**: Match on (customer_email + issue content hash + timestamp within 60s).
**Handling**: Return existing ticket_id instead of creating duplicate.
**Sample Ticket**: #38 (Chris Evans duplicate of #37)

## EC-02: Unknown Customer

**Scenario**: Message arrives with an identifier not in the system (new email/phone).
**Expected**: System creates a new customer record and links the identifier automatically.
**Handling**: `resolve_customer()` creates customer + identifier on miss, proceeds normally.
**Sample Ticket**: #39 (newuser12345@tempmail.com)

## EC-03: Empty Message Body

**Scenario**: Customer sends a blank email or WhatsApp message (empty string).
**Expected**: System creates a ticket and requests clarification instead of crashing.
**Handling**: Create ticket with issue="[Empty message]", respond "Could you please provide more details about your issue?"
**Sample Ticket**: #34 (Daniel Clark empty webform)

## EC-04: Extremely Long Message

**Scenario**: Customer sends a 10,000-word email.
**Expected**: System processes it normally but caps the reply at 500 words (Gmail) or 300 chars (WhatsApp).
**Handling**: Full message stored in DB. Knowledge base search uses first 500 words. Response length enforced by channel config.
**Sample Ticket**: #37 (Chris Evans long complaint)

## EC-05: Simultaneous Multi-Channel

**Scenario**: Customer sends a web form and WhatsApp message at the same time about the same issue.
**Expected**: System creates two tickets but links them to the same customer and conversation.
**Handling**: Both tickets created (G6 mandate). Identity resolver links both to same customer_id.

## EC-06: Knowledge Base Returns No Results

**Scenario**: Query finds no relevant answers (all similarities below threshold).
**Expected**: System responds honestly "I don't have an answer for that" and escalates.
**Handling**: If top KB result similarity < 0.3, respond with honesty message + escalate.

## EC-07: Sentiment Borderline (Exactly 0.3)

**Scenario**: Customer's message scores exactly 0.3 on sentiment analysis.
**Expected**: System does NOT escalate. Threshold is strictly less than 0.3 (< 0.3).
**Handling**: `check_angry_customer()` uses `<` not `<=`. Score 0.3 = not angry.
**Sample Ticket**: #42 (Boundary Tester)

## EC-08: Multiple Guardrail Triggers

**Scenario**: Message triggers both pricing AND legal AND angry customer guardrails.
**Expected**: System escalates ONCE with ALL reasons listed in a single escalation.
**Handling**: `check_all()` collects all triggered guardrails, joins reasons with ";".
**Sample Ticket**: #40 (discount + lawyer + human + manager = G1+G2+G5)

## EC-09: Channel Switch Mid-Ticket

**Scenario**: Customer opens ticket via web form, responds via Gmail about the same issue.
**Expected**: System links the Gmail response to the existing open ticket.
**Handling**: Identity resolver finds customer by email → get_customer_history returns webform messages → conversation continuity maintained.
**Sample Tickets**: #35, #44 (Sarah Chen webform→gmail→gmail)

## EC-10: Malformed Webhook Payload

**Scenario**: Twilio sends a corrupted or incomplete webhook payload.
**Expected**: System logs the error, does not crash, and does not create a partial ticket.
**Handling**: Validate payload schema before processing. On validation error: log structured error, return 400, do not create ticket.
**Sample Ticket**: #43 (INVALID phone, null name/message)

## EC-11: Rate Limiting

**Scenario**: Same customer sends 50 messages in 1 minute.
**Expected**: System processes all messages but flags the customer for potential abuse.
**Handling**: Track message count per customer per minute. If > 30/min, add "abuse-flagged" to ticket metadata. Continue processing.
**Sample Ticket**: #45 (Speed Tester rapid-fire)

## EC-12: Non-English Message

**Scenario**: Customer writes in Chinese, Japanese, or other non-English language.
**Expected**: System attempts to respond in the same language. If unsupported, escalate.
**Handling**: OpenAI model handles multilingual. Sentiment analysis works across languages. If response quality is uncertain, add note "language: detected [lang]" to metadata.
**Sample Tickets**: #20 (Japanese), #54 (Chinese)

---

## Summary Table

| # | Edge Case | Guardrail | Priority | Sample |
|---|-----------|-----------|----------|--------|
| EC-01 | Duplicate submissions | G6 | High | #38 |
| EC-02 | Unknown customer | — | High | #39 |
| EC-03 | Empty message body | G6 | Medium | #34 |
| EC-04 | Extremely long message | G7 | Medium | #37 |
| EC-05 | Simultaneous multi-channel | G6 | Medium | — |
| EC-06 | KB no results | G4 | High | — |
| EC-07 | Sentiment exactly 0.3 | G5 | High | #42 |
| EC-08 | Multiple guardrail triggers | G1+G2+G5 | High | #40 |
| EC-09 | Channel switch mid-ticket | — | Medium | #35,#44 |
| EC-10 | Malformed webhook | — | High | #43 |
| EC-11 | Rate limiting | — | Low | #45 |
| EC-12 | Non-English message | — | Low | #20,#54 |
