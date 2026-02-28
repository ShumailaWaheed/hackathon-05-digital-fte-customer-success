# Research: Customer Success Digital FTE

**Date**: 2026-02-23 | **Plan**: [plan.md](./plan.md)

## R1: Gmail Ingestion Method

**Decision**: Polling (15-second interval)
**Rationale**: Pub/Sub requires Google Cloud project with domain
  verification and push endpoint configuration — significant setup
  overhead for a hackathon. Polling via `users.messages.list` with
  `after:` query parameter is simpler, sufficient for <50 emails/day.
**Alternatives**: Gmail Pub/Sub (real-time but complex setup),
  IMAP polling (deprecated for OAuth2 service accounts).
**Upgrade path**: Switch to Pub/Sub post-hackathon for real-time.

## R2: Embedding Model for Knowledge Base

**Decision**: OpenAI text-embedding-3-small (1536 dimensions)
**Rationale**: 5x cheaper than text-embedding-3-large ($0.02/1M tokens
  vs $0.13/1M). 1536 dimensions provide sufficient semantic resolution
  for product support Q&A. pgvector IVFFlat index performs well at
  this dimensionality.
**Alternatives**: text-embedding-3-large (3072 dims, higher accuracy,
  higher cost), sentence-transformers local model (free but slower,
  no GPU in K8s budget).
**Risk**: If accuracy <85%, upgrade to 3-large and re-embed.

## R3: Sentiment Analysis Approach

**Decision**: OpenAI gpt-4o-mini with structured output (float 0.0–1.0)
**Rationale**: Handles sarcasm, context, multilingual nuance. Cost:
  ~$0.001/message. Pydantic structured output ensures consistent
  float response. Faster than gpt-4o, sufficient for sentiment.
**Alternatives**: VADER/TextBlob (free, rule-based, poor on nuance),
  AWS Comprehend (additional dependency), fine-tuned classifier
  (training overhead).

## R4: Kafka Configuration

**Decision**: Self-hosted Apache Kafka in KRaft mode (no Zookeeper)
**Rationale**: KRaft mode eliminates Zookeeper dependency (simpler
  Docker Compose, fewer pods in K8s). Single broker sufficient for
  hackathon volume. 4 topics: inbound-messages, outbound-responses,
  escalations, metrics.
**Alternatives**: Confluent Cloud (managed but costs), Redis Streams
  (simpler but doesn't meet "Kafka" requirement), RabbitMQ (not Kafka).
**Config**: 1 broker, replication-factor=1 (hackathon), retention=7d.

## R5: Web Form Embedding Strategy

**Decision**: Next.js standalone form with iframe embed option
**Rationale**: Next.js provides React component model with built-in
  form handling, Zod validation, and TypeScript. Embeddable via
  iframe with postMessage API for cross-origin response delivery.
  Also works standalone at its own URL.
**Alternatives**: Plain HTML + vanilla JS (simpler but no component
  model), React SPA (needs separate build tooling), Web Component
  (browser support complexity).

## R6: WhatsApp Message Splitting Algorithm

**Decision**: Split at sentence boundaries (`.!?` + space), max 300
  characters per segment, sequential delivery with 500ms delay.
**Rationale**: Sentence-boundary splitting preserves readability.
  500ms delay prevents out-of-order delivery on Twilio. If a single
  sentence exceeds 300 chars, split at nearest space before 300.
**Alternatives**: Hard truncate at 300 (loses information), split at
  word boundaries only (awkward mid-sentence breaks).

## R7: Retry and Failure Recovery

**Decision**: Exponential backoff (1s, 4s, 16s) with max 3 attempts,
  then alternate channel fallback, then dead letter queue.
**Rationale**: 3 retries cover transient API failures. Alternate
  channel delivery (e.g., Gmail→email if WhatsApp fails) ensures
  customer gets response. Dead letter queue preserves failed messages
  for human review.
**Alternatives**: Linear retry (slower recovery), infinite retry
  (resource exhaustion risk), immediate escalation (over-escalates).

## R8: Database Connection Strategy

**Decision**: asyncpg connection pool (min=5, max=20) with health check
**Rationale**: asyncpg is the fastest async PostgreSQL driver for
  Python. Pool size 5-20 handles concurrent Kafka consumer + API
  requests without exhausting PG connections. Health check query
  validates pool on /health endpoint.
**Alternatives**: psycopg3 async (slightly slower), SQLAlchemy async
  (ORM overhead unnecessary for this project), direct connections
  (no pooling, connection exhaustion risk).
