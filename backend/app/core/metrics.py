"""
Prometheus metrics for observability.

According to OBSERVABILITY.md:
- RED metrics (Rate, Errors, Duration)
- Business metrics
- Resource metrics
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST

# RED Metrics - Rate
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

# RED Metrics - Errors
http_errors_total = Counter(
    'http_errors_total',
    'Total number of HTTP errors',
    ['method', 'endpoint', 'status_code']
)

# RED Metrics - Duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Business Metrics
search_zero_results_total = Counter(
    'search_zero_results_total',
    'Total number of searches with zero results',
    ['query_type']
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

ranking_score_distribution = Histogram(
    'ranking_score_distribution',
    'Distribution of ranking scores',
    ['product_id'],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# Semantic Search Metrics
semantic_search_requests_total = Counter(
    'semantic_search_requests_total',
    'Total number of semantic search requests'
)

semantic_search_latency_seconds = Histogram(
    'semantic_search_latency_seconds',
    'Semantic search latency in seconds',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

semantic_embedding_generation_latency_seconds = Histogram(
    'semantic_embedding_generation_latency_seconds',
    'Semantic embedding generation latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

semantic_faiss_search_latency_seconds = Histogram(
    'semantic_faiss_search_latency_seconds',
    'FAISS index search latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

semantic_search_fallback_total = Counter(
    'semantic_search_fallback_total',
    'Total number of semantic search fallbacks to keyword-only'
)

# Resource Metrics
system_cpu_usage_percent = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_memory_usage_bytes = Gauge(
    'system_memory_usage_bytes',
    'System memory usage in bytes'
)

db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    ['state']  # 'active' or 'idle'
)

# Semantic Search Resource Metrics
semantic_index_memory_bytes = Gauge(
    'semantic_index_memory_bytes',
    'FAISS index memory usage in bytes'
)

semantic_index_total_products = Gauge(
    'semantic_index_total_products',
    'Total number of products in FAISS index'
)

semantic_index_available = Gauge(
    'semantic_index_available',
    'Whether semantic search index is available (1 = available, 0 = unavailable)'
)


def get_metrics():
    """
    Get Prometheus metrics in text format.
    
    Returns:
        Tuple of (metrics_text, content_type)
    """
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST

