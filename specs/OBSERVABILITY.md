## Three Pillars

### 1. Metrics (Prometheus + Grafana)
- Request rate, latency, errors (RED metrics)
- Resource utilization (CPU, memory, disk)
- Business metrics (CVR, CTR)

### 2. Logs (Structured JSON)
```json
{
  "timestamp": "2026-01-02T10:30:45Z",
  "level": "INFO",
  "service": "search_service",
  "trace_id": "abc123",
  "user_id": "user_456",
  "query": "running shoes",
  "results_count": 42,
  "latency_ms": 87
}
```

### 3. Traces (OpenTelemetry)
- Request flows across services
- Identify bottlenecks
- Trace ID propagated via HTTP headers

## Service-Specific Instrumentation

### FastAPI Gateway
- Request count by endpoint
- p50/p95/p99 latency per endpoint
- 4xx/5xx error rate

### Search Service
- Query latency by type (keyword vs semantic)
- FAISS index size and memory usage
- Cache hit rate

### Ranking Service
- Feature retrieval time
- Scoring latency
- Score distribution (detect drift)

## Alerting Rules
- p99 latency > 500ms for 5 minutes → Page on-call
- Error rate > 1% for 2 minutes → Slack alert
- Zero-result rate > 10% for 10 minutes → Investigate