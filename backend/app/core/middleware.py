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
from fastapi import Request, Response
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

