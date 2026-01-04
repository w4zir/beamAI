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

# Cache hits and misses
cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
    ["cache_type"],  # e.g., "search", "recommendation", "features"
    registry=registry,
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
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


def record_cache_hit(cache_type: str) -> None:
    """
    Record a cache hit.
    
    Args:
        cache_type: Type of cache (e.g., "search", "recommendation", "features")
    """
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str) -> None:
    """
    Record a cache miss.
    
    Args:
        cache_type: Type of cache (e.g., "search", "recommendation", "features")
    """
    cache_misses_total.labels(cache_type=cache_type).inc()


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

