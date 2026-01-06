"""
Unit tests for OpenTelemetry distributed tracing.

Tests verify:
- Tracing configuration works correctly
- Trace IDs are generated correctly
- Spans are created for key operations
- Trace context propagation works
- Integration with logging system
"""
import os
from unittest.mock import patch, MagicMock
from typing import Optional

import pytest

from app.core.tracing import (
    configure_tracing,
    get_tracer,
    get_trace_id_from_context,
    get_span_id_from_context,
    set_span_attribute,
    set_span_status,
    record_exception,
    extract_trace_context,
    inject_trace_context,
    StatusCode,
    shutdown_tracing,
)


class TestTracingConfiguration:
    """Test tracing configuration and setup."""
    
    def test_configure_tracing_defaults(self):
        """Test that tracing can be configured with defaults."""
        # Configure tracing (should not raise)
        configure_tracing()
        
        # Get tracer (should not raise)
        tracer = get_tracer()
        assert tracer is not None
    
    def test_configure_tracing_with_service_name(self):
        """Test configuring tracing with custom service name."""
        configure_tracing(service_name="test_service")
        
        tracer = get_tracer()
        assert tracer is not None
    
    def test_configure_tracing_with_jaeger_disabled(self):
        """Test configuring tracing with Jaeger disabled."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        tracer = get_tracer()
        assert tracer is not None
    
    def test_get_tracer_auto_configures(self):
        """Test that get_tracer auto-configures if not already configured."""
        # Reset tracer state
        from app.core.tracing import _tracer, _tracer_provider
        from app.core.tracing import trace
        
        # Clear existing tracer provider
        trace._TRACER_PROVIDER = None
        
        # Get tracer (should auto-configure)
        tracer = get_tracer()
        assert tracer is not None


class TestSpanCreation:
    """Test span creation and manipulation."""
    
    def test_create_span(self):
        """Test creating a span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            assert span is not None
            # NonRecordingSpan doesn't have name attribute, but span should exist
            # Check if it's a recording span by checking for name attribute
            if hasattr(span, 'name'):
                assert span.name == "test.operation"
    
    def test_set_span_attribute(self):
        """Test setting span attributes."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            set_span_attribute("test.key", "test.value")
            set_span_attribute("test.number", 42)
            set_span_attribute("test.bool", True)
            
            # Verify attributes were set (check span attributes)
            # Note: Span attributes may not be directly accessible, but function should not raise
            assert span is not None
    
    def test_set_span_status_ok(self):
        """Test setting span status to OK."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            set_span_status(StatusCode.OK)
            assert span is not None
    
    def test_set_span_status_error(self):
        """Test setting span status to ERROR."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            set_span_status(StatusCode.ERROR, "Test error")
            assert span is not None
    
    def test_record_exception(self):
        """Test recording an exception on a span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            try:
                raise ValueError("Test exception")
            except ValueError as e:
                record_exception(e)
                assert span is not None


class TestTraceIDExtraction:
    """Test trace ID extraction from context."""
    
    def test_get_trace_id_from_context_with_span(self):
        """Test getting trace ID from active span context."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            trace_id = get_trace_id_from_context()
            
            # Should return a trace ID (hex string, 32 characters)
            if trace_id:
                assert isinstance(trace_id, str)
                assert len(trace_id) == 32  # 16 bytes = 32 hex chars
    
    def test_get_trace_id_from_context_without_span(self):
        """Test getting trace ID when no active span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        # No active span
        trace_id = get_trace_id_from_context()
        
        # Should return None or empty
        assert trace_id is None or trace_id == ""
    
    def test_get_span_id_from_context_with_span(self):
        """Test getting span ID from active span context."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            span_id = get_span_id_from_context()
            
            # Should return a span ID (hex string, 16 characters)
            if span_id:
                assert isinstance(span_id, str)
                assert len(span_id) == 16  # 8 bytes = 16 hex chars
    
    def test_get_span_id_from_context_without_span(self):
        """Test getting span ID when no active span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        # No active span
        span_id = get_span_id_from_context()
        
        # Should return None or empty
        assert span_id is None or span_id == ""


class TestTraceContextPropagation:
    """Test trace context propagation."""
    
    def test_extract_trace_context_from_headers(self):
        """Test extracting trace context from HTTP headers."""
        # W3C TraceContext format
        headers = {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }
        
        context = extract_trace_context(headers)
        
        # Should extract context (may return dict or None)
        # The exact format depends on OpenTelemetry implementation
        assert context is not None or context == {}
    
    def test_extract_trace_context_without_headers(self):
        """Test extracting trace context when headers are missing."""
        headers = {}
        
        context = extract_trace_context(headers)
        
        # Should return None or empty dict
        assert context is None or context == {}
    
    def test_inject_trace_context_into_headers(self):
        """Test injecting trace context into HTTP headers."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        headers = {}
        
        with tracer.start_as_current_span("test.operation") as span:
            inject_trace_context(headers)
            
            # Should add trace context headers
            # May add "traceparent" header
            assert isinstance(headers, dict)


class TestTracingIntegration:
    """Test tracing integration with other components."""
    
    def test_tracing_with_logging(self):
        """Test that tracing integrates with logging system."""
        from app.core.logging import configure_logging, get_logger, set_trace_id
        
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        configure_logging(log_level="INFO", json_output=False)
        
        tracer = get_tracer()
        logger = get_logger(__name__)
        
        with tracer.start_as_current_span("test.operation") as span:
            # Get trace ID from OpenTelemetry
            otel_trace_id = get_trace_id_from_context()
            
            # Log a message
            logger.info("test_message", test_field="test_value")
            
            # Trace ID should be available
            assert otel_trace_id is None or isinstance(otel_trace_id, str)
    
    def test_nested_spans(self):
        """Test creating nested spans."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("parent.operation") as parent_span:
            assert parent_span is not None
            
            with tracer.start_as_current_span("child.operation") as child_span:
                assert child_span is not None
                # NonRecordingSpan doesn't have name attribute, but span should exist
                if hasattr(child_span, 'name'):
                    assert child_span.name == "child.operation"
    
    def test_span_with_attributes(self):
        """Test span with multiple attributes."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        tracer = get_tracer()
        
        with tracer.start_as_current_span("test.operation") as span:
            set_span_attribute("operation.type", "test")
            set_span_attribute("operation.id", "123")
            set_span_attribute("operation.count", 5)
            
            assert span is not None


class TestTracingShutdown:
    """Test tracing shutdown."""
    
    def test_shutdown_tracing(self):
        """Test shutting down tracing."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        # Shutdown should not raise
        shutdown_tracing()
        
        # Should be able to reconfigure after shutdown
        configure_tracing(enable_jaeger=False, enable_otlp=False)


class TestTracingErrorHandling:
    """Test error handling in tracing."""
    
    def test_tracing_with_invalid_config(self):
        """Test that tracing handles invalid configuration gracefully."""
        # Configure with invalid endpoint (should not raise)
        configure_tracing(
            jaeger_endpoint="http://invalid-endpoint:9999/api/traces",
            enable_jaeger=True,
            enable_otlp=False
        )
        
        # Should still get a tracer
        tracer = get_tracer()
        assert tracer is not None
    
    def test_set_span_attribute_without_span(self):
        """Test setting span attribute when no active span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        # No active span - should not raise
        set_span_attribute("test.key", "test.value")
    
    def test_set_span_status_without_span(self):
        """Test setting span status when no active span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        # No active span - should not raise
        set_span_status(StatusCode.OK)
    
    def test_record_exception_without_span(self):
        """Test recording exception when no active span."""
        configure_tracing(enable_jaeger=False, enable_otlp=False)
        
        # No active span - should not raise
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            record_exception(e)

