## Three Pillars

### 1. Metrics (Prometheus + Grafana)
- Request rate, latency, errors (RED metrics)
- Resource utilization (CPU, memory, disk)
- Business metrics (CVR, CTR)
- **Status**: Not yet implemented (Phase 1.2)

### 2. Logs (Structured JSON) ✅ IMPLEMENTED
The system uses `structlog` for structured JSON logging with trace ID propagation.

**Implementation:**
- Logging module: `app/core/logging.py`
- Middleware: `app/core/middleware.py` (TraceIDMiddleware)
- All logs output to stdout (containerized environments)
- Supports JSON (production) and console (development) formats

**Core Fields (automatically included in all logs):**
- `timestamp`: ISO 8601 format (UTC)
- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `service`: Service name (`beamai_search_api`)
- `trace_id`: Correlation ID (UUID v4)
- `request_id`: Unique per request (UUID v4)
- `user_id`: User identifier (when available)

**Example Log Entry:**
```json
{
  "timestamp": "2026-01-02T10:30:45.123456Z",
  "level": "INFO",
  "service": "beamai_search_api",
  "trace_id": "abc123-def456-ghi789",
  "request_id": "req-123-456",
  "user_id": "user_789",
  "event": "search_completed",
  "query": "running shoes",
  "results_count": 42,
  "latency_ms": 87,
  "cache_hit": false
}
```

**Log Events:**
- `request_started`, `request_completed`, `request_failed`
- `search_started`, `search_completed`, `search_zero_results`, `search_error`
- `recommendation_started`, `recommendation_completed`, `recommendation_zero_results`, `recommendation_error`
- `ranking_started`, `ranking_completed`, `ranking_product_scored` (DEBUG)

**Trace ID Propagation:**
- Extracted from `X-Trace-ID` or `X-Request-ID` headers (if present)
- Generated as UUID v4 if not present
- Stored in context variables and automatically included in all log entries
- Returned in response headers (`X-Trace-ID`, `X-Request-ID`)

**Configuration:**
- Environment variables: `LOG_LEVEL` (default: INFO), `LOG_JSON` (default: true)
- Configured at application startup in `app/main.py`

### 3. Traces (OpenTelemetry)
- Request flows across services
- Identify bottlenecks
- Trace ID propagated via HTTP headers
- **Status**: Not yet implemented (Phase 1.3)

## Service-Specific Instrumentation

### FastAPI Gateway
- Request count by endpoint
- p50/p95/p99 latency per endpoint
- 4xx/5xx error rate
- **Logging**: ✅ `request_started`, `request_completed`, `request_failed` events with trace IDs

### Search Service
- Query latency by type (keyword vs semantic)
- FAISS index size and memory usage
- Cache hit rate
- **Logging**: ✅ `search_started`, `search_completed`, `search_zero_results`, `search_error` events with query context

### Ranking Service
- Feature retrieval time
- Scoring latency
- Score distribution (detect drift)
- **Logging**: ✅ `ranking_started`, `ranking_completed`, `ranking_product_scored` (DEBUG) events with score breakdowns

## Alerting Rules
- p99 latency > 500ms for 5 minutes → Page on-call
- Error rate > 1% for 2 minutes → Slack alert
- Zero-result rate > 10% for 10 minutes → Investigate