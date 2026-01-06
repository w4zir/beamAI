"""
Middleware for trace ID propagation and request context management.

This middleware:
- Extracts trace ID from HTTP headers (X-Trace-ID or X-Request-ID)
- Generates new trace ID if not present
- Propagates trace ID through all service calls
- Includes trace ID in HTTP response headers
- Generates unique request ID per request
"""
import time
from typing import Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import (
    set_trace_id,
    get_trace_id,
    set_request_id,
    get_request_id,
    set_user_id,
    generate_trace_id,
    generate_request_id,
    get_logger,
)
from .metrics import record_http_request
from .tracing import (
    extract_trace_context,
    get_trace_id_from_context,
    set_span_attribute,
    get_tracer,
)

logger = get_logger(__name__)


class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle trace ID propagation and request context.
    
    Extracts trace ID from headers (X-Trace-ID or X-Request-ID) or generates
    a new one. Sets trace ID and request ID in context for structured logging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add trace ID context.
        
        Integrates with OpenTelemetry tracing:
        - Extracts trace context from headers (W3C TraceContext format)
        - Falls back to X-Trace-ID or X-Request-ID headers
        - Generates new trace ID if not present
        - Sets trace ID in both logging context and OpenTelemetry span
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with trace ID in headers
        """
        # Extract trace context from OpenTelemetry headers (W3C TraceContext)
        headers_dict = dict(request.headers)
        otel_trace_context = extract_trace_context(headers_dict)
        
        # Extract trace ID from headers (check both X-Trace-ID and X-Request-ID)
        # Priority: X-Trace-ID > X-Request-ID > OpenTelemetry context > generate new
        trace_id = (
            request.headers.get("X-Trace-ID") or 
            request.headers.get("X-Request-ID")
        )
        
        # If trace ID provided in headers, use it (preserve user-provided trace ID)
        # Otherwise, try OpenTelemetry context, or generate new
        if not trace_id:
            # Try to get trace ID from OpenTelemetry context (if span already created by FastAPI instrumentation)
            otel_trace_id = get_trace_id_from_context()
            if otel_trace_id:
                # Convert hex format to UUID format for consistency
                if len(otel_trace_id) == 32:
                    trace_id = f"{otel_trace_id[0:8]}-{otel_trace_id[8:12]}-{otel_trace_id[12:16]}-{otel_trace_id[16:20]}-{otel_trace_id[20:32]}"
                else:
                    trace_id = otel_trace_id
            else:
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
        
        # Get tracer and create/update span attributes
        tracer = get_tracer()
        with tracer.start_as_current_span("http.request") as span:
            # Set span attributes
            set_span_attribute("http.method", request.method)
            set_span_attribute("http.url", str(request.url))
            set_span_attribute("http.route", request.url.path)
            if user_id:
                set_span_attribute("user.id", user_id)
            
            # Log request start
            start_time = time.time()
            # Store start time in request state for exception handlers
            request.state.start_time = start_time
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
                
                # Set span attributes for response
                set_span_attribute("http.status_code", response.status_code)
                set_span_attribute("http.response.latency_ms", latency_ms)
                
                # Record metrics
                record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration_seconds=process_time,
                )
                
                # Log request completion
                logger.info(
                    "request_completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                )
                
                # Add trace ID to response headers
                # Use the trace_id we set at the beginning (preserves user-provided trace ID)
                # Convert hex format to UUID format if needed for consistency
                otel_trace_id = get_trace_id_from_context()
                if otel_trace_id and len(otel_trace_id) == 32 and trace_id != otel_trace_id:
                    # If OpenTelemetry generated a different trace ID, convert it to UUID format
                    uuid_trace_id = f"{otel_trace_id[0:8]}-{otel_trace_id[8:12]}-{otel_trace_id[12:16]}-{otel_trace_id[16:20]}-{otel_trace_id[20:32]}"
                    # But prefer the trace_id we set (which preserves user-provided trace ID)
                    response.headers["X-Trace-ID"] = trace_id
                else:
                    # Use the trace_id we set (preserves user-provided trace ID)
                    response.headers["X-Trace-ID"] = trace_id
                response.headers["X-Request-ID"] = request_id
                
                return response
                
            except HTTPException as exc:
                # Set span status for HTTP exceptions
                set_span_attribute("http.status_code", exc.status_code)
                set_span_attribute("error", True)
                set_span_attribute("error.type", "HTTPException")
                # HTTPExceptions (4xx) are handled by FastAPI exception handlers
                # Don't record metrics here - let the exception handler do it
                # Re-raise to let FastAPI handle it
                raise
            except Exception as e:
                # Calculate latency even on error
                process_time = time.time() - start_time
                latency_ms = int(process_time * 1000)
                
                # Set span status for errors
                from .tracing import record_exception, set_span_status, StatusCode
                record_exception(e)
                set_span_status(StatusCode.ERROR, str(e))
                set_span_attribute("http.status_code", 500)
                
                # Record metrics for error (500 status code)
                record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=500,
                    duration_seconds=process_time,
                )
                
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

