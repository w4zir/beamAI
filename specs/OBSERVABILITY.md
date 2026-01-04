## Three Pillars

### 1. Metrics (Prometheus + Grafana) ✅ IMPLEMENTED
- Request rate, latency, errors (RED metrics)
- Resource utilization (CPU, memory, disk)
- Business metrics (zero-result searches, cache hits/misses, ranking scores)
- Semantic search metrics (Phase 3.1)
- **Status**: ✅ Implemented (Phase 1.2)

**Implementation:**
- Metrics module: `app/core/metrics.py`
- Metrics endpoint: `/metrics` (Prometheus format)
- Grafana dashboards: 5 dashboards automatically provisioned
- RED metrics: Rate, Errors, Duration for all endpoints
- Business metrics: Zero-result searches, cache hits/misses, ranking score distribution
- Resource metrics: CPU usage, memory usage, database connection pool
- Semantic search metrics: Request count, latency, embedding generation latency, FAISS search latency

**Available Metrics:**
- `http_requests_total{method, endpoint, status}`: Total HTTP requests
- `http_errors_total{method, endpoint, status_code}`: Total HTTP errors (4xx, 5xx)
- `http_request_duration_seconds{method, endpoint}`: Request latency histogram
- `search_zero_results_total{query_pattern}`: Zero-result searches
- `cache_hits_total{cache_type}`: Cache hits
- `cache_misses_total{cache_type}`: Cache misses
- `ranking_score_distribution{product_id}`: Ranking score distribution
- `system_cpu_usage_percent`: CPU usage percentage
- `system_memory_usage_bytes`: Memory usage in bytes
- `db_connection_pool_size{state}`: Database connection pool metrics
- `semantic_search_requests_total`: Semantic search request count
- `semantic_search_latency_seconds`: Semantic search latency histogram
- `semantic_embedding_generation_latency_seconds`: Embedding generation latency
- `semantic_faiss_search_latency_seconds`: FAISS search latency
- `semantic_index_memory_bytes`: FAISS index memory usage
- `semantic_index_total_products`: Total products in FAISS index
- `semantic_index_available`: FAISS index availability (0 or 1)

**Grafana Dashboards:**
- Service Health Overview: Request rate, error rate, latency percentiles, CPU/memory
- Search Performance: Search-specific metrics (rate, latency, zero-results, cache hits)
- Recommendation Performance: Recommendation-specific metrics
- Database Health: Connection pool usage and database metrics
- Cache Performance: Cache hit/miss rates by type

**Configuration:**
- Prometheus scrapes metrics every 15 seconds from `/metrics` endpoint
- Metrics are exposed without authentication (standard Prometheus practice)
- Resource metrics updated on-demand when metrics are scraped

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