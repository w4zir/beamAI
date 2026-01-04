# How It Works

This document provides a detailed explanation of each component of the BeamAI search and recommendation system, including algorithms and code snippets.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Structured Logging](#structured-logging)
3. [Prometheus Metrics Collection](#prometheus-metrics-collection)
4. [Search Service](#search-service)
5. [Recommendation Service](#recommendation-service)
6. [Ranking Service](#ranking-service)
7. [Feature Computation](#feature-computation)
8. [Event Tracking](#event-tracking)
9. [Request Flow](#request-flow)

---

## System Architecture

The system follows a **separation of concerns** architecture where retrieval, ranking, and serving are independent components.

### High-Level Components

- **FastAPI Gateway**: Request validation and orchestration only
- **Search Service**: Keyword search (Postgres FTS) - returns candidates only
- **Recommendation Service**: Popularity-based recommendations - returns candidates only
- **Ranking Service**: Deterministic scoring using Phase 1 formula - final ordering

### Core Principles

1. **Retrieval is separate from ranking**: Search/recommendation services return candidates, ranking service orders them
2. **Offline training, online serving**: Features are computed offline, models are trained separately
3. **Fail gracefully**: Every component has fallback mechanisms

---

## Structured Logging

The system uses **structured JSON logging** with trace ID propagation for observability and debugging.

### Logging Configuration

Logging is configured using `structlog` and supports both JSON (production) and console (development) formats:

```67:118:backend/app/core/logging.py
def configure_logging(
    log_level: str = "INFO",
    service_name: Optional[str] = None,
    json_output: bool = True
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Service name identifier (defaults to SERVICE_NAME)
        json_output: If True, output JSON format (for production). If False, use console format (for dev)
    """
    global SERVICE_NAME
    if service_name:
        SERVICE_NAME = service_name
    
    # Configure processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context variables
        structlog.stdlib.add_log_level,  # Add log level
        structlog.stdlib.add_logger_name,  # Add logger name
        add_trace_context,  # Add trace context (trace_id, request_id, user_id, service)
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamp
        structlog.processors.StackInfoRenderer(),  # Stack traces
        structlog.processors.format_exc_info,  # Exception formatting
    ]
    
    if json_output:
        # JSON output for production (containerized environments)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
```

### Core Logging Fields

Every log entry includes:
- **timestamp**: ISO 8601 format (UTC)
- **level**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **service**: Service name identifier (`beamai_search_api`)
- **trace_id**: Correlation ID for request tracing (UUID v4)
- **request_id**: Unique ID per request (UUID v4)
- **user_id**: User identifier (when available)

### Trace ID Propagation

Trace IDs are propagated through HTTP headers and context variables:

```39:133:backend/app/core/middleware.py
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add trace ID context.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with trace ID in headers
        """
        # Extract trace ID from headers (check both X-Trace-ID and X-Request-ID)
        trace_id = (
            request.headers.get("X-Trace-ID") or 
            request.headers.get("X-Request-ID")
        )
        
        # Generate new trace ID if not present
        if not trace_id:
            trace_id = generate_trace_id()
        
        # Generate unique request ID for this request
        request_id = generate_request_id()
        
        # Extract user ID from query params or headers (if available)
        # This is optional and may not be present for all requests
        user_id = (
            request.query_params.get("user_id") or
            request.headers.get("X-User-ID")
        )
        
        # Set context variables for this request
        set_trace_id(trace_id)
        set_request_id(request_id)
        if user_id:
            set_user_id(user_id)
        
        # Log request start
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate latency
            process_time = time.time() - start_time
            latency_ms = int(process_time * 1000)
            
            # Log request completion
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=latency_ms,
            )
            
            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate latency even on error
            process_time = time.time() - start_time
            latency_ms = int(process_time * 1000)
            
            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                latency_ms=latency_ms,
                exc_info=True,
            )
            
            # Re-raise exception (let FastAPI error handlers deal with it)
            raise
        finally:
            # Clear context variables after request completes
            # (ContextVar automatically handles this per async task, but explicit is better)
            set_trace_id(None)
            set_request_id(None)
            set_user_id(None)
```

**Trace ID Flow:**
1. Extract from `X-Trace-ID` or `X-Request-ID` headers (if present)
2. Generate new UUID v4 if not present
3. Store in context variable (`trace_id_var`)
4. Automatically included in all log entries via `add_trace_context` processor
5. Returned in response headers (`X-Trace-ID`)

### Search Endpoint Logging

Search endpoints log structured events with relevant context:

```55:115:backend/app/routes/search.py
        logger.info(
            "search_started",
            query=query,
            user_id=user_id,
            k=k,
        )
        
        # Get candidates from search service
        candidates = search_keywords(query, limit=k * 2)
        
        if not candidates:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "search_zero_results",
                query=query,
                user_id=user_id,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
            )
            return []
        
        # Apply ranking
        try:
            ranked = rank_products(candidates, is_search=True, user_id=user_id)
            
            # Format results
            results = [
                SearchResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (search: {breakdown['search_score']:.3f}, popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
        except Exception as ranking_error:
            logger.warning(
                "search_ranking_failed",
                query=query,
                error=str(ranking_error),
                error_type=type(ranking_error).__name__,
            )
            # Fallback: sort by search_score
            candidates.sort(key=lambda x: x[1], reverse=True)
            results = [
                SearchResult(
                    product_id=product_id,
                    score=score,
                    reason=f"Keyword match score: {score:.3f} (ranking unavailable)"
                )
                for product_id, score in candidates[:k]
            ]
        
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "search_completed",
            query=query,
            user_id=user_id,
            results_count=len(results),
            latency_ms=latency_ms,
            cache_hit=cache_hit,
        )
```

**Search Log Events:**
- `search_started`: Query initiated (includes `query`, `user_id`, `k`)
- `search_completed`: Query finished (includes `query`, `user_id`, `results_count`, `latency_ms`, `cache_hit`)
- `search_zero_results`: No results found (includes `query`, `user_id`, `latency_ms`, `cache_hit`)
- `search_error`: Error occurred (includes `query`, `user_id`, `error`, `error_type`, `latency_ms`)

### Ranking Service Logging

Ranking service logs scoring operations:

```85:179:backend/app/services/ranking/score.py
    logger.info(
        "ranking_started",
        is_search=is_search,
        user_id=user_id,
        candidates_count=len(candidates),
        weights=WEIGHTS,
    )
    
    # Extract product IDs and search scores
    product_ids = [product_id for product_id, _ in candidates]
    search_scores = {product_id: score for product_id, score in candidates}
    
    # Get product features
    features = get_product_features(product_ids)
    
    if not features:
        logger.warning(
            "ranking_no_features",
            is_search=is_search,
            user_id=user_id,
            candidates_count=len(candidates),
        )
        # Fallback: return candidates sorted by search_score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [
            (product_id, score, {"search_score": score, "cf_score": 0.0, "popularity_score": 0.0, "freshness_score": 0.0})
            for product_id, score in candidates
        ]
    
    # Compute final scores
    ranked_results = []
    
    for product_id, search_score in candidates:
        if product_id not in features:
            logger.warning(
                "ranking_product_features_missing",
                product_id=product_id,
                is_search=is_search,
                user_id=user_id,
            )
            continue
        
        product_features = features[product_id]
        popularity_score = product_features.get("popularity_score", 0.0)
        freshness_score = product_features.get("freshness_score", 0.0)
        
        # For recommendations, search_score is 0
        if not is_search:
            search_score = 0.0
        
        # cf_score is 0 in Phase 1
        cf_score = 0.0
        
        # Compute final score
        final_score = compute_final_score(
            search_score=search_score,
            cf_score=cf_score,
            popularity_score=popularity_score,
            freshness_score=freshness_score
        )
        
        # Create breakdown for explainability
        breakdown = {
            "search_score": search_score,
            "cf_score": cf_score,
            "popularity_score": popularity_score,
            "freshness_score": freshness_score
        }
        
        # Log ranking for each product
        logger.debug(
            "ranking_product_scored",
            product_id=product_id,
            final_score=final_score,
            score_breakdown=breakdown,
            feature_values={
                "popularity_score": popularity_score,
                "freshness_score": freshness_score,
            },
            is_search=is_search,
            user_id=user_id,
        )
        
        ranked_results.append((product_id, final_score, breakdown))
    
    # Sort by final_score descending
    ranked_results.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(
        "ranking_completed",
        is_search=is_search,
        user_id=user_id,
        ranked_count=len(ranked_results),
        candidates_count=len(candidates),
    )
```

**Ranking Log Events:**
- `ranking_started`: Ranking initiated (includes `is_search`, `user_id`, `candidates_count`, `weights`)
- `ranking_completed`: Ranking finished (includes `is_search`, `user_id`, `ranked_count`, `candidates_count`)
- `ranking_product_scored`: Individual product scoring (DEBUG level, includes `product_id`, `final_score`, `score_breakdown`)

### Example Log Entry

**JSON Format (Production):**
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

**Console Format (Development):**
```
2026-01-02T10:30:45.123456Z [info     ] search_completed          [beamai_search_api] cache_hit=False latency_ms=87 query="running shoes" request_id=req-123-456 results_count=42 trace_id=abc123-def456-ghi789 user_id=user_789
```

---

## Prometheus Metrics Collection

The system implements comprehensive metrics collection using Prometheus (Phase 1.2 implementation) following the RED metrics pattern (Rate, Errors, Duration) plus business and resource metrics.

### Metrics Architecture

```
Backend API (FastAPI)
    ↓ (exposes /metrics endpoint)
Prometheus (scrapes every 15s)
    ↓ (data source)
Grafana (visualizes in dashboards)
```

### Metrics Module

Metrics are defined in `app/core/metrics.py` using the `prometheus-client` library:

```38:65:backend/app/core/metrics.py
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
```

### RED Metrics (Rate, Errors, Duration)

**Rate Metrics:**

Tracks request rate per endpoint using counters:

```167:190:backend/app/core/metrics.py
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
```

**Error Metrics:**

Separate tracking for 4xx (client errors) and 5xx (server errors):

```192:198:backend/app/core/metrics.py
    # Record errors (4xx and 5xx)
    if status_code >= 400:
        http_errors_total.labels(
            method=method,
            endpoint=normalized_endpoint,
            status_code=str(status_code),
        ).inc()
```

**Duration Metrics:**

Latency histogram with configurable buckets for percentile calculations:

```200:204:backend/app/core/metrics.py
    # Record duration
    http_request_duration_seconds.labels(
        method=method,
        endpoint=normalized_endpoint,
    ).observe(duration_seconds)
```

**Buckets:** [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0] seconds
- Enables calculation of p50, p95, p99, p999 percentiles
- Example PromQL: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`

### Business Metrics

**Zero-Result Searches:**

Tracks searches that return no results:

```72:77:backend/app/core/metrics.py
# Zero-result searches
search_zero_results_total = Counter(
    "search_zero_results_total",
    "Total number of searches that returned zero results",
    ["query_pattern"],  # Can be normalized query pattern for grouping
    registry=registry,
)
```

Recording zero results:

```207:216:backend/app/core/metrics.py
def record_search_zero_result(query: Optional[str] = None) -> None:
    """
    Record a zero-result search.
    
    Args:
        query: Search query (optional, for pattern matching)
    """
    # Normalize query pattern (first 20 chars or "empty")
    query_pattern = "empty" if not query else query[:20].lower()
    search_zero_results_total.labels(query_pattern=query_pattern).inc()
```

**Cache Metrics:**

Tracks cache hits and misses by cache type:

```79:92:backend/app/core/metrics.py
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
```

**Ranking Score Distribution:**

Histogram of ranking scores for analysis:

```94:101:backend/app/core/metrics.py
# Ranking score distribution
ranking_score_distribution = Histogram(
    "ranking_score_distribution",
    "Distribution of ranking scores",
    ["product_id"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry,
)
```

### Resource Metrics

**CPU and Memory Usage:**

System resource metrics updated on each scrape:

```107:119:backend/app/core/metrics.py
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
```

Updating resource metrics:

```250:274:backend/app/core/metrics.py
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
```

**Database Connection Pool:**

Tracks connection pool utilization:

```121:127:backend/app/core/metrics.py
# Database connection pool (placeholder - will be implemented when connection pooling is added)
db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["state"],  # "active", "idle", "total"
    registry=registry,
)
```

### Metrics Endpoint

The `/metrics` endpoint exposes Prometheus-formatted metrics:

```17:42:backend/app/routes/metrics.py
@router.get("", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    No authentication required (standard Prometheus practice).
    """
    try:
        metrics_data = get_metrics()
        return Response(
            content=metrics_data,
            media_type=get_metrics_content_type(),
        )
    except Exception as e:
        logger.error(
            "metrics_endpoint_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Return empty metrics on error (better than failing completely)
        return Response(
            content=b"# Error collecting metrics\n",
            media_type=get_metrics_content_type(),
        )
```

Metrics are generated on-demand when scraped:

```291:301:backend/app/core/metrics.py
def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format.
    
    Returns:
        Prometheus metrics text format
    """
    # Update resource metrics before returning
    update_resource_metrics()
    
    return generate_latest(registry)
```

### Metrics Recording in Middleware

Metrics are automatically recorded for all HTTP requests via middleware:

```97:130:backend/app/core/middleware.py
            # Record metrics
            record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration_seconds=process_time,
            )
```

**Endpoint Normalization:**

Dynamic segments (like user_id) are normalized to avoid high cardinality:

```134:164:backend/app/core/metrics.py
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
```

### Prometheus Configuration

Prometheus scrapes metrics every 15 seconds from the backend:

```1:23:monitoring/prometheus/prometheus.yml
# Prometheus configuration for BeamAI Search & Recommendation API
# Scrapes metrics from the FastAPI backend

global:
  scrape_interval: 15s  # Scrape targets every 15 seconds
  evaluation_interval: 15s  # Evaluate rules every 15 seconds
  external_labels:
    cluster: 'beamai-local'
    environment: 'development'

# Scrape configurations
scrape_configs:
  # Scrape the FastAPI backend metrics endpoint
  - job_name: 'beamai-backend'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['backend:8000']
        labels:
          service: 'beamai-backend'
          component: 'api'
```

### Grafana Dashboards

Five dashboards are automatically provisioned for visualization:

1. **Service Health Overview**: Request rate, error rate, latency percentiles, CPU/memory
2. **Search Performance**: Search-specific metrics (rate, latency, zero-results, cache hits)
3. **Recommendation Performance**: Recommendation-specific metrics
4. **Database Health**: Connection pool usage and database metrics
5. **Cache Performance**: Cache hit/miss rates by type

**Example PromQL Queries Used in Dashboards:**

```promql
# Request rate per endpoint
rate(http_requests_total[5m])

# Error rate
rate(http_errors_total[5m])

# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))

# Zero-result rate
rate(search_zero_results_total[5m]) / rate(http_requests_total{endpoint="/search"}[5m])
```

### Metrics Best Practices

1. **Low Cardinality Labels**: Endpoints are normalized to avoid high cardinality
2. **Histogram Buckets**: Configured for meaningful percentile calculations
3. **Resource Metrics**: Updated on-demand (not continuously) to reduce overhead
4. **Error Handling**: Metrics collection failures don't break the application
5. **Standard Naming**: Follows Prometheus naming conventions (`_total`, `_seconds`)

### Integration with Logging

Metrics complement structured logging:
- **Logs**: Detailed context per request (trace_id, query, user_id)
- **Metrics**: Aggregated statistics over time (rate, percentiles, distributions)
- **Correlation**: Use trace_id from logs to correlate with metrics

---

## Search Service

The search service implements **keyword search** using PostgreSQL Full Text Search (FTS) principles.

### Query Normalization

Before searching, queries are normalized:

```17:47:backend/app/services/search/keyword.py
def normalize_query(query: str) -> str:
    """
    Normalize search query.
    
    Steps:
    1. Lowercase
    2. Remove punctuation (keep spaces)
    3. Trim whitespace
    
    Args:
        query: Raw search query
        
    Returns:
        Normalized query string
    """
    if not query:
        return ""
    
    # Lowercase
    normalized = query.lower()
    
    # Remove punctuation but keep spaces and alphanumeric
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Trim whitespace
    normalized = normalized.strip()
    
    return normalized
```

### Keyword Search Algorithm

The search algorithm uses a simple word-matching approach with weighted scoring:

```50:156:backend/app/services/search/keyword.py
def search_keywords(query: str, limit: int = 50) -> List[Tuple[str, float]]:
    """
    Search products using PostgreSQL Full Text Search.
    
    Returns candidates with search_keyword_score.
    According to SEARCH_DESIGN.md: Search returns candidate product IDs only.
    Ranking is handled downstream.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of tuples (product_id, search_keyword_score)
        Results are sorted by score descending
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return []
    
    # Normalize query
    normalized_query = normalize_query(query)
    
    if not normalized_query:
        logger.warning("Empty query after normalization")
        return []
    
    try:
        # Convert query to tsquery format for Postgres FTS
        # Use plainto_tsquery for better user experience (handles multiple words)
        # This creates a query like: 'running' & 'shoes'
        
        # Build the FTS query using Postgres functions
        # We'll use the search_vector column with ts_rank for scoring
        
        # For Supabase, we need to use RPC or raw SQL for FTS queries
        # Since Supabase client doesn't directly support FTS, we'll query products
        # and filter/rank in Python for Phase 1, or use a simpler approach
        
        # Alternative: Use Supabase's text search if available, or query all and filter
        # For now, let's use a Postgres function approach via RPC
        
        # Simple approach: Query products and use Python to compute scores
        # This is not ideal for large datasets but works for Phase 1
        
        # Better approach: Use raw SQL via Supabase's postgrest client
        # We'll construct a query that uses ts_rank
        
        # Build tsquery from normalized query
        # Split into words and join with &
        words = normalized_query.split()
        tsquery = ' & '.join(words)
        
        # Use Supabase's RPC to call a Postgres function, or use direct query
        # For Phase 1, let's query products and compute scores in Python
        # In production, this should use a Postgres function
        
        # Query products with search_vector
        response = client.table("products").select("id, name, description, category, search_vector").execute()
        
        if not response.data:
            return []
        
        results = []
        
        # Compute FTS scores in Python (for Phase 1)
        # In production, this should be done in Postgres
        import re
        
        query_words = set(words)
        
        for product in response.data:
            product_id = product["id"]
            name = product.get("name", "").lower()
            description = product.get("description", "").lower()
            category = product.get("category", "").lower()
            
            # Simple scoring: count word matches
            # Weight: name (3x), description (2x), category (1x)
            score = 0.0
            
            for word in query_words:
                if word in name:
                    score += 3.0
                if word in description:
                    score += 2.0
                if word in category:
                    score += 1.0
            
            if score > 0:
                # Normalize score (simple normalization)
                normalized_score = min(score / (len(query_words) * 3.0), 1.0)
                results.append((product_id, normalized_score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        results = results[:limit]
        
        logger.info(f"Keyword search for '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in keyword search: {e}", exc_info=True)
        return []
```

**Scoring Algorithm:**
- **Name matches**: 3 points per word
- **Description matches**: 2 points per word
- **Category matches**: 1 point per word
- **Normalization**: Score divided by `(number_of_query_words * 3.0)` to get a value between 0 and 1

### Search Endpoint

The search endpoint orchestrates the search and ranking:

```26:79:backend/app/routes/search.py
@router.get("", response_model=List[SearchResult])
async def search(
    q: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Optional user ID for personalization"),
    k: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """
    Search for products using keyword search with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    try:
        # Get candidates from search service
        candidates = search_keywords(q.strip(), limit=k * 2)
        
        if not candidates:
            return []
        
        # Apply ranking
        try:
            ranked = rank_products(candidates, is_search=True, user_id=user_id)
            
            # Format results
            results = [
                SearchResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (search: {breakdown['search_score']:.3f}, popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
        except Exception as ranking_error:
            logger.warning(f"Ranking failed, falling back to popularity sort: {ranking_error}")
            # Fallback: sort by search_score
            candidates.sort(key=lambda x: x[1], reverse=True)
            results = [
                SearchResult(
                    product_id=product_id,
                    score=score,
                    reason=f"Keyword match score: {score:.3f} (ranking unavailable)"
                )
                for product_id, score in candidates[:k]
            ]
        
        logger.info(f"Search query '{q}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during search")
```

---

## Recommendation Service

The recommendation service provides **popularity-based recommendations** as the baseline model.

### Popularity Recommendation Algorithm

```15:68:backend/app/services/recommendation/popularity.py
def get_popularity_recommendations(
    user_id: Optional[str] = None,
    limit: int = 10,
    category: Optional[str] = None
) -> List[str]:
    """
    Get product recommendations based on global popularity.
    
    Returns candidate product IDs ordered by popularity_score.
    According to RECOMMENDATION_DESIGN.md: Returns candidates only.
    Ranking is handled downstream.
    
    Args:
        user_id: Optional user ID (for future personalization)
        limit: Maximum number of recommendations
        category: Optional category filter
        
    Returns:
        List of product IDs ordered by popularity_score (descending)
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return []
    
    try:
        # Build query
        query = client.table("products").select("id, popularity_score")
        
        # Filter by category if provided
        if category:
            query = query.eq("category", category)
        
        # Order by popularity_score descending
        query = query.order("popularity_score", desc=True)
        
        # Limit results
        query = query.limit(limit * 2)  # Get more candidates for ranking later
        
        response = query.execute()
        
        if not response.data:
            logger.warning("No products found for recommendations")
            return []
        
        # Extract product IDs
        product_ids = [product["id"] for product in response.data]
        
        logger.info(f"Popularity recommendations returned {len(product_ids)} candidates")
        return product_ids
        
    except Exception as e:
        logger.error(f"Error getting popularity recommendations: {e}", exc_info=True)
        return []
```

**Algorithm:**
1. Query products ordered by `popularity_score` descending
2. Optionally filter by category
3. Return top `limit * 2` candidates (more candidates for ranking later)
4. Ranking service will re-rank these candidates

### Recommendation Endpoint

```27:95:backend/app/routes/recommend.py
@router.get("/{user_id}", response_model=List[RecommendResult])
async def recommend(
    user_id: str = Path(..., description="User ID"),
    k: int = Query(10, ge=1, le=100, description="Number of recommendations to return")
):
    """
    Get product recommendations for a user with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    try:
        # Verify user exists
        client = get_supabase_client()
        if client:
            user_check = client.table("users").select("id").eq("id", user_id).limit(1).execute()
            if not user_check.data:
                logger.warning(f"User {user_id} not found, but continuing with recommendations")
        
        # Get candidates from recommendation service
        candidate_ids = get_popularity_recommendations(user_id=user_id, limit=k * 2)
        
        if not candidate_ids:
            logger.warning(f"No recommendations found for user {user_id}")
            return []
        
        # Convert to candidates format (product_id, search_score=0 for recommendations)
        candidates = [(product_id, 0.0) for product_id in candidate_ids]
        
        # Apply ranking (is_search=False for recommendations)
        try:
            ranked = rank_products(candidates, is_search=False, user_id=user_id)
            
            # Format results
            results = [
                RecommendResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
        except Exception as ranking_error:
            logger.warning(f"Ranking failed, falling back to popularity sort: {ranking_error}")
            # Fallback: use popularity scores
            if client:
                products = client.table("products").select("id, popularity_score").in_("id", candidate_ids).execute()
                score_map = {p["id"]: p.get("popularity_score", 0.0) or 0.0 for p in products.data}
            else:
                score_map = {}
            
            # Sort by popularity
            sorted_candidates = sorted(candidate_ids, key=lambda pid: score_map.get(pid, 0.0), reverse=True)
            
            results = [
                RecommendResult(
                    product_id=product_id,
                    score=score_map.get(product_id, 0.0),
                    reason=f"Popularity score: {score_map.get(product_id, 0.0):.3f} (ranking unavailable)"
                )
                for product_id in sorted_candidates[:k]
            ]
        
        logger.info(f"Recommendations for user {user_id} returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in recommend endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during recommendation")
```

---

## Ranking Service

The ranking service implements the **Phase 1 ranking formula** with deterministic scoring.

### Phase 1 Ranking Formula

According to `RANKING_LOGIC.md`, the Phase 1 formula is:

```python
final_score = (
    0.4 * search_score +
    0.3 * cf_score +
    0.2 * popularity_score +
    0.1 * freshness_score
)
```

### Score Computation

```31:56:backend/app/services/ranking/score.py
def compute_final_score(
    search_score: float,
    cf_score: float,
    popularity_score: float,
    freshness_score: float
) -> float:
    """
    Compute final ranking score using Phase 1 formula.
    
    Args:
        search_score: Search relevance score (0 for recommendations)
        cf_score: Collaborative filtering score (0 in Phase 1)
        popularity_score: Product popularity score
        freshness_score: Product freshness score
        
    Returns:
        Final ranking score
    """
    final_score = (
        WEIGHTS["search_score"] * search_score +
        WEIGHTS["cf_score"] * cf_score +
        WEIGHTS["popularity_score"] * popularity_score +
        WEIGHTS["freshness_score"] * freshness_score
    )
    
    return final_score
```

**Weights:**
- `search_score`: 0.4 (40%)
- `cf_score`: 0.3 (30%) - Currently 0 in Phase 1
- `popularity_score`: 0.2 (20%)
- `freshness_score`: 0.1 (10%)

### Ranking Algorithm

```59:137:backend/app/services/ranking/score.py
def rank_products(
    candidates: List[Tuple[str, float]],
    is_search: bool = True,
    user_id: Optional[str] = None
) -> List[Tuple[str, float, Dict[str, float]]]:
    """
    Rank products using Phase 1 formula.
    
    Args:
        candidates: List of (product_id, search_keyword_score) tuples
        is_search: True if this is a search query, False if recommendations
        user_id: Optional user ID (for future personalization)
        
    Returns:
        List of (product_id, final_score, breakdown) tuples, sorted by final_score descending
        breakdown contains individual feature scores for explainability
    """
    if not candidates:
        return []
    
    # Extract product IDs and search scores
    product_ids = [product_id for product_id, _ in candidates]
    search_scores = {product_id: score for product_id, score in candidates}
    
    # Get product features
    features = get_product_features(product_ids)
    
    if not features:
        logger.warning("No features retrieved, returning candidates as-is")
        # Fallback: return candidates sorted by search_score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [
            (product_id, score, {"search_score": score, "cf_score": 0.0, "popularity_score": 0.0, "freshness_score": 0.0})
            for product_id, score in candidates
        ]
    
    # Compute final scores
    ranked_results = []
    
    for product_id, search_score in candidates:
        if product_id not in features:
            logger.warning(f"Features not found for product {product_id}, skipping")
            continue
        
        product_features = features[product_id]
        popularity_score = product_features.get("popularity_score", 0.0)
        freshness_score = product_features.get("freshness_score", 0.0)
        
        # For recommendations, search_score is 0
        if not is_search:
            search_score = 0.0
        
        # cf_score is 0 in Phase 1
        cf_score = 0.0
        
        # Compute final score
        final_score = compute_final_score(
            search_score=search_score,
            cf_score=cf_score,
            popularity_score=popularity_score,
            freshness_score=freshness_score
        )
        
        # Create breakdown for explainability
        breakdown = {
            "search_score": search_score,
            "cf_score": cf_score,
            "popularity_score": popularity_score,
            "freshness_score": freshness_score
        }
        
        ranked_results.append((product_id, final_score, breakdown))
    
    # Sort by final_score descending
    ranked_results.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Ranked {len(ranked_results)} products")
    return ranked_results
```

**Algorithm Steps:**
1. Extract product IDs from candidates
2. Fetch features (popularity_score, freshness_score) for all products
3. For each candidate:
   - Set `search_score` to 0 for recommendations
   - Set `cf_score` to 0 (Phase 1)
   - Compute final score using weighted formula
   - Create breakdown for explainability
4. Sort by final_score descending
5. Return ranked results with breakdowns

---

## Feature Computation

Features are computed **offline** and stored in the database. The ranking service only reads features.

### Popularity Score Algorithm

Popularity scores are computed from weighted event counts:

```22:63:backend/app/services/features/popularity.py
def compute_popularity_scores() -> Dict[str, float]:
    """
    Compute popularity scores for all products based on weighted event counts.
    
    Returns:
        Dictionary mapping product_id to popularity_score
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return {}
    
    try:
        # Get all events grouped by product_id and event_type
        events_response = client.table("events").select("product_id, event_type").execute()
        
        if not events_response.data:
            logger.warning("No events found in database")
            return {}
        
        # Aggregate scores by product
        product_scores: Dict[str, float] = {}
        
        for event in events_response.data:
            product_id = event["product_id"]
            event_type = event["event_type"]
            weight = EVENT_WEIGHTS.get(event_type, 0.0)
            
            if product_id not in product_scores:
                product_scores[product_id] = 0.0
            
            product_scores[product_id] += weight
        
        # Normalize scores (optional: can be adjusted based on business needs)
        # For now, we'll use raw weighted counts
        
        logger.info(f"Computed popularity scores for {len(product_scores)} products")
        return product_scores
        
    except Exception as e:
        logger.error(f"Error computing popularity scores: {e}", exc_info=True)
        return {}
```

**Event Weights:**
- `purchase`: 3.0
- `add_to_cart`: 2.0
- `view`: 1.0

**Algorithm:**
1. Fetch all events from database
2. For each event, add weight to product's score
3. Return aggregated scores (raw weighted counts, not normalized)

### Freshness Score Algorithm

Freshness scores use **exponential decay** based on product creation date:

```21:61:backend/app/services/features/freshness.py
def compute_freshness_score(created_at: datetime, reference_time: Optional[datetime] = None) -> float:
    """
    Compute freshness score using exponential decay.
    
    Formula: score = exp(-ln(2) * days_old / half_life)
    - New products (0 days old): score = 1.0
    - Products at half-life: score = 0.5
    - Older products: score approaches 0
    
    Args:
        created_at: When the product was created
        reference_time: Reference time for calculation (defaults to now)
        
    Returns:
        Freshness score between 0.0 and 1.0
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    
    # Ensure both datetimes are timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    
    # Calculate days since creation
    delta = reference_time - created_at
    days_old = delta.total_seconds() / (24 * 3600)
    
    # Handle negative days (future dates) or very old products
    if days_old < 0:
        days_old = 0
    elif days_old > FRESHNESS_HALF_LIFE_DAYS * 5:  # Very old products
        return 0.0
    
    # Exponential decay formula
    # Using numpy for numerical stability
    score = np.exp(-np.log(2) * days_old / FRESHNESS_HALF_LIFE_DAYS)
    
    # Clamp to [0, 1]
    return float(np.clip(score, 0.0, 1.0))
```

**Formula:**
```
score = exp(-ln(2) * days_old / half_life)
```

**Parameters:**
- `half_life`: 90 days (products lose half their freshness after 90 days)
- New products (0 days): score = 1.0
- Products at half-life (90 days): score = 0.5
- Very old products (>450 days): score = 0.0

### Feature Retrieval

Features are retrieved on-demand during ranking:

```17:64:backend/app/services/ranking/features.py
def get_product_features(product_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get features for a list of products.
    
    Returns:
        Dictionary mapping product_id to feature dict:
        {
            "popularity_score": float,
            "freshness_score": float
        }
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return {}
    
    try:
        # Fetch products with popularity_score and created_at
        response = client.table("products").select(
            "id, popularity_score, created_at"
        ).in_("id", product_ids).execute()
        
        if not response.data:
            return {}
        
        features = {}
        
        for product in response.data:
            product_id = product["id"]
            popularity_score = product.get("popularity_score", 0.0) or 0.0
            created_at = product.get("created_at")
            
            # Compute freshness score
            freshness_score = 0.0
            if created_at:
                freshness_score = compute_freshness_score_from_string(created_at)
            
            features[product_id] = {
                "popularity_score": float(popularity_score),
                "freshness_score": freshness_score
            }
        
        logger.debug(f"Retrieved features for {len(features)} products")
        return features
        
    except Exception as e:
        logger.error(f"Error retrieving product features: {e}", exc_info=True)
        return {}
```

**Note:** `popularity_score` is stored in the database (computed offline), while `freshness_score` is computed on-demand from `created_at`.

---

## Event Tracking

Events are **append-only** and track user interactions for analytics and feature computation.

### Event Types

- `view`: User viewed a product
- `add_to_cart`: User added product to cart
- `purchase`: User purchased product

### Event Tracking Endpoint

```27:84:backend/app/routes/events.py
@router.post("")
async def track_event(event: EventRequest):
    """
    Track a user interaction event.
    
    Events are append-only and used for:
    - Computing popularity scores
    - Training collaborative filtering models
    - Analytics
    """
    # Validate event_type
    valid_event_types = ["view", "add_to_cart", "purchase"]
    if event.event_type not in valid_event_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    # Validate source if provided
    if event.source:
        valid_sources = ["search", "recommendation", "direct"]
        if event.source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
            )
    
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Insert event
        event_data = {
            "user_id": event.user_id,
            "product_id": event.product_id,
            "event_type": event.event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "source": event.source
        }
        
        response = client.table("events").insert(event_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to insert event")
        
        logger.info(f"Tracked event: {event.event_type} for user {event.user_id}, product {event.product_id}")
        
        return {
            "success": True,
            "event_id": response.data[0].get("id") if response.data else None
        }
        
    except Exception as e:
        logger.error(f"Error tracking event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during event tracking")
```

**Event Data Structure:**
- `user_id`: User identifier
- `product_id`: Product identifier
- `event_type`: One of `view`, `add_to_cart`, `purchase`
- `timestamp`: UTC timestamp
- `source`: Optional source (`search`, `recommendation`, `direct`)

---

## Request Flow

### Search Request Flow

1. **User sends search query** → `GET /search?q={query}&k={limit}`
2. **FastAPI Gateway** validates request
3. **Search Service** normalizes query and retrieves candidates with `search_keyword_score`
4. **Ranking Service** fetches features (popularity_score, freshness_score) and computes final scores
5. **Results returned** with scores and breakdowns

**Example Flow:**
```
User Query: "running shoes"
↓
Normalize: "running shoes"
↓
Search Service: Returns [(product_id, search_score), ...]
↓
Ranking Service: 
  - Fetch features for products
  - Compute: final_score = 0.4*search_score + 0.2*popularity + 0.1*freshness
  - Sort by final_score
↓
Return top k results
```

### Recommendation Request Flow

1. **User requests recommendations** → `GET /recommend/{user_id}?k={limit}`
2. **FastAPI Gateway** validates request
3. **Recommendation Service** retrieves top products by `popularity_score`
4. **Ranking Service** fetches features and computes final scores (search_score=0 for recommendations)
5. **Results returned** with scores and breakdowns

**Example Flow:**
```
User ID: "user_123"
↓
Recommendation Service: Returns top products by popularity_score
↓
Ranking Service:
  - Fetch features for products
  - Compute: final_score = 0.2*popularity + 0.1*freshness (search_score=0)
  - Sort by final_score
↓
Return top k results
```

### Graceful Degradation

The system includes fallback mechanisms:

1. **Ranking Service Failure**: Falls back to sorting by `search_score` (search) or `popularity_score` (recommendations)
2. **Feature Retrieval Failure**: Returns candidates sorted by search score only
3. **Database Connection Failure**: Returns empty results with error logging

---

## Summary

The BeamAI system implements a **production-grade search and recommendation platform** with:

- **Separation of concerns**: Retrieval, ranking, and serving are independent
- **Deterministic ranking**: Phase 1 formula with explainable scores
- **Offline feature computation**: Popularity scores computed in batch jobs
- **On-demand freshness**: Freshness scores computed from creation dates
- **Graceful degradation**: Fallback mechanisms at every layer
- **Event-driven analytics**: Append-only event tracking for feature computation
- **Comprehensive observability**: Structured JSON logging with trace IDs and Prometheus metrics collection
- **Metrics visualization**: Grafana dashboards for RED metrics, business metrics, and resource monitoring

**Observability Stack:**
- **Logs**: Structured JSON logging with trace ID propagation for request correlation
- **Metrics**: Prometheus metrics (RED metrics, business metrics, resource metrics) exposed at `/metrics`
- **Dashboards**: Five Grafana dashboards for service health, search/recommendation performance, database health, and cache performance

The system is designed to scale from local development to production environments without architectural rewrites.

