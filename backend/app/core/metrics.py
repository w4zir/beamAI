"""
Prometheus metrics collection module.

This module provides comprehensive metrics collection following the observability
specification in /specs/OBSERVABILITY.md and Phase 1.2 requirements.

Metrics Categories:
- RED Metrics: Rate, Errors, Duration
- Business Metrics: Zero-result searches, cache hits/misses, ranking scores
- Resource Metrics: CPU, memory, database connection pool
- Semantic Search Metrics: Semantic search specific metrics

All metrics follow Prometheus naming conventions:
- Counters: _total suffix
- Histograms: _seconds suffix for duration, _distribution for distributions
- Gauges: No special suffix
"""
import time
import psutil
from typing import Optional, Dict
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    REGISTRY,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.core import CollectorRegistry

from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize Prometheus registry
# Using default REGISTRY for simplicity (can be customized if needed)
registry = REGISTRY

# ============================================================================
# RED METRICS - Rate, Errors, Duration
# ============================================================================

# Rate: HTTP requests total
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

# Errors: HTTP errors total (separate 4xx and 5xx)
http_errors_total = Counter(
    "http_errors_total",
    "Total number of HTTP errors",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

# Duration: HTTP request latency histogram
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# Zero-result searches
search_zero_results_total = Counter(
    "search_zero_results_total",
    "Total number of searches that returned zero results",
    ["query_pattern"],  # Can be normalized query pattern for grouping
    registry=registry,
)

# Cache hits and misses (Phase 3.1)
cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type", "cache_layer"],  # e.g., "search", "query_result"
    registry=registry,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type", "cache_layer"],
    registry=registry,
)

# Cache operation latency (Phase 3.1)
cache_operation_latency_seconds = Histogram(
    "cache_operation_latency_seconds",
    "Cache operation latency in seconds",
    ["cache_type", "operation"],  # operation: "get", "set", "delete"
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=registry,
)

# Cache errors (Phase 3.1)
cache_errors_total = Counter(
    "cache_errors_total",
    "Total number of cache errors",
    ["cache_type", "reason"],  # reason: "timeout", "connection_error", etc.
    registry=registry,
)

# Cache invalidations (Phase 3.1)
cache_invalidations_total = Counter(
    "cache_invalidations_total",
    "Total number of cache invalidations",
    ["cache_type", "reason"],  # reason: "product_update", "manual", etc.
    registry=registry,
)

# Circuit breaker state (Phase 3.1, 3.3)
cache_circuit_breaker_state = Gauge(
    "cache_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    ["circuit_breaker_name"],
    registry=registry,
)

# Rate limiting metrics (Phase 3.2)
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total number of rate limit hits",
    ["endpoint", "type"],  # type: "ip", "api_key"
    registry=registry,
)

rate_limit_abuse_detected_total = Counter(
    "rate_limit_abuse_detected_total",
    "Total number of abuse patterns detected",
    ["pattern"],  # pattern: "same_query", "sequential_enumeration"
    registry=registry,
)

rate_limit_whitelist_size = Gauge(
    "rate_limit_whitelist_size",
    "Number of IPs/keys in whitelist",
    registry=registry,
)

rate_limit_blacklist_size = Gauge(
    "rate_limit_blacklist_size",
    "Number of IPs/keys in blacklist",
    registry=registry,
)

# Circuit breaker metrics (Phase 3.3)
circuit_breaker_state_changes_total = Counter(
    "circuit_breaker_state_changes_total",
    "Total number of circuit breaker state changes",
    ["circuit_breaker_name", "from_state", "to_state"],
    registry=registry,
)

circuit_breaker_failures_total = Counter(
    "circuit_breaker_failures_total",
    "Total number of circuit breaker failures",
    ["circuit_breaker_name"],
    registry=registry,
)

# Database metrics (Phase 3.4)
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],  # query_type: "search", "recommendation", "feature"
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry,
)

db_slow_queries_total = Counter(
    "db_slow_queries_total",
    "Total number of slow queries (>100ms)",
    ["query_type", "threshold"],  # threshold: "100ms"
    registry=registry,
)

db_replication_lag_seconds = Gauge(
    "db_replication_lag_seconds",
    "Database replication lag in seconds",
    ["replica"],
    registry=registry,
)

db_replica_health = Gauge(
    "db_replica_health",
    "Database replica health (1=healthy, 0=unhealthy)",
    ["replica"],
    registry=registry,
)

# Async operation metrics (Phase 3.5)
async_operation_duration_seconds = Histogram(
    "async_operation_duration_seconds",
    "Async operation duration in seconds",
    ["operation_type"],  # operation_type: "feature_fetch", "cache_lookup", etc.
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

# Ranking score distribution
ranking_score_distribution = Histogram(
    "ranking_score_distribution",
    "Distribution of ranking scores",
    ["product_id"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry,
)

# ============================================================================
# SEMANTIC SEARCH METRICS
# ============================================================================

semantic_search_requests_total = Counter(
    "semantic_search_requests_total",
    "Total number of semantic search requests",
    registry=registry,
)

semantic_search_latency_seconds = Histogram(
    "semantic_search_latency_seconds",
    "Semantic search latency in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry,
)

semantic_embedding_generation_latency_seconds = Histogram(
    "semantic_embedding_generation_latency_seconds",
    "Semantic embedding generation latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=registry,
)

semantic_faiss_search_latency_seconds = Histogram(
    "semantic_faiss_search_latency_seconds",
    "FAISS index search latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
    registry=registry,
)

semantic_search_fallback_total = Counter(
    "semantic_search_fallback_total",
    "Total number of semantic search fallbacks to keyword-only",
    registry=registry,
)

# ============================================================================
# COLLABORATIVE FILTERING METRICS
# ============================================================================

cf_scoring_requests_total = Counter(
    "cf_scoring_requests_total",
    "Total number of CF scoring requests",
    registry=registry,
)

cf_scoring_latency_seconds = Histogram(
    "cf_scoring_latency_seconds",
    "CF scoring latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

cf_cold_start_total = Counter(
    "cf_cold_start_total",
    "Total number of cold start cases",
    ["cold_start_type"],  # "new_user", "new_product"
    registry=registry,
)

cf_model_staleness_seconds = Gauge(
    "cf_model_staleness_seconds",
    "Time since last model training in seconds",
    registry=registry,
)

# ============================================================================
# RESOURCE METRICS
# ============================================================================

# CPU usage gauge
system_cpu_usage_percent = Gauge(
    "system_cpu_usage_percent",
    "System CPU usage percentage",
    registry=registry,
)

# Memory usage gauge
system_memory_usage_bytes = Gauge(
    "system_memory_usage_bytes",
    "System memory usage in bytes",
    registry=registry,
)

# Database connection pool (placeholder - will be implemented when connection pooling is added)
db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["state"],  # "active", "idle", "total"
    registry=registry,
)

# Semantic Search Resource Metrics
semantic_index_memory_bytes = Gauge(
    "semantic_index_memory_bytes",
    "FAISS index memory usage in bytes",
    registry=registry,
)

semantic_index_total_products = Gauge(
    "semantic_index_total_products",
    "Total number of products in FAISS index",
    registry=registry,
)

semantic_index_available = Gauge(
    "semantic_index_available",
    "Whether semantic search index is available (1 = available, 0 = unavailable)",
    registry=registry,
)

# ============================================================================
# QUERY ENHANCEMENT METRICS
# ============================================================================

query_enhancement_requests_total = Counter(
    "query_enhancement_requests_total",
    "Total number of query enhancement requests",
    registry=registry,
)

query_spell_correction_total = Counter(
    "query_spell_correction_total",
    "Total number of spell correction attempts",
    ["applied"],  # "true" or "false"
    registry=registry,
)

query_spell_correction_confidence = Histogram(
    "query_spell_correction_confidence",
    "Distribution of spell correction confidence scores",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry,
)

query_synonym_expansion_total = Counter(
    "query_synonym_expansion_total",
    "Total number of synonym expansion attempts",
    ["applied"],  # "true" or "false"
    registry=registry,
)

query_classification_distribution = Counter(
    "query_classification_distribution",
    "Distribution of query classifications",
    ["classification"],  # "navigational", "informational", "transactional"
    registry=registry,
)

query_enhancement_latency_seconds = Histogram(
    "query_enhancement_latency_seconds",
    "Query enhancement latency in seconds",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)


# ============================================================================
# LLM / AI ORCHESTRATION METRICS
# ============================================================================

llm_requests_total = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["agent", "model", "tier"],
    registry=registry,
)

llm_errors_total = Counter(
    "llm_errors_total",
    "Total number of LLM errors",
    ["agent", "reason"],
    registry=registry,
)

llm_latency_ms = Histogram(
    "llm_latency_ms",
    "LLM request latency in milliseconds",
    ["agent", "tier"],
    # Focus on fast Tier 1 SLA (p95 < 80ms) but allow slower tails
    buckets=[5, 10, 20, 40, 80, 150, 300, 500, 1000],
    registry=registry,
)

llm_cache_hit_total = Counter(
    "llm_cache_hit_total",
    "Total number of LLM cache hits",
    ["agent"],
    registry=registry,
)

llm_cache_miss_total = Counter(
    "llm_cache_miss_total",
    "Total number of LLM cache misses",
    ["agent"],
    registry=registry,
)

llm_schema_validation_failures_total = Counter(
    "llm_schema_validation_failures_total",
    "Total number of LLM schema validation failures",
    ["agent"],
    registry=registry,
)

llm_low_confidence_total = Counter(
    "llm_low_confidence_total",
    "Total number of low-confidence LLM results",
    ["agent"],
    registry=registry,
)

llm_tokens_input_total = Counter(
    "llm_tokens_input_total",
    "Total number of input tokens sent to LLMs",
    ["agent", "model"],
    registry=registry,
)

llm_tokens_output_total = Counter(
    "llm_tokens_output_total",
    "Total number of output tokens received from LLMs",
    ["agent", "model"],
    registry=registry,
)

llm_cost_usd_total = Counter(
    "llm_cost_usd_total",
    "Total estimated LLM cost in USD",
    ["agent", "model"],
    registry=registry,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_endpoint(path: str) -> str:
    """
    Normalize endpoint path for metrics.
    
    Replaces dynamic segments (like user_id, product_id) with placeholders
    to avoid high cardinality in metrics.
    
    Examples:
        /recommend/user123 -> /recommend/{user_id}
        /search?q=test -> /search
        /health -> /health
    
    Args:
        path: Request path
        
    Returns:
        Normalized endpoint path
    """
    # Remove query parameters
    if "?" in path:
        path = path.split("?")[0]
    
    # Normalize common patterns
    # /recommend/{user_id} pattern
    if path.startswith("/recommend/"):
        parts = path.split("/")
        if len(parts) >= 3:
            return "/recommend/{user_id}"
    
    # Keep other paths as-is (they're already normalized)
    return path


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """
    Record HTTP request metrics (RED metrics).
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: Normalized endpoint path
        status_code: HTTP status code
        duration_seconds: Request duration in seconds
    """
    # Normalize endpoint
    normalized_endpoint = normalize_endpoint(endpoint)
    
    # Record request count
    http_requests_total.labels(
        method=method,
        endpoint=normalized_endpoint,
        status=str(status_code),
    ).inc()
    
    # Record errors (4xx and 5xx)
    if status_code >= 400:
        http_errors_total.labels(
            method=method,
            endpoint=normalized_endpoint,
            status_code=str(status_code),
        ).inc()
    
    # Record duration
    http_request_duration_seconds.labels(
        method=method,
        endpoint=normalized_endpoint,
    ).observe(duration_seconds)


def record_search_zero_result(query: Optional[str] = None) -> None:
    """
    Record a zero-result search.
    
    Args:
        query: Search query (optional, for pattern matching)
    """
    # Normalize query pattern (first 20 chars or "empty")
    query_pattern = "empty" if not query else query[:20].lower()
    search_zero_results_total.labels(query_pattern=query_pattern).inc()


def record_cache_hit(cache_type: str, cache_layer: str = "unknown") -> None:
    """
    Record a cache hit.
    
    Args:
        cache_type: Type of cache (e.g., "search", "recommendation", "features")
        cache_layer: Cache layer (e.g., "query_result", "feature", "ranking")
    """
    cache_hits_total.labels(cache_type=cache_type, cache_layer=cache_layer).inc()


def record_cache_miss(cache_type: str, cache_layer: str = "unknown") -> None:
    """
    Record a cache miss.
    
    Args:
        cache_type: Type of cache (e.g., "search", "recommendation", "features")
        cache_layer: Cache layer (e.g., "query_result", "feature", "ranking")
    """
    cache_misses_total.labels(cache_type=cache_type, cache_layer=cache_layer).inc()


def record_cache_operation_latency(cache_type: str, operation: str, duration_seconds: float) -> None:
    """
    Record cache operation latency.
    
    Args:
        cache_type: Type of cache
        operation: Operation type ("get", "set", "delete")
        duration_seconds: Operation duration in seconds
    """
    cache_operation_latency_seconds.labels(cache_type=cache_type, operation=operation).observe(duration_seconds)


def record_cache_error(cache_type: str, reason: str) -> None:
    """
    Record a cache error.
    
    Args:
        cache_type: Type of cache
        reason: Error reason ("timeout", "connection_error", etc.)
    """
    cache_errors_total.labels(cache_type=cache_type, reason=reason).inc()


def record_cache_invalidation(cache_type: str, reason: str) -> None:
    """
    Record a cache invalidation.
    
    Args:
        cache_type: Type of cache
        reason: Invalidation reason ("product_update", "manual", etc.)
    """
    cache_invalidations_total.labels(cache_type=cache_type, reason=reason).inc()


def update_circuit_breaker_state(circuit_breaker_name: str, state: int) -> None:
    """
    Update circuit breaker state metric.
    
    Args:
        circuit_breaker_name: Name of circuit breaker
        state: State (0=closed, 1=open, 2=half-open)
    """
    cache_circuit_breaker_state.labels(circuit_breaker_name=circuit_breaker_name).set(state)


def record_rate_limit_hit(endpoint: str, limit_type: str) -> None:
    """
    Record a rate limit hit.
    
    Args:
        endpoint: Endpoint name
        limit_type: Type of limit ("ip", "api_key")
    """
    rate_limit_hits_total.labels(endpoint=endpoint, type=limit_type).inc()


def record_abuse_detection(pattern: str) -> None:
    """
    Record abuse pattern detection.
    
    Args:
        pattern: Abuse pattern ("same_query", "sequential_enumeration")
    """
    rate_limit_abuse_detected_total.labels(pattern=pattern).inc()


def update_rate_limit_list_sizes(whitelist_size: int, blacklist_size: int) -> None:
    """
    Update rate limit list sizes.
    
    Args:
        whitelist_size: Number of entries in whitelist
        blacklist_size: Number of entries in blacklist
    """
    rate_limit_whitelist_size.set(whitelist_size)
    rate_limit_blacklist_size.set(blacklist_size)


def record_circuit_breaker_state_change(circuit_breaker_name: str, from_state: str, to_state: str) -> None:
    """
    Record circuit breaker state change.
    
    Args:
        circuit_breaker_name: Name of circuit breaker
        from_state: Previous state
        to_state: New state
    """
    circuit_breaker_state_changes_total.labels(
        circuit_breaker_name=circuit_breaker_name,
        from_state=from_state,
        to_state=to_state
    ).inc()


def record_circuit_breaker_failure(circuit_breaker_name: str) -> None:
    """
    Record circuit breaker failure.
    
    Args:
        circuit_breaker_name: Name of circuit breaker
    """
    circuit_breaker_failures_total.labels(circuit_breaker_name=circuit_breaker_name).inc()


def record_db_query_duration(query_type: str, duration_seconds: float) -> None:
    """
    Record database query duration.
    
    Args:
        query_type: Type of query ("search", "recommendation", "feature")
        duration_seconds: Query duration in seconds
    """
    db_query_duration_seconds.labels(query_type=query_type).observe(duration_seconds)
    
    # Record slow queries (>100ms)
    if duration_seconds > 0.1:
        db_slow_queries_total.labels(query_type=query_type, threshold="100ms").inc()


def update_replication_lag(replica: str, lag_seconds: float) -> None:
    """
    Update replication lag metric.
    
    Args:
        replica: Replica name
        lag_seconds: Replication lag in seconds
    """
    db_replication_lag_seconds.labels(replica=replica).set(lag_seconds)


def update_replica_health(replica: str, healthy: bool) -> None:
    """
    Update replica health metric.
    
    Args:
        replica: Replica name
        healthy: Health status (True=healthy, False=unhealthy)
    """
    db_replica_health.labels(replica=replica).set(1 if healthy else 0)


def record_async_operation_duration(operation_type: str, duration_seconds: float) -> None:
    """
    Record async operation duration.
    
    Args:
        operation_type: Type of operation ("feature_fetch", "cache_lookup", etc.)
        duration_seconds: Operation duration in seconds
    """
    async_operation_duration_seconds.labels(operation_type=operation_type).observe(duration_seconds)


def record_ranking_score(product_id: str, score: float) -> None:
    """
    Record a ranking score for distribution analysis.
    
    Args:
        product_id: Product ID
        score: Ranking score (0.0 to 1.0)
    """
    ranking_score_distribution.labels(product_id=product_id).observe(score)


def update_resource_metrics() -> None:
    """
    Update system resource metrics (CPU, memory).
    
    This should be called periodically (e.g., every 10-30 seconds)
    or on-demand when metrics are scraped.
    """
    try:
        # CPU usage percentage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_cpu_usage_percent.set(cpu_percent)
        
        # Memory usage in bytes
        memory = psutil.virtual_memory()
        system_memory_usage_bytes.set(memory.used)
        
    except ImportError:
        # psutil not installed - skip resource metrics
        logger.debug("metrics_resource_update_skipped", reason="psutil not available")
    except Exception as e:
        logger.warning(
            "metrics_resource_update_failed",
            error=str(e),
            error_type=type(e).__name__,
        )


def update_db_pool_metrics(active: int = 0, idle: int = 0, total: int = 0) -> None:
    """
    Update database connection pool metrics.
    
    Args:
        active: Number of active connections
        idle: Number of idle connections
        total: Total number of connections
    """
    db_connection_pool_size.labels(state="active").set(active)
    db_connection_pool_size.labels(state="idle").set(idle)
    db_connection_pool_size.labels(state="total").set(total)


def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        Prometheus metrics text format
    """
    # Update resource metrics before returning
    update_resource_metrics()
    
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """
    Get content type for metrics endpoint.
    
    Returns:
        Content type string for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST


# ============================================================================
# QUERY ENHANCEMENT METRIC HELPERS
# ============================================================================

def record_query_enhancement(
    correction_applied: bool = False,
    correction_confidence: float = 0.0,
    expansion_applied: bool = False,
    classification: Optional[str] = None,
    latency_seconds: float = 0.0,
) -> None:
    """
    Record query enhancement metrics.
    
    Args:
        correction_applied: Whether spell correction was applied
        correction_confidence: Spell correction confidence score (0.0 to 1.0)
        expansion_applied: Whether synonym expansion was applied
        classification: Query classification (navigational/informational/transactional)
        latency_seconds: Query enhancement latency in seconds
    """
    # Record total requests
    query_enhancement_requests_total.inc()
    
    # Record spell correction
    query_spell_correction_total.labels(applied=str(correction_applied).lower()).inc()
    if correction_applied and correction_confidence > 0:
        query_spell_correction_confidence.observe(correction_confidence)
    
    # Record synonym expansion
    query_synonym_expansion_total.labels(applied=str(expansion_applied).lower()).inc()
    
    # Record classification
    if classification:
        query_classification_distribution.labels(classification=classification).inc()
    
    # Record latency
    if latency_seconds > 0:
        query_enhancement_latency_seconds.observe(latency_seconds)


# ============================================================================
# LLM METRIC HELPERS
# ============================================================================

def record_llm_request(
    agent: str,
    model: str,
    tier: str,
    duration_ms: float,
) -> None:
    """
    Record a single LLM request and its latency.

    Args:
        agent: Logical agent name (e.g., \"intent\", \"rewrite\")
        model: Model name (e.g., \"gpt-3.5-turbo\")
        tier: LLM tier (\"1\" or \"2\")
        duration_ms: Request duration in milliseconds
    """
    llm_requests_total.labels(agent=agent, model=model, tier=tier).inc()
    # Store latency in milliseconds histogram to align with AI specs
    llm_latency_ms.labels(agent=agent, tier=tier).observe(duration_ms)


def record_llm_cache_hit(agent: str) -> None:
    """Record an LLM cache hit for a given agent."""
    llm_cache_hit_total.labels(agent=agent).inc()


def record_llm_cache_miss(agent: str) -> None:
    """Record an LLM cache miss for a given agent."""
    llm_cache_miss_total.labels(agent=agent).inc()


def record_llm_error(agent: str, reason: str) -> None:
    """Record an LLM error with a reason label (e.g. timeout, api_error)."""
    llm_errors_total.labels(agent=agent, reason=reason).inc()


def record_llm_schema_validation_failure(agent: str) -> None:
    """Record a schema validation failure for a given agent."""
    llm_schema_validation_failures_total.labels(agent=agent).inc()


def record_llm_low_confidence(agent: str) -> None:
    """Record a low-confidence LLM output for a given agent."""
    llm_low_confidence_total.labels(agent=agent).inc()


def record_llm_tokens_and_cost(
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float = 0.0,
) -> None:
    """
    Record LLM token usage and estimated cost.

    Args:
        agent: Logical agent name
        model: Model name
        input_tokens: Number of prompt/input tokens
        output_tokens: Number of completion/output tokens
        cost_usd: Estimated cost in USD (can be 0.0 if not computed)
    """
    if input_tokens > 0:
        llm_tokens_input_total.labels(agent=agent, model=model).inc(input_tokens)
    if output_tokens > 0:
        llm_tokens_output_total.labels(agent=agent, model=model).inc(output_tokens)
    if cost_usd > 0:
        llm_cost_usd_total.labels(agent=agent, model=model).inc(cost_usd)

