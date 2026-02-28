# Operational Runbook: Customer Success Digital FTE

## Deploy

### Docker Compose (Development)
```bash
# Start all services
docker-compose up -d

# Verify health
curl http://localhost:8000/health | python -m json.tool

# View logs
docker-compose logs -f api worker
```

### Kubernetes (Production)
```bash
# Apply all manifests
kubectl apply -f production/k8s/namespace.yaml
kubectl apply -f production/k8s/configmap.yaml
kubectl apply -f production/k8s/secrets.yaml
kubectl apply -f production/k8s/deployment-postgres.yaml
kubectl apply -f production/k8s/deployment-kafka.yaml
kubectl apply -f production/k8s/service-api.yaml
kubectl apply -f production/k8s/deployment-api.yaml
kubectl apply -f production/k8s/deployment-worker.yaml
kubectl apply -f production/k8s/hpa.yaml

# Verify pods
kubectl get pods -n customer-success-fte
```

## Rollback

### Docker Compose
```bash
docker-compose down
git checkout <previous-tag>
docker-compose up -d --build
```

### Kubernetes
```bash
# Rollback deployment
kubectl rollout undo deployment/api -n customer-success-fte
kubectl rollout undo deployment/worker -n customer-success-fte

# Verify rollback
kubectl rollout status deployment/api -n customer-success-fte
```

## Scale

### Horizontal Scaling
```bash
# K8s: scale API replicas
kubectl scale deployment api --replicas=5 -n customer-success-fte

# K8s: scale workers
kubectl scale deployment worker --replicas=4 -n customer-success-fte

# Docker: scale worker instances
docker-compose up -d --scale worker=3
```

### HPA (auto-scaling)
```bash
# Check HPA status
kubectl get hpa -n customer-success-fte

# Update limits
kubectl patch hpa api-hpa -n customer-success-fte \
  -p '{"spec":{"maxReplicas":10}}'
```

## Monitor Logs

### Structured Log Fields
All logs are JSON with fields: `timestamp`, `level`, `service`, `ticket_id`, `channel`, `step`, `duration_ms`, `message`.

```bash
# Filter by ticket
docker-compose logs api | grep "ticket_id.*<UUID>"

# Filter escalations
docker-compose logs worker | grep '"escalated": true'

# K8s: tail API logs
kubectl logs -f deployment/api -n customer-success-fte --tail=100
```

## Handle Escalation Queue

```bash
# Check escalation topic backlog
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group escalation-handler

# View pending escalations
curl http://localhost:8000/api/reports/daily | python -m json.tool
```

## Restart Kafka

```bash
# Docker
docker-compose restart kafka
# Wait 30s, then restart consumers
docker-compose restart worker

# K8s
kubectl rollout restart statefulset/kafka -n customer-success-fte
kubectl rollout restart deployment/worker -n customer-success-fte
```

## Rebuild KB Embeddings

```bash
# Connect to database
docker-compose exec postgres psql -U fte_user -d fte_crm

# Check current KB entries
SELECT id, title, source, created_at FROM knowledge_base ORDER BY created_at DESC LIMIT 20;

# Re-seed from seed.sql (resets to default)
docker-compose exec postgres psql -U fte_user -d fte_crm -f /docker-entrypoint-initdb.d/seed.sql
```

## Generate Ad-Hoc Reports

```bash
# Get yesterday's report
curl "http://localhost:8000/api/reports/daily" | python -m json.tool

# Get specific date
curl "http://localhost:8000/api/reports/daily?date=2026-02-24" | python -m json.tool
```

## Common Issues

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| API 502 | DB pool exhausted | Increase `max_size` in connection.py, restart |
| Kafka consumer lag | Slow processing | Scale workers, check OpenAI rate limits |
| High escalation rate | Guardrails too aggressive | Review G1-G9 keywords in guardrails.py |
| Slow KB search | Missing pgvector index | `CREATE INDEX ON knowledge_base USING ivfflat (embedding vector_cosine_ops)` |
| Gmail 403 | Token expired | Refresh service account credentials |
| Twilio 401 | Wrong auth token | Check TWILIO_AUTH_TOKEN in .env/secrets |
