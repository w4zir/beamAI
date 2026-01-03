# Phase 1: Foundation & Observability - TODO Checklist

**Goal**: Make the system observable and debuggable. You can't improve what you can't measure.

**Timeline**: Weeks 1-4

---

## 1.1 Structured Logging

### Setup & Configuration
- [ ] Install structured logging library (`structlog` or `python-json-logger`)
- [ ] Add logging dependency to `requirements.txt`
- [ ] Create logging configuration module (`app/core/logging.py`)
- [ ] Configure JSON formatter with required fields

### Core Logging Fields
- [ ] Implement `timestamp` field (ISO 8601 format)
- [ ] Implement `level` field (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [ ] Implement `service` field (identify service name)
- [ ] Implement `trace_id` field (correlation ID)
- [ ] Implement `user_id` field (when available)
- [ ] Implement `request_id` field (unique per request)

### Search/Recommendation Logging
- [ ] Add logging to search endpoint with: `query`, `results_count`, `latency_ms`, `cache_hit`
- [ ] Add logging to recommendation endpoint with: `user_id`, `results_count`, `latency_ms`, `cache_hit`
- [ ] Log zero-result queries with appropriate context

### Ranking Logging
- [ ] Add logging to ranking service with: `product_id`, `final_score`, `score_breakdown`
- [ ] Log ranking weight configurations
- [ ] Log feature values used in ranking

### Trace ID Propagation
- [ ] Implement trace ID generation middleware
- [ ] Extract trace ID from HTTP headers (`X-Trace-ID` or `X-Request-ID`)
- [ ] Generate new trace ID if not present in request
- [ ] Propagate trace ID through all service calls
- [ ] Include trace ID in HTTP response headers

### Integration
- [ ] Replace all existing `print()` statements with structured logging
- [ ] Replace basic `logging` calls with structured logger
- [ ] Ensure logs output to stdout (for containerized environments)
- [ ] Test log aggregation (verify JSON format)

### Testing
- [ ] Write unit tests for logging configuration
- [ ] Verify trace ID propagation in integration tests
- [ ] Test log format matches expected JSON structure
- [ ] Verify logs are searchable by `trace_id`

---

## 1.2 Metrics Collection (Prometheus)

### Setup & Configuration
- [ ] Install `prometheus-client` Python library
- [ ] Add prometheus-client to `requirements.txt`
- [ ] Create metrics module (`app/core/metrics.py`)
- [ ] Initialize Prometheus registry

### RED Metrics - Rate
- [ ] Create counter metric for request rate per endpoint
- [ ] Track: `http_requests_total{method, endpoint, status}`
- [ ] Increment counter on each request
- [ ] Calculate requests/second from counter

### RED Metrics - Errors
- [ ] Create counter metric for error rate per endpoint
- [ ] Track: `http_errors_total{method, endpoint, status_code}`
- [ ] Track 4xx errors separately from 5xx errors
- [ ] Calculate error rate percentage

### RED Metrics - Duration
- [ ] Create histogram metric for request latency
- [ ] Track: `http_request_duration_seconds{method, endpoint}`
- [ ] Calculate percentiles: p50, p95, p99, p999
- [ ] Track latency for each endpoint separately

### Business Metrics
- [ ] Create counter for zero-result searches: `search_zero_results_total{query}`
- [ ] Create counter for cache hits: `cache_hits_total{cache_type}`
- [ ] Create counter for cache misses: `cache_misses_total{cache_type}`
- [ ] Create histogram for ranking scores: `ranking_score_distribution{product_id}`
- [ ] Calculate zero-result rate percentage
- [ ] Calculate cache hit rate percentage

### Resource Metrics
- [ ] Create gauge for CPU usage: `system_cpu_usage_percent`
- [ ] Create gauge for memory usage: `system_memory_usage_bytes`
- [ ] Create gauge for database connection pool: `db_connection_pool_size{state}`
- [ ] Track active vs idle connections

### Metrics Endpoint
- [ ] Create `/metrics` endpoint in FastAPI
- [ ] Expose Prometheus format metrics
- [ ] Ensure endpoint is accessible (no auth required for Prometheus scraping)
- [ ] Test metrics endpoint returns valid Prometheus format

### Grafana Dashboards
- [ ] Set up Grafana instance (or configure access)
- [ ] Create dashboard: Service Health Overview
  - [ ] Request rate per endpoint
  - [ ] Error rate per endpoint
  - [ ] Latency percentiles (p50, p95, p99)
  - [ ] CPU and memory usage
- [ ] Create dashboard: Search Performance
  - [ ] Search request rate
  - [ ] Search latency (p50, p95, p99)
  - [ ] Search error rate
  - [ ] Zero-result rate
  - [ ] Cache hit rate for searches
- [ ] Create dashboard: Recommendation Performance
  - [ ] Recommendation request rate
  - [ ] Recommendation latency (p50, p95, p99)
  - [ ] Recommendation error rate
  - [ ] Cache hit rate for recommendations
- [ ] Create dashboard: Database Health
  - [ ] Connection pool usage
  - [ ] Query latency
  - [ ] Connection pool exhaustion alerts
- [ ] Create dashboard: Cache Performance
  - [ ] Cache hit rate by type
  - [ ] Cache miss rate by type
  - [ ] Cache operation latency

### Testing
- [ ] Write unit tests for metrics collection
- [ ] Verify metrics are correctly incremented
- [ ] Test metrics endpoint returns expected format
- [ ] Verify Grafana dashboards display data correctly

---

## 1.3 Distributed Tracing (OpenTelemetry)

### Setup & Configuration
- [ ] Install OpenTelemetry Python SDK packages
  - [ ] `opentelemetry-api`
  - [ ] `opentelemetry-sdk`
  - [ ] `opentelemetry-instrumentation-fastapi`
  - [ ] `opentelemetry-instrumentation-httpx`
  - [ ] `opentelemetry-instrumentation-asyncpg` (or psycopg2)
  - [ ] `opentelemetry-exporter-jaeger` (or otlp exporter)
- [ ] Add OpenTelemetry dependencies to `requirements.txt`
- [ ] Create tracing configuration module (`app/core/tracing.py`)

### Trace ID Generation
- [ ] Configure trace ID generation at API gateway/FastAPI entry point
- [ ] Ensure trace ID is generated for every request
- [ ] Extract trace ID from incoming headers if present
- [ ] Generate new trace ID if not present

### Trace Propagation
- [ ] Configure trace context propagation via HTTP headers
- [ ] Propagate trace ID through database calls
- [ ] Propagate trace ID through cache calls
- [ ] Propagate trace ID through ranking service calls
- [ ] Ensure trace ID flows through all service boundaries

### Span Creation
- [ ] Create span for search retrieval operation
- [ ] Create span for ranking operation
- [ ] Create span for feature fetching operation
- [ ] Create span for database queries
- [ ] Create span for cache operations
- [ ] Add span attributes: endpoint, method, user_id, query, etc.

### FastAPI Instrumentation
- [ ] Instrument FastAPI application with OpenTelemetry
- [ ] Configure automatic span creation for HTTP requests
- [ ] Add custom spans for business logic operations
- [ ] Ensure spans capture request/response metadata

### Trace Export
- [ ] Configure trace export to Jaeger backend (or Tempo)
- [ ] Set up Jaeger/Tempo instance (or configure access)
- [ ] Configure trace exporter endpoint
- [ ] Test trace export works correctly
- [ ] Verify traces appear in Jaeger/Tempo UI

### Trace ID in Logs
- [ ] Ensure trace ID is included in all log entries
- [ ] Link logs to traces via trace ID
- [ ] Test log-trace correlation

### Trace ID in Error Responses
- [ ] Include trace ID in error response headers
- [ ] Include trace ID in error response body
- [ ] Ensure trace ID helps with debugging

### Testing
- [ ] Write unit tests for tracing setup
- [ ] Verify trace IDs are generated correctly
- [ ] Test trace propagation through services
- [ ] Verify spans are created for key operations
- [ ] Test trace export to backend
- [ ] Verify traces are visible in Jaeger/Tempo UI

---

## 1.4 Alerting Rules

### Setup & Configuration
- [ ] Set up Prometheus Alertmanager (or configure Grafana alerts)
- [ ] Create alerting configuration file
- [ ] Configure alert notification channels (Slack, PagerDuty, email)

### Alert: High Latency (p99 > 500ms)
- [ ] Create Prometheus alert rule: `p99_latency_high`
- [ ] Configure threshold: p99 latency > 500ms for 5 minutes
- [ ] Set severity: Page on-call
- [ ] Add alert labels: endpoint, method
- [ ] Test alert fires correctly
- [ ] Document alert in runbook

### Alert: High Error Rate (> 1%)
- [ ] Create Prometheus alert rule: `error_rate_high`
- [ ] Configure threshold: Error rate > 1% for 2 minutes
- [ ] Set severity: Slack alert
- [ ] Add alert labels: endpoint, status_code
- [ ] Test alert fires correctly
- [ ] Document alert in runbook

### Alert: High Zero-Result Rate (> 10%)
- [ ] Create Prometheus alert rule: `zero_result_rate_high`
- [ ] Configure threshold: Zero-result rate > 10% for 10 minutes
- [ ] Set severity: Investigate (non-critical)
- [ ] Add alert labels: query_pattern
- [ ] Test alert fires correctly
- [ ] Document alert in runbook

### Alert: Database Connection Pool Exhaustion
- [ ] Create Prometheus alert rule: `db_pool_exhausted`
- [ ] Configure threshold: Available connections < 2
- [ ] Set severity: Alert
- [ ] Add alert labels: pool_name
- [ ] Test alert fires correctly
- [ ] Document alert in runbook

### Alert: Low Cache Hit Rate (< 50%)
- [ ] Create Prometheus alert rule: `cache_hit_rate_low`
- [ ] Configure threshold: Cache hit rate < 50% for 10 minutes
- [ ] Set severity: Investigate (non-critical)
- [ ] Add alert labels: cache_type
- [ ] Test alert fires correctly
- [ ] Document alert in runbook

### On-Call Runbooks
- [ ] Create runbook for `p99_latency_high` alert
  - [ ] Symptoms description
  - [ ] Investigation steps
  - [ ] Common causes
  - [ ] Resolution steps
- [ ] Create runbook for `error_rate_high` alert
  - [ ] Symptoms description
  - [ ] Investigation steps
  - [ ] Common causes
  - [ ] Resolution steps
- [ ] Create runbook for `zero_result_rate_high` alert
  - [ ] Symptoms description
  - [ ] Investigation steps
  - [ ] Common causes
  - [ ] Resolution steps
- [ ] Create runbook for `db_pool_exhausted` alert
  - [ ] Symptoms description
  - [ ] Investigation steps
  - [ ] Common causes
  - [ ] Resolution steps
- [ ] Create runbook for `cache_hit_rate_low` alert
  - [ ] Symptoms description
  - [ ] Investigation steps
  - [ ] Common causes
  - [ ] Resolution steps

### Alert Testing
- [ ] Test all alerts fire correctly for test scenarios
- [ ] Verify alert notifications are received
- [ ] Test alert recovery (alerts clear when conditions improve)
- [ ] Verify alert labels are correct
- [ ] Test alert routing to correct channels

---

## Success Criteria Verification

### All requests have trace IDs
- [ ] Verify 100% of requests have trace IDs
- [ ] Test trace ID propagation through all services
- [ ] Verify trace IDs are unique per request

### p95 latency visible in Grafana
- [ ] Verify p95 latency metric is collected
- [ ] Verify p95 latency is displayed in Grafana dashboard
- [ ] Test latency tracking for all endpoints

### Alerts fire correctly for test scenarios
- [ ] Simulate high latency scenario → verify alert fires
- [ ] Simulate high error rate → verify alert fires
- [ ] Simulate zero-result rate spike → verify alert fires
- [ ] Simulate database pool exhaustion → verify alert fires
- [ ] Simulate low cache hit rate → verify alert fires

### Logs searchable by trace_id
- [ ] Test searching logs by trace_id
- [ ] Verify trace_id appears in all log entries
- [ ] Test log aggregation tools can filter by trace_id

---

## Documentation

- [ ] Document logging configuration and usage
- [ ] Document metrics collection and available metrics
- [ ] Document tracing setup and usage
- [ ] Document alerting rules and runbooks
- [ ] Update architecture documentation with observability components
- [ ] Create developer guide for adding new metrics/logs/traces

---

## Integration & Testing

- [ ] Integration test: End-to-end request with full observability
  - [ ] Verify trace ID generated
  - [ ] Verify logs created with trace ID
  - [ ] Verify metrics incremented
  - [ ] Verify trace visible in Jaeger/Tempo
- [ ] Load test: Verify observability doesn't impact performance
- [ ] Test observability stack resilience (what happens if Prometheus/Jaeger is down?)

---

## Notes

- Prioritize structured logging first (foundation for everything else)
- Metrics and tracing can be implemented in parallel
- Alerting depends on metrics being in place
- Test each component independently before integration
- Document any deviations from the plan

---

## References

- Phase 1 specification: `/docs/implementation_phases.md`
- Observability spec: `/specs/OBSERVABILITY.md`
- Architecture: `/specs/ARCHITECTURE.md`

