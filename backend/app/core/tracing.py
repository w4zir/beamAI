"""
OpenTelemetry distributed tracing configuration.

This module provides distributed tracing using OpenTelemetry, following the
observability specification in /specs/OBSERVABILITY.md.

Features:
- Automatic trace ID generation and propagation
- Span creation for key operations (search, ranking, database, cache)
- Trace export via OTLP (OpenTelemetry Protocol) - recommended
- Legacy Jaeger exporter support (if package is manually installed)
- Integration with structured logging (trace_id in logs)
- Trace context propagation via HTTP headers

Configuration:
- OTEL_SERVICE_NAME: Service name (default: beamai_search_api)
- OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (recommended, e.g., http://localhost:4317 for gRPC or http://localhost:4318 for HTTP)
- OTEL_EXPORTER_JAEGER_ENDPOINT: Jaeger endpoint (deprecated, use OTLP instead)
- OTEL_TRACES_SAMPLER_ARG: Sampling rate (default: 1.0 for 100% sampling)

Note: Jaeger exporter package has been removed from requirements due to dependency conflicts.
Use OTLP exporter instead - Jaeger can receive traces via OTLP endpoint.
"""
import os
from typing import Optional, Dict, Any, Sequence, TYPE_CHECKING
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Span

# Jaeger exporter is deprecated - use OTLP exporter instead
# OTLP can send traces to Jaeger via OTLP endpoint
if TYPE_CHECKING:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter

try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False
    JaegerExporter = None  # type: ignore
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Status, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from .logging import get_logger, get_trace_id, set_trace_id

logger = get_logger(__name__)

# Context variable for OpenTelemetry trace context
trace_context_var: ContextVar[Optional[Dict[str, str]]] = ContextVar("trace_context", default=None)

# Global tracer instance
_tracer: Optional[Tracer] = None
_tracer_provider: Optional[TracerProvider] = None


class ResilientJaegerExporter(SpanExporter):
    """
    Wrapper around JaegerExporter that handles connection errors gracefully.
    
    This prevents connection failures from appearing as exceptions in logs
    when Jaeger is not available. Connection errors are logged as warnings
    but do not interrupt application execution.
    """
    
    def __init__(self, jaeger_exporter: Any):  # type: ignore
        self._exporter = jaeger_exporter
        self._connection_failed = False
    
    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """
        Export spans to Jaeger, handling connection errors gracefully.
        
        Args:
            spans: List of spans to export
            
        Returns:
            SpanExportResult indicating success or failure
        """
        try:
            return self._exporter.export(spans)
        except (ConnectionRefusedError, OSError, Exception) as e:
            # Log connection errors only once to avoid spam
            if not self._connection_failed:
                logger.warning(
                    "tracing_jaeger_export_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    message="Jaeger is not available. Traces will be generated but not exported. Start Jaeger or disable tracing to suppress this message.",
                )
                self._connection_failed = True
            # Return success to prevent retries and exception propagation
            return SpanExportResult.SUCCESS
    
    def shutdown(self) -> None:
        """Shutdown the underlying exporter."""
        try:
            self._exporter.shutdown()
        except Exception as e:
            logger.debug(
                "tracing_jaeger_shutdown_failed",
                error=str(e),
                error_type=type(e).__name__,
            )


def configure_tracing(
    service_name: Optional[str] = None,
    jaeger_endpoint: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    sampling_rate: float = 1.0,
    enable_jaeger: bool = True,
    enable_otlp: bool = False,
) -> None:
    """
    Configure OpenTelemetry tracing.
    
    Args:
        service_name: Service name identifier (defaults to OTEL_SERVICE_NAME or beamai_search_api)
        jaeger_endpoint: Jaeger endpoint URL (defaults to OTEL_EXPORTER_JAEGER_ENDPOINT or http://localhost:14268/api/traces)
        otlp_endpoint: OTLP endpoint URL (defaults to OTEL_EXPORTER_OTLP_ENDPOINT)
        sampling_rate: Sampling rate (0.0 to 1.0, default: 1.0 for 100% sampling)
        enable_jaeger: Enable Jaeger exporter (default: True)
        enable_otlp: Enable OTLP exporter (default: False)
    """
    global _tracer, _tracer_provider
    
    # Get configuration from environment variables or use defaults
    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "beamai_search_api")
    jaeger_endpoint = jaeger_endpoint or os.getenv(
        "OTEL_EXPORTER_JAEGER_ENDPOINT",
        "http://localhost:14268/api/traces"
    )
    otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    sampling_rate = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", str(sampling_rate)))
    
    # Create resource with service name
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
    })
    
    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    
    # Configure sampling
    if sampling_rate < 1.0:
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
        sampler = TraceIdRatioBased(sampling_rate)
        _tracer_provider = TracerProvider(resource=resource, sampler=sampler)
    
    # Add Jaeger exporter if enabled
    # Note: Jaeger exporter package is deprecated and removed from requirements.
    # Use OTLP exporter instead (configure via OTEL_EXPORTER_OTLP_ENDPOINT).
    # Jaeger can receive traces via OTLP endpoint (typically port 4317 for gRPC or 4318 for HTTP).
    if enable_jaeger and jaeger_endpoint:
        if JAEGER_AVAILABLE:
            try:
                # Legacy Jaeger exporter (deprecated, only if package is manually installed)
                # Parse endpoint URL
                # Format: http://host:port/api/traces or http://host:port
                if "://" in jaeger_endpoint:
                    # Extract host and port from URL
                    url_parts = jaeger_endpoint.split("://")[1]
                    if "/" in url_parts:
                        host_port = url_parts.split("/")[0]
                    else:
                        host_port = url_parts
                    
                    if ":" in host_port:
                        host, port_str = host_port.split(":")
                        port = int(port_str)
                    else:
                        host = host_port
                        port = 14268  # Default Jaeger port
                else:
                    host = "localhost"
                    port = 14268
                
                # JaegerExporter uses agent_host_name and agent_port for UDP
                jaeger_exporter = JaegerExporter(
                    agent_host_name=host,
                    agent_port=port,
                )
                # Wrap exporter to handle connection errors gracefully
                resilient_exporter = ResilientJaegerExporter(jaeger_exporter)
                span_processor = BatchSpanProcessor(resilient_exporter)
                _tracer_provider.add_span_processor(span_processor)
                logger.info(
                    "tracing_jaeger_configured",
                    host=host,
                    port=port,
                    sampling_rate=sampling_rate,
                )
            except Exception as e:
                logger.warning(
                    "tracing_jaeger_configuration_failed",
                    endpoint=jaeger_endpoint,
                    error=str(e),
                    error_type=type(e).__name__,
                    message="Tracing will continue without Jaeger export",
                )
        else:
            # Jaeger exporter package not available - recommend using OTLP instead
            logger.warning(
                "tracing_jaeger_exporter_unavailable",
                endpoint=jaeger_endpoint,
                message="Jaeger exporter package is not installed. Use OTLP exporter instead by setting OTEL_EXPORTER_OTLP_ENDPOINT. Jaeger can receive traces via OTLP (port 4317 for gRPC or 4318 for HTTP).",
            )
    
    # Add OTLP exporter if enabled
    if enable_otlp and otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            _tracer_provider.add_span_processor(span_processor)
            logger.info(
                "tracing_otlp_configured",
                endpoint=otlp_endpoint,
                sampling_rate=sampling_rate,
            )
        except Exception as e:
            logger.warning(
                "tracing_otlp_configuration_failed",
                endpoint=otlp_endpoint,
                error=str(e),
                error_type=type(e).__name__,
                message="Tracing will continue without OTLP export",
            )
    
    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)
    
    # Get tracer instance
    _tracer = trace.get_tracer(__name__)
    
    logger.info(
        "tracing_configured",
        service_name=service_name,
        sampling_rate=sampling_rate,
        jaeger_enabled=enable_jaeger,
        otlp_enabled=enable_otlp,
    )


def get_tracer() -> Tracer:
    """
    Get the global tracer instance.
    
    Returns:
        OpenTelemetry Tracer instance
        
    Raises:
        RuntimeError: If tracing is not configured
    """
    global _tracer
    if _tracer is None:
        # Auto-configure if not already configured
        configure_tracing()
        _tracer = trace.get_tracer(__name__)
    return _tracer


def extract_trace_context(headers: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Extract trace context from HTTP headers.
    
    Supports W3C TraceContext format (traceparent header).
    
    Args:
        headers: Dictionary of HTTP headers
        
    Returns:
        Trace context dictionary or None if not present
    """
    propagator = TraceContextTextMapPropagator()
    try:
        context = propagator.extract(headers)
        if context:
            # Convert to dict format
            trace_context = {}
            propagator.inject(trace_context, context)
            return trace_context
    except Exception as e:
        logger.debug(
            "trace_context_extraction_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
    return None


def inject_trace_context(headers: Dict[str, str]) -> None:
    """
    Inject trace context into HTTP headers.
    
    Args:
        headers: Dictionary to add trace context headers to
    """
    propagator = TraceContextTextMapPropagator()
    current_span = trace.get_current_span()
    if current_span and current_span.get_span_context().is_valid:
        context = trace.set_span_in_context(current_span)
        propagator.inject(headers, context)


def get_trace_id_from_context() -> Optional[str]:
    """
    Get trace ID from current OpenTelemetry span context.
    
    Returns:
        Trace ID as hex string or None if no active span
    """
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            return format(span_context.trace_id, "032x")
    return None


def get_span_id_from_context() -> Optional[str]:
    """
    Get span ID from current OpenTelemetry span context.
    
    Returns:
        Span ID as hex string or None if no active span
    """
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            return format(span_context.span_id, "016x")
    return None


def set_span_attribute(key: str, value: Any) -> None:
    """
    Set an attribute on the current span.
    
    Args:
        key: Attribute key
        value: Attribute value (must be JSON-serializable)
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute(key, value)


def set_span_status(status_code: StatusCode, description: Optional[str] = None) -> None:
    """
    Set status on the current span.
    
    Args:
        status_code: Status code (StatusCode.OK, StatusCode.ERROR)
        description: Optional status description
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_status(Status(status_code, description))


def record_exception(exception: Exception) -> None:
    """
    Record an exception on the current span.
    
    Args:
        exception: Exception to record
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.record_exception(exception)
        current_span.set_status(Status(StatusCode.ERROR, str(exception)))


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.
    
    This automatically creates spans for all HTTP requests.
    
    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("tracing_fastapi_instrumented")
    except Exception as e:
        logger.warning(
            "tracing_fastapi_instrumentation_failed",
            error=str(e),
            error_type=type(e).__name__,
            message="Tracing will continue without automatic FastAPI instrumentation",
        )


def shutdown_tracing() -> None:
    """
    Shutdown tracing and flush all spans.
    """
    global _tracer_provider
    if _tracer_provider:
        try:
            _tracer_provider.shutdown()
            logger.info("tracing_shutdown")
        except Exception as e:
            logger.warning(
                "tracing_shutdown_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

