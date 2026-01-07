import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.logging import configure_logging, get_logger, get_trace_id
from .core.middleware import TraceIDMiddleware
from .core.metrics import record_http_request
from .core.rate_limit import initialize_rate_limit_middleware
from .core.tracing import (
    configure_tracing,
    instrument_fastapi,
    shutdown_tracing,
    get_trace_id_from_context,
    record_exception,
    set_span_status,
    StatusCode,
)
from .routes import health, search, recommend, events, metrics, admin
from .services.search.semantic import initialize_semantic_search
from .services.recommendation.collaborative import initialize_collaborative_filtering
from .core.cache import initialize_redis, close_redis
from .core.database_pool import initialize_database_pool, close_database_pools

# Configure structured logging
# Use JSON output in production (containerized), console output in development
log_level = os.getenv("LOG_LEVEL", "INFO")
json_output = os.getenv("LOG_JSON", "true").lower() == "true"
configure_logging(log_level=log_level, json_output=json_output)

logger = get_logger(__name__)

# Configure distributed tracing
# Enable Jaeger by default, can be disabled via OTEL_EXPORTER_JAEGER_ENDPOINT=""
enable_jaeger = os.getenv("OTEL_EXPORTER_JAEGER_ENDPOINT", "").lower() != "disabled"
enable_otlp = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").lower() != ""
configure_tracing(enable_jaeger=enable_jaeger, enable_otlp=enable_otlp)

app = FastAPI(
    title="BeamAI Search & Recommendation API",
    description="Unified search and recommendation platform",
    version="1.0.0"
)

# CORS for local dev; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trace ID middleware (must be after CORS middleware)
app.add_middleware(TraceIDMiddleware)

# Add rate limiting middleware (Phase 3.2)
# Initialize after Redis is available (will be set up in startup)
rate_limit_middleware = initialize_rate_limit_middleware(app)

# Instrument FastAPI with OpenTelemetry (creates automatic spans for HTTP requests)
instrument_fastapi(app)


# Startup event: Initialize semantic search
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("app_startup_started")
    
    # Initialize Redis cache (Phase 3.1)
    redis_initialized = await initialize_redis()
    if redis_initialized:
        logger.info("app_startup_redis_ready")
        # Update rate limit middleware with Redis client
        from app.core.rate_limit import get_rate_limit_middleware
        from app.core.cache import get_redis_client
        middleware = get_rate_limit_middleware()
        if middleware:
            middleware.redis_client = get_redis_client()
    else:
        logger.warning(
            "app_startup_redis_unavailable",
            message="Redis cache not available. System will function without caching (degraded performance).",
        )
    
    # Initialize database connection pools (Phase 3.4)
    db_pool_initialized = await initialize_database_pool()
    if db_pool_initialized:
        logger.info("app_startup_database_pool_ready")
    else:
        logger.warning(
            "app_startup_database_pool_unavailable",
            message="Database connection pool not available. System may not function correctly.",
        )
    
    # Initialize semantic search (loads FAISS index if available)
    # This will gracefully fail if index is not available, falling back to keyword-only search
    semantic_initialized = initialize_semantic_search()
    
    if semantic_initialized:
        logger.info("app_startup_semantic_search_ready")
    else:
        logger.info(
            "app_startup_semantic_search_unavailable",
            message="Semantic search not available. Using keyword search only. Run build_faiss_index.py to enable semantic search.",
        )
    
    # Initialize collaborative filtering (loads CF model if available)
    # This will gracefully fail if model is not available, falling back to cf_score=0.0
    cf_initialized = initialize_collaborative_filtering()
    
    if cf_initialized:
        logger.info("app_startup_collaborative_filtering_ready")
    else:
        logger.info(
            "app_startup_collaborative_filtering_unavailable",
            message="Collaborative filtering not available. Using cf_score=0.0. Run train_cf_model.py to enable collaborative filtering.",
        )
    
    logger.info("app_startup_completed")


# Shutdown event: Cleanup tracing
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    logger.info("app_shutdown_started")
    shutdown_tracing()
    await close_redis()  # Close Redis connection pool (Phase 3.1)
    await close_database_pools()  # Close database connection pools (Phase 3.4)
    logger.info("app_shutdown_completed")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    import time
    # Get start time from request state (set by middleware)
    start_time = getattr(request.state, "start_time", time.time())
    duration = time.time() - start_time
    
    # Get trace ID from logging context or OpenTelemetry context
    trace_id = get_trace_id() or get_trace_id_from_context()
    
    # Set span status for HTTP exceptions
    set_span_status(StatusCode.ERROR if exc.status_code >= 500 else StatusCode.OK, exc.detail)
    
    # Record metrics for HTTP exceptions (4xx errors)
    record_http_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=exc.status_code,
        duration_seconds=duration,
    )
    
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "trace_id": trace_id,
        }
    )
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    return response


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    # Get trace ID from logging context or OpenTelemetry context
    trace_id = get_trace_id() or get_trace_id_from_context()
    
    # Record exception on span
    record_exception(exc)
    set_span_status(StatusCode.ERROR, str(exc))
    
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "trace_id": trace_id,
        }
    )
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    return response


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


