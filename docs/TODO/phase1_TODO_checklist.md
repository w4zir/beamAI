# Phase 1: Foundation & Observability - TODO Checklist

**Goal**: Make the system observable and debuggable. You can't improve what you can't measure.

**Timeline**: Weeks 1-4

**Status**: 
- ✅ **1.1 Structured Logging**: COMPLETE
- ✅ **1.2 Metrics Collection (Prometheus)**: COMPLETE
- ⏳ **1.3 Distributed Tracing (OpenTelemetry)**: NOT IMPLEMENTED
- ⏳ **1.4 Alerting Rules**: NOT IMPLEMENTED

---

## 1.1 Structured Logging

### Setup & Configuration
- [x] Install structured logging library (`structlog` or `python-json-logger`)
- [x] Add logging dependency to `requirements.txt`
- [x] Create logging configuration module (`app/core/logging.py`)
- [x] Configure JSON formatter with required fields

### Core Logging Fields
- [x] Implement `timestamp` field (ISO 8601 format)
- [x] Implement `level` field (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [x] Implement `service` field (identify service name)
- [x] Implement `trace_id` field (correlation ID)
- [x] Implement `user_id` field (when available)
- [x] Implement `request_id` field (unique per request)

### Search/Recommendation Logging
- [x] Add logging to search endpoint with: `query`, `results_count`, `latency_ms`, `cache_hit`
- [x] Add logging to recommendation endpoint with: `user_id`, `results_count`, `latency_ms`, `cache_hit`
- [x] Log zero-result queries with appropriate context

### Ranking Logging
- [x] Add logging to ranking service with: `product_id`, `final_score`, `score_breakdown`
- [x] Log ranking weight configurations
- [x] Log feature values used in ranking

### Trace ID Propagation
- [x] Implement trace ID generation middleware
- [x] Extract trace ID from HTTP headers (`X-Trace-ID` or `X-Request-ID`)
- [x] Generate new trace ID if not present in request
- [x] Propagate trace ID through all service calls
- [x] Include trace ID in HTTP response headers

### Integration
- [x] Replace all existing `print()` statements with structured logging
- [x] Replace basic `logging` calls with structured logger
- [x] Ensure logs output to stdout (for containerized environments)
- [x] Test log aggregation (verify JSON format)

### Testing
- [x] Write unit tests for logging configuration
- [x] Verify trace ID propagation in integration tests
- [x] Test log format matches expected JSON structure
- [x] Verify logs are searchable by `trace_id`

---

## 1.2 Metrics Collection (Prometheus)

### Setup & Configuration
- [x] Install `prometheus-client` Python library
- [x] Add prometheus-client to `requirements.txt`
- [x] Create metrics module (`app/core/metrics.py`)
- [x] Initialize Prometheus registry

### RED Metrics - Rate
- [x] Create counter metric for request rate per endpoint
- [x] Track: `http_requests_total{method, endpoint, status}`
- [x] Increment counter on each request
- [x] Calculate requests/second from counter

### RED Metrics - Errors
- [x] Create counter metric for error rate per endpoint
- [x] Track: `http_errors_total{method, endpoint, status_code}`
- [x] Track 4xx errors separately from 5xx errors
- [x] Calculate error rate percentage

### RED Metrics - Duration
- [x] Create histogram metric for request latency
- [x] Track: `http_request_duration_seconds{method, endpoint}`
- [x] Calculate percentiles: p50, p95, p99, p999
- [x] Track latency for each endpoint separately

### Business Metrics
- [x] Create counter for zero-result searches: `search_zero_results_total{query}`
- [x] Create counter for cache hits: `cache_hits_total{cache_type}`
- [x] Create counter for cache misses: `cache_misses_total{cache_type}`
- [x] Create histogram for ranking scores: `ranking_score_distribution{product_id}`
- [x] Calculate zero-result rate percentage
- [x] Calculate cache hit rate percentage

### Resource Metrics
- [x] Create gauge for CPU usage: `system_cpu_usage_percent`
- [x] Create gauge for memory usage: `system_memory_usage_bytes`
- [x] Create gauge for database connection pool: `db_connection_pool_size{state}`
- [x] Track active vs idle connections

### Metrics Endpoint
- [x] Create `/metrics` endpoint in FastAPI
- [x] Expose Prometheus format metrics
- [x] Ensure endpoint is accessible (no auth required for Prometheus scraping)
- [x] Test metrics endpoint returns valid Prometheus format

### Grafana Dashboards
- [x] Set up Grafana instance (or configure access)
- [x] Create dashboard: Service Health Overview
  - [x] Request rate per endpoint
  - [x] Error rate per endpoint
  - [x] Latency percentiles (p50, p95, p99)
  - [x] CPU and memory usage
- [x] Create dashboard: Search Performance
  - [x] Search request rate
  - [x] Search latency (p50, p95, p99)
  - [x] Search error rate
  - [x] Zero-result rate
  - [x] Cache hit rate for searches
- [x] Create dashboard: Recommendation Performance
  - [x] Recommendation request rate
  - [x] Recommendation latency (p50, p95, p99)
  - [x] Recommendation error rate
  - [x] Cache hit rate for recommendations
- [x] Create dashboard: Database Health
  - [x] Connection pool usage
  - [x] Query latency
  - [x] Connection pool exhaustion alerts
- [x] Create dashboard: Cache Performance
  - [x] Cache hit rate by type
  - [x] Cache miss rate by type
  - [x] Cache operation latency

### Testing
- [x] Write unit tests for metrics collection
- [x] Verify metrics are correctly incremented
- [x] Test metrics endpoint returns expected format
- [x] Verify Grafana dashboards display data correctly (requires Grafana setup)

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

---

## AI Integration: Phase 1 - Query Understanding (Tier 1) - Parallel Track

**Note**: AI Phase 1 can be implemented in parallel with Phase 1 observability. It enhances query understanding without blocking core observability work.

**Goal**: Implement AI Orchestration Layer with Tier 1 LLM agents for query understanding

**Architecture Alignment**: Implements the AI Orchestration Layer pattern from `specs/AI_ARCHITECTURE.md`

### Setup & Configuration
- [ ] Set up Redis for caching (mandatory before LLM calls) - **Required for AI Phase 1**
- [ ] Set up LLM API client (OpenAI GPT-3.5 Turbo for Tier 1)
- [ ] Add LLM client dependencies to `requirements.txt`
- [ ] Create AI services directory structure (`app/services/ai/`)

### AI Orchestration Layer
- [ ] Create `AIOrchestrationService` in `backend/app/services/ai/orchestration.py`
- [ ] Implement orchestration logic to decide pipeline (search/recommend/clarify)
- [ ] Implement confidence threshold enforcement
- [ ] Implement fallback to deterministic systems
- [ ] Add orchestration middleware before search execution

### Intent Classification Agent (Tier 1)
- [ ] Create `IntentClassificationAgent` (Tier 1) in `backend/app/services/ai/agents/intent.py`
- [ ] Implement intent classification with structured JSON output
- [ ] Implement cache-first flow (check cache → LLM → cache result)
- [ ] Configure cache TTL (24h for intent classification)
- [ ] Implement schema validation for intent outputs
- [ ] Add timeout handling (fallback to keyword search)
- [ ] Add error handling (fallback to keyword search)

### Query Rewrite & Entity Extraction Agent (Tier 1)
- [ ] Create `QueryRewriteAgent` (Tier 1) in `backend/app/services/ai/agents/rewrite.py`
- [ ] Implement query rewriting with structured JSON output
- [ ] Implement entity extraction (brand, category, attributes)
- [ ] Implement cache-first flow (check cache → LLM → cache result)
- [ ] Configure cache TTL (24h for query rewrite)
- [ ] Implement schema validation for rewrite outputs
- [ ] Add timeout handling (fallback to original query)
- [ ] Add error handling (fallback to original query)

### Caching Strategy
- [ ] Implement Redis caching for intent classification results
- [ ] Implement Redis caching for query rewrite results
- [ ] Implement cache key generation (hash of query)
- [ ] Implement cache invalidation strategy
- [ ] Add cache hit/miss metrics

### Integration with Search Pipeline
- [ ] Update search endpoint to use orchestrated queries (with fallback)
- [ ] Integrate intent classification before search
- [ ] Integrate query rewrite before search
- [ ] Maintain backward compatibility (keyword search still works)
- [ ] Add feature flag for AI orchestration (enable/disable)

### LLMOps Metrics
- [ ] Add metric: `llm_requests_total{agent, model, tier}`
- [ ] Add metric: `llm_latency_ms_bucket{agent, tier}` (histogram)
- [ ] Add metric: `llm_cache_hit_total{agent}`
- [ ] Add metric: `llm_cache_miss_total{agent}`
- [ ] Add metric: `llm_errors_total{agent, reason}`
- [ ] Add metric: `llm_schema_validation_failures_total{agent}`
- [ ] Add metric: `llm_low_confidence_total{agent}`
- [ ] Calculate cache hit rate: `llm_cache_hit_rate{agent}`

### Circuit Breakers
- [ ] Implement circuit breaker for LLM API calls
- [ ] Configure failure threshold (50% error rate over 1 minute)
- [ ] Configure open duration (30 seconds)
- [ ] Configure half-open test traffic (10%)
- [ ] Add circuit breaker state metrics
- [ ] Implement automatic fallback to deterministic systems

### Testing
- [ ] Write unit tests for intent classification agent
- [ ] Write unit tests for query rewrite agent
- [ ] Write unit tests for AI orchestration service
- [ ] Write unit tests for caching logic
- [ ] Write unit tests for circuit breakers
- [ ] Write integration tests for AI-enhanced search endpoint
- [ ] Test fallback mechanisms (LLM timeout, error, circuit breaker open)
- [ ] Test cache hit/miss scenarios
- [ ] Performance test: Query understanding latency (target: p95 <80ms with cache)

### A/B Testing Setup
- [ ] Create A/B test framework for enhanced vs. baseline queries
- [ ] Implement traffic splitting (50/50 or configurable)
- [ ] Track experiment metrics (zero-result rate, CTR, latency)
- [ ] Create experiment dashboard
- [ ] Document A/B test results

### Success Criteria Verification
- [ ] Verify 15-25% reduction in zero-result searches
- [ ] Verify 10-20% improvement in click-through rates
- [ ] Verify query understanding latency: p95 <80ms (with caching)
- [ ] Verify cache hit rate: >80%
- [ ] Verify LLM error rate: <1%
- [ ] Verify schema validation pass rate: 100%

### Documentation
- [ ] Document AI orchestration layer architecture
- [ ] Document intent classification agent usage
- [ ] Document query rewrite agent usage
- [ ] Document caching strategy
- [ ] Document circuit breaker configuration
- [ ] Document LLMOps metrics
- [ ] Update API documentation with AI-enhanced endpoints
- [ ] Create developer guide for adding new AI agents

### References
- AI Phase 1 specification: `/docs/AI_strategy_memo.md` (Phase 1: Query Understanding)
- AI Architecture: `/specs/AI_ARCHITECTURE.md`
- Phase 1 specification: `/docs/implementation_phases.md`

---

## References

- Phase 1 specification: `/docs/implementation_phases.md`
- Observability spec: `/specs/OBSERVABILITY.md`
- Architecture: `/specs/ARCHITECTURE.md`
- **AI Strategy Memo**: `/docs/AI_strategy_memo.md`
- **AI Architecture**: `/specs/AI_ARCHITECTURE.md`

