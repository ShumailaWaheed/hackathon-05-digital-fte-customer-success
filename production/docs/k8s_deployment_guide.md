# Kubernetes Deployment Guide

## Prerequisites

- Kubernetes cluster (1.28+)
- kubectl configured with cluster access
- Docker registry access (for pushing images)
- Secrets: OpenAI API key, Twilio credentials, Gmail service account

## Step 1: Build and Push Images

```bash
# Build API/Worker image
docker build -t your-registry/fte-api:latest -f production/Dockerfile .
docker push your-registry/fte-api:latest

# Build Frontend image
docker build -t your-registry/fte-frontend:latest -f frontend/Dockerfile .
docker push your-registry/fte-frontend:latest
```

## Step 2: Create Namespace

```bash
kubectl apply -f production/k8s/namespace.yaml
kubectl config set-context --current --namespace=customer-success-fte
```

## Step 3: Configure Secrets

```bash
# Edit secrets.yaml with base64-encoded values
# echo -n "sk-your-key" | base64
kubectl apply -f production/k8s/secrets.yaml

# Verify
kubectl get secrets -n customer-success-fte
```

## Step 4: Apply ConfigMap

```bash
kubectl apply -f production/k8s/configmap.yaml
```

## Step 5: Deploy Data Stores

```bash
# PostgreSQL (with pgvector)
kubectl apply -f production/k8s/deployment-postgres.yaml

# Wait for postgres to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n customer-success-fte --timeout=120s

# Kafka (KRaft mode)
kubectl apply -f production/k8s/deployment-kafka.yaml

# Wait for kafka
kubectl wait --for=condition=ready pod -l app=kafka -n customer-success-fte --timeout=120s
```

## Step 6: Deploy Application

```bash
# Services first
kubectl apply -f production/k8s/service-api.yaml

# API deployment
kubectl apply -f production/k8s/deployment-api.yaml

# Worker deployment
kubectl apply -f production/k8s/deployment-worker.yaml

# HPA
kubectl apply -f production/k8s/hpa.yaml
```

## Step 7: Verify Pods

```bash
# Check all pods
kubectl get pods -n customer-success-fte

# Expected output:
# NAME                      READY   STATUS    RESTARTS   AGE
# api-xxxxx-yyyyy           1/1     Running   0          1m
# api-xxxxx-zzzzz           1/1     Running   0          1m
# worker-xxxxx-yyyyy        1/1     Running   0          1m
# worker-xxxxx-zzzzz        1/1     Running   0          1m
# postgres-0                1/1     Running   0          3m
# kafka-0                   1/1     Running   0          2m

# Check HPA
kubectl get hpa -n customer-success-fte
```

## Step 8: Configure Webhooks

```bash
# Get external API URL
kubectl get svc api-external -n customer-success-fte

# Configure in external services:
# - Twilio WhatsApp webhook: https://<EXTERNAL-IP>:8000/webhooks/whatsapp
# - Gmail Pub/Sub push: https://<EXTERNAL-IP>:8000/webhooks/gmail
# - Frontend embed: https://<EXTERNAL-IP>:3000
```

## Step 9: Smoke Tests

```bash
# Health check
EXTERNAL_IP=$(kubectl get svc api-external -n customer-success-fte -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

curl http://$EXTERNAL_IP:8000/health | python -m json.tool

# Submit test form
curl -X POST http://$EXTERNAL_IP:8000/api/support \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","category":"general-question","message":"Hello test"}'

# Check logs
kubectl logs -f deployment/api -n customer-success-fte --tail=50
```

## Monitoring

```bash
# Pod resource usage
kubectl top pods -n customer-success-fte

# API logs (structured JSON)
kubectl logs deployment/api -n customer-success-fte | jq '.level'

# Worker logs
kubectl logs deployment/worker -n customer-success-fte --tail=100

# Escalation events
kubectl logs deployment/worker -n customer-success-fte | grep "ESCALATION"
```

## Troubleshooting

| Issue | Command | Fix |
|-------|---------|-----|
| Pod CrashLoop | `kubectl describe pod <name>` | Check env vars, secrets |
| DB connection refused | `kubectl logs postgres-0` | Wait for init, check DATABASE_URL |
| Kafka timeout | `kubectl logs kafka-0` | Check KAFKA_BOOTSTRAP_SERVERS in configmap |
| HPA not scaling | `kubectl describe hpa` | Verify metrics-server installed |
| Webhook 404 | `kubectl get svc` | Check service ports and external IP |
