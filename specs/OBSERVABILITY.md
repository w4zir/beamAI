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

**Implementation Plan:**

**Tools**: OpenTelemetry Python SDK, Jaeger or Tempo backend

**Instrumentation**:
- FastAPI middleware for automatic span creation
- Database client instrumentation (asyncpg/psycopg2)
- Redis client instrumentation
- HTTP client instrumentation (for external APIs)

**Span Creation**:
- **API Gateway**: Root span for each request
- **Search Service**: Spans for keyword search, semantic search, hybrid merge
- **Ranking Service**: Spans for feature fetching, scoring, sorting
- **Feature Service**: Spans for batch feature fetching
- **Cache Service**: Spans for cache operations (get, set, miss)

**Trace Export**:
- Export to Jaeger (development) or Tempo (production)
- Batch export (every 5 seconds or 100 spans)
- Sampling: 100% for errors, 10% for successful requests (adjustable)

**Trace Context Propagation**:
- Extract trace context from HTTP headers (`traceparent`, `X-Trace-ID`)
- Propagate to all downstream services
- Include trace_id in all logs and error responses

**Trace Visualization**:
- Service map showing request flow
- Latency breakdown per service
- Error traces highlighted
- Bottleneck identification (slowest spans)

**Metrics from Traces**:
```
trace_duration_seconds{service="search", operation="keyword_search"}
trace_duration_seconds{service="ranking", operation="scoring"}
trace_errors_total{service="search", operation="semantic_search"}
```

**Configuration**:
- Environment variables: `OTEL_EXPORTER_JAEGER_ENDPOINT`, `OTEL_SERVICE_NAME`
- Sampling rate: `OTEL_TRACES_SAMPLER_ARG` (default: 0.1 for 10% sampling)

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

**Alignment**: Implements Phase 1.4 from `docs/TODO/implementation_phases.md`

**Tool**: Prometheus Alertmanager

### Alert Definitions

#### Critical Alerts (Page On-Call)

**1. High Latency**
- **Condition**: `http_request_duration_seconds{p99} > 0.5` for 5 minutes
- **Severity**: Critical
- **Action**: Page on-call engineer
- **Runbook**: Check database performance, cache hit rate, service health
- **Resolution**: Scale services, check for slow queries, verify cache is working

**2. High Error Rate**
- **Condition**: `rate(http_errors_total[2m]) / rate(http_requests_total[2m]) > 0.01` for 2 minutes
- **Severity**: Critical
- **Action**: Page on-call engineer
- **Runbook**: Check error logs, database connectivity, external service health
- **Resolution**: Check application logs, verify database/replica health, check circuit breakers

**3. Database Connection Pool Exhaustion**
- **Condition**: `db_connection_pool_size{state="waiting"} > 5` for 2 minutes
- **Severity**: Critical
- **Action**: Page on-call engineer
- **Runbook**: Check for connection leaks, slow queries, pool size configuration
- **Resolution**: Increase pool size, fix connection leaks, optimize slow queries

**4. Replication Lag Critical**
- **Condition**: `db_replication_lag_seconds > 120` for 5 minutes
- **Severity**: Critical
- **Action**: Page on-call engineer
- **Runbook**: Check replica health, network connectivity, primary database load
- **Resolution**: Check replica status, verify network, consider promoting new replica

**5. Cache Circuit Breaker Open**
- **Condition**: `cache_circuit_breaker_state{state="open"} == 1` for 5 minutes
- **Severity**: Critical
- **Action**: Page on-call engineer
- **Runbook**: Check Redis health, network connectivity, Redis memory usage
- **Resolution**: Check Redis service, verify network, restart Redis if needed

**6. FAISS Index Unavailable**
- **Condition**: `semantic_index_available == 0` for 1 minute
- **Severity**: Critical
- **Action**: Page on-call engineer
- **Runbook**: Check index file, disk space, memory availability
- **Resolution**: Rebuild index, check disk space, verify file permissions

#### Warning Alerts (Slack Notification)

**1. Elevated Latency**
- **Condition**: `http_request_duration_seconds{p95} > 0.3` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Monitor trends, check cache hit rate, review recent deployments
- **Resolution**: Investigate performance degradation, check for resource constraints

**2. Elevated Error Rate**
- **Condition**: `rate(http_errors_total[5m]) / rate(http_requests_total[5m]) > 0.005` for 5 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Review error logs, check for intermittent failures
- **Resolution**: Investigate error patterns, check external dependencies

**3. High Zero-Result Rate**
- **Condition**: `rate(search_zero_results_total[10m]) / rate(search_requests_total[10m]) > 0.1` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Check query patterns, verify search index, review query enhancement
- **Resolution**: Investigate query patterns, check search index health, review query logs

**4. Low Cache Hit Rate**
- **Condition**: `cache_hit_rate < 0.6` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Check cache warming, verify TTL settings, review cache invalidation
- **Resolution**: Review cache strategy, check for excessive invalidation, verify warming scripts

**5. Replication Lag Warning**
- **Condition**: `db_replication_lag_seconds > 60` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Monitor replication lag trends, check primary database load
- **Resolution**: Monitor trends, consider read routing adjustments

**6. High Memory Usage**
- **Condition**: `system_memory_usage_bytes / system_memory_total_bytes > 0.85` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Check for memory leaks, review service memory limits
- **Resolution**: Investigate memory usage, consider scaling services

**7. High CPU Usage**
- **Condition**: `system_cpu_usage_percent > 80` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert to #alerts channel
- **Runbook**: Check for CPU-intensive operations, review service load
- **Resolution**: Investigate CPU usage, consider scaling services

### Alertmanager Configuration

**Alert Routing**:
- **Critical Alerts**: Route to PagerDuty/OpsGenie (page on-call)
- **Warning Alerts**: Route to Slack #alerts channel
- **Info Alerts**: Route to Slack #monitoring channel

**Alert Grouping**:
- Group alerts by service and severity
- Suppress duplicate alerts for 5 minutes
- Escalate if alert persists >15 minutes

**Notification Templates**:
- Include alert name, severity, condition, runbook link
- Include relevant metrics and logs
- Include trace_id for error alerts

### On-Call Runbooks

Each alert includes a runbook with:
1. **Alert Description**: What the alert means
2. **Immediate Actions**: Steps to investigate
3. **Common Causes**: Typical root causes
4. **Resolution Steps**: How to fix the issue
5. **Escalation**: When to escalate to senior engineer

### Alert Testing

**Test Scenarios**:
- Simulate high latency (add artificial delay)
- Simulate errors (inject failures)
- Simulate cache failures (disable Redis)
- Simulate database failures (stop replica)

**Frequency**: Test alerts monthly to ensure they fire correctly

---

## LLMOps Metrics

**Alignment**: Aligns with `specs/AI_ARCHITECTURE.md` LLM observability requirements

### Core LLM Metrics

#### 1. Request Metrics
```
llm_requests_total{agent="intent", model="gpt-3.5-turbo", tier="1"}
llm_requests_total{agent="rewrite", model="gpt-3.5-turbo", tier="1"}
llm_requests_total{agent="explanation", model="gpt-4", tier="2"}
llm_errors_total{agent="intent", reason="timeout"}
llm_errors_total{agent="rewrite", reason="api_error"}
llm_errors_total{agent="clarification", reason="rate_limit"}
```

#### 2. Latency Metrics
```
llm_latency_ms_bucket{agent="intent", tier="1"}  # Histogram
llm_latency_ms_p50{agent="intent", tier="1"}
llm_latency_ms_p95{agent="intent", tier="1"}  # Target: <80ms for Tier 1
llm_latency_ms_p95{agent="rewrite", tier="1"}  # Target: <80ms for Tier 1
llm_latency_ms_p95{agent="explanation", tier="2"}  # Best-effort, async
```

#### 3. Cost & Token Metrics
```
llm_tokens_input_total{agent="intent", model="gpt-3.5-turbo"}
llm_tokens_output_total{agent="intent", model="gpt-3.5-turbo"}
llm_cost_usd_total{agent="intent", model="gpt-3.5-turbo"}
llm_cost_usd_total{agent="rewrite", model="gpt-3.5-turbo"}
llm_cost_usd_total{agent="explanation", model="gpt-4"}
```

**Cost Calculation**:
- Track input/output tokens per model
- Calculate cost based on model pricing
- Aggregate daily/weekly/monthly costs

#### 4. Cache Effectiveness
```
llm_cache_hit_total{agent="intent"}
llm_cache_miss_total{agent="intent"}
llm_cache_hit_rate{agent="intent"}  # Calculated: hits / (hits + misses)
llm_cache_hit_rate{agent="rewrite"}  # Target: >80%
```

#### 5. Quality & Confidence
```
llm_low_confidence_total{agent="intent"}  # Confidence < threshold
llm_clarification_triggered_total{}  # Clarification requests
llm_schema_validation_failures_total{agent="rewrite"}  # Schema validation failures
llm_grounding_violations_total{agent="explanation"}  # Hallucination detection
```

### LLM Alerts

**1. LLM Latency Spike (Tier 1)**
- **Condition**: `llm_latency_ms_p95{agent="intent", tier="1"} > 150` for 5 minutes
- **Severity**: Warning
- **Action**: Slack alert
- **Runbook**: Check LLM API status, verify cache hit rate, check network latency

**2. LLM Error Rate**
- **Condition**: `rate(llm_errors_total[2m]) / rate(llm_requests_total[2m]) > 0.01` for 2 minutes
- **Severity**: Critical
- **Action**: Page on-call
- **Runbook**: Check LLM API status, verify API keys, check rate limits
- **Resolution**: Circuit breaker should auto-disable LLM, verify fallback works

**3. Low Cache Hit Rate**
- **Condition**: `llm_cache_hit_rate{agent="intent"} < 0.6` for 10 minutes
- **Severity**: Warning
- **Action**: Slack alert
- **Runbook**: Check cache warming, verify TTL settings, review query patterns

**4. High Token Cost**
- **Condition**: `rate(llm_cost_usd_total[1h]) > 2 * baseline_cost` for 1 hour
- **Severity**: Warning
- **Action**: Slack alert
- **Runbook**: Check for cache misses, verify token usage, review prompt sizes

**5. Schema Validation Failures**
- **Condition**: `rate(llm_schema_validation_failures_total[5m]) / rate(llm_requests_total[5m]) > 0.05` for 5 minutes
- **Severity**: Warning
- **Action**: Slack alert
- **Runbook**: Check LLM output format, verify schema definitions, review prompts

### LLM Grafana Dashboard

**LLM Performance Dashboard**:
- Request rate by agent and model
- Latency percentiles (p50, p95, p99) by tier
- Error rate by agent and reason
- Cache hit rate by agent
- Token usage and cost trends
- Quality metrics (confidence, validation failures)

**Panels**:
1. **Request Overview**: Total requests, error rate, cache hit rate
2. **Latency Breakdown**: p95 latency by agent and tier
3. **Cost Analysis**: Daily/weekly cost by agent and model
4. **Quality Metrics**: Confidence distribution, validation failures
5. **Cache Performance**: Hit rate, miss rate, cache size

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 1.2, 1.3, 1.4)
- **AI Architecture**: `specs/AI_ARCHITECTURE.md` (LLMOps Metrics)
- **Caching Strategy**: `specs/CACHING_STRATEGY.md` (Cache Metrics)
- **Database Optimization**: `specs/DATABASE_OPTIMIZATION.md` (Database Metrics)