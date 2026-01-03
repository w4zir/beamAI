"""
Structured logging configuration for the application.

This module provides JSON-structured logging with correlation IDs (trace_id),
following the observability specification in /specs/OBSERVABILITY.md.

All logs include:
- timestamp (ISO 8601 format)
- level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- service (service name identifier)
- trace_id (correlation ID for request tracing)
- user_id (when available)
- request_id (unique per request)
"""
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Any, Dict
import structlog
from structlog.types import Processor

# Context variable for trace ID propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

# Service name - can be overridden via environment variable
SERVICE_NAME = "beamai_search_api"


def add_trace_context(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add trace context (trace_id, request_id, user_id) to log entries.
    
    This processor extracts context variables and adds them to every log entry.
    """
    # Add trace_id if available
    trace_id = trace_id_var.get()
    if trace_id:
        event_dict["trace_id"] = trace_id
    
    # Add request_id if available
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    
    # Add user_id if available
    user_id = user_id_var.get()
    if user_id:
        event_dict["user_id"] = user_id
    
    # Always add service name
    event_dict["service"] = SERVICE_NAME
    
    # Ensure timestamp is in ISO 8601 format
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    return event_dict


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


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        Configured structlog logger bound with context
    """
    return structlog.get_logger(name)


def set_trace_id(trace_id: Optional[str]) -> None:
    """
    Set trace ID in context for current request.
    
    Args:
        trace_id: Trace ID to set (or None to clear)
    """
    trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    """
    Get current trace ID from context.
    
    Returns:
        Current trace ID or None
    """
    return trace_id_var.get()


def set_request_id(request_id: Optional[str]) -> None:
    """
    Set request ID in context for current request.
    
    Args:
        request_id: Request ID to set (or None to clear)
    """
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.
    
    Returns:
        Current request ID or None
    """
    return request_id_var.get()


def set_user_id(user_id: Optional[str]) -> None:
    """
    Set user ID in context for current request.
    
    Args:
        user_id: User ID to set (or None to clear)
    """
    user_id_var.set(user_id)


def get_user_id() -> Optional[str]:
    """
    Get current user ID from context.
    
    Returns:
        Current user ID or None
    """
    return user_id_var.get()


def generate_request_id() -> str:
    """
    Generate a new unique request ID.
    
    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())


def generate_trace_id() -> str:
    """
    Generate a new unique trace ID.
    
    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())

