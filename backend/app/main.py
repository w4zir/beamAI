import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.logging import configure_logging, get_logger, get_trace_id
from .core.middleware import TraceIDMiddleware
from .routes import health, search, recommend, events
from .services.search.semantic import initialize_semantic_search

# Configure structured logging
# Use JSON output in production (containerized), console output in development
log_level = os.getenv("LOG_LEVEL", "INFO")
json_output = os.getenv("LOG_JSON", "true").lower() == "true"
configure_logging(log_level=log_level, json_output=json_output)

logger = get_logger(__name__)

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


# Startup event: Initialize semantic search
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("app_startup_started")
    
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
    
    logger.info("app_startup_completed")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    trace_id = get_trace_id()
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    return response


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    trace_id = get_trace_id()
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
        content={"detail": "Internal server error", "status_code": 500}
    )
    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    return response


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])
app.include_router(events.router, prefix="/events", tags=["Events"]) 


