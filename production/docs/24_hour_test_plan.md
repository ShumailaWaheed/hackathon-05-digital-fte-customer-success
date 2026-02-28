# 24-Hour Chaos Test Plan

## Overview

Continuous load test with pod disruptions to validate system resilience under production-like conditions.

## Test Setup

### Infrastructure
- Docker Compose or Kubernetes cluster
- PostgreSQL 16 + pgvector
- Kafka (KRaft mode, single broker)
- 2 API replicas, 2 Worker replicas

### Volume Targets
| Channel | Messages | Rate |
|---------|----------|------|
| Web Form | 100+ | ~4/hour |
| Gmail | 50+ | ~2/hour |
| WhatsApp | 50+ | ~2/hour |
| **Total** | **200+** | **~8/hour** |

### Message Mix
- 60% Normal support requests
- 25% Escalation triggers (pricing, legal, angry)
- 15% Edge cases (empty, long, multi-guardrail, unicode)

## Disruption Schedule

| Time | Action | Target |
|------|--------|--------|
| T+2h | Kill 1 API pod | `api` deployment |
| T+4h | Kill 1 Worker pod | `worker` deployment |
| T+6h | Kill 1 API pod | `api` deployment |
| T+8h | Restart Kafka | `kafka` statefulset |
| T+10h | Kill 1 Worker pod | `worker` deployment |
| T+12h | Kill 1 API + 1 Worker | Both deployments |
| T+14h | Kill 1 API pod | `api` deployment |
| T+16h | Kill 1 Worker pod | `worker` deployment |
| T+18h | Restart PostgreSQL | `postgres` statefulset |
| T+20h | Kill 1 API pod | `api` deployment |
| T+22h | Kill 1 Worker pod | `worker` deployment |
| T+24h | End test | Collect metrics |

## Success Gates

| Metric | Target | Method |
|--------|--------|--------|
| Escalation Rate | < 20% | agent_metrics table |
| KB Accuracy | > 85% | Sample validation |
| Cross-Channel ID Accuracy | > 95% | customer_identifiers audit |
| P95 Response Latency | < 3s | Kafka message timestamps |
| Uptime | 99.9% | Health endpoint polling |
| Guardrail Violations | 0 | Check for pricing/legal responses |
| Data Loss | 0 messages | Compare sent vs. processed counts |

## Execution

### Run with Compressed Time (4h at 6x speed)
```bash
cd production
python -m tests.chaos.chaos_runner --messages 200 --concurrency 20
```

### Run with Pod Disruptions (24h)
```bash
# Terminal 1: Message generator
python -m tests.chaos.chaos_runner --messages 200 --duration 24h

# Terminal 2: Pod killer
python -c "
from production.tests.chaos.pod_killer import PodKiller
killer = PodKiller()
killer.schedule_disruptions(interval_hours=2, duration_hours=24)
"
```

## Metrics Collection

```sql
-- Total messages processed
SELECT COUNT(*) FROM agent_metrics WHERE created_at > NOW() - INTERVAL '24 hours';

-- Escalation rate
SELECT
  COUNT(*) FILTER (WHERE escalated) as escalated,
  COUNT(*) as total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE escalated) / COUNT(*), 1) as rate
FROM agent_metrics WHERE created_at > NOW() - INTERVAL '24 hours';

-- Average response time
SELECT AVG(response_time_ms), PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)
FROM agent_metrics WHERE created_at > NOW() - INTERVAL '24 hours';

-- Channel breakdown
SELECT channel, COUNT(*), AVG(sentiment_score)
FROM agent_metrics WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY channel;
```

## Post-Test Report

Generate report:
```bash
curl http://localhost:8000/api/reports/daily | python -m json.tool
```
