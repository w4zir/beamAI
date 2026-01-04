"""
Unit tests for Prometheus metrics collection.

Tests verify:
- Metrics are correctly initialized
- RED metrics (Rate, Errors, Duration) are recorded correctly
- Business metrics (zero-results, cache hits/misses, ranking scores) are recorded correctly
- Resource metrics (CPU, memory) are updated correctly
- Semantic search metrics are recorded correctly
- Metrics endpoint returns valid Prometheus format
- Metrics are correctly incremented/observed
"""
import time
from unittest.mock import patch, MagicMock
import pytest
from prometheus_client import REGISTRY, CollectorRegistry

from app.core.metrics import (
    record_http_request,
    record_search_zero_result,
    record_cache_hit,
    record_cache_miss,
    record_ranking_score,
    update_resource_metrics,
    update_db_pool_metrics,
    get_metrics,
    get_metrics_content_type,
    normalize_endpoint,
    http_requests_total,
    http_errors_total,
    http_request_duration_seconds,
    search_zero_results_total,
    cache_hits_total,
    cache_misses_total,
    ranking_score_distribution,
    system_cpu_usage_percent,
    system_memory_usage_bytes,
    db_connection_pool_size,
    semantic_search_requests_total,
    semantic_search_latency_seconds,
    semantic_embedding_generation_latency_seconds,
    semantic_faiss_search_latency_seconds,
    semantic_index_memory_bytes,
    semantic_index_total_products,
    semantic_index_available,
    registry,
)


def test_semantic_search_requests_counter():
    """Test semantic search requests counter."""
    initial_value = semantic_search_requests_total._value.get()
    semantic_search_requests_total.inc()
    assert semantic_search_requests_total._value.get() == initial_value + 1


def test_semantic_search_latency_histogram():
    """Test semantic search latency histogram."""
    semantic_search_latency_seconds.observe(0.1)
    semantic_search_latency_seconds.observe(0.2)
    semantic_search_latency_seconds.observe(0.3)
    
    # Check that observations were recorded
    samples = list(semantic_search_latency_seconds.collect()[0].samples)
    assert len(samples) > 0


def test_semantic_embedding_generation_latency_histogram():
    """Test embedding generation latency histogram."""
    semantic_embedding_generation_latency_seconds.observe(0.01)
    semantic_embedding_generation_latency_seconds.observe(0.02)
    
    samples = list(semantic_embedding_generation_latency_seconds.collect()[0].samples)
    assert len(samples) > 0


def test_semantic_faiss_search_latency_histogram():
    """Test FAISS search latency histogram."""
    semantic_faiss_search_latency_seconds.observe(0.005)
    semantic_faiss_search_latency_seconds.observe(0.01)
    
    samples = list(semantic_faiss_search_latency_seconds.collect()[0].samples)
    assert len(samples) > 0


def test_semantic_index_memory_gauge():
    """Test semantic index memory gauge."""
    semantic_index_memory_bytes.set(1024 * 1024)  # 1 MB
    assert semantic_index_memory_bytes._value.get() == 1024 * 1024
    
    semantic_index_memory_bytes.set(2048 * 1024)  # 2 MB
    assert semantic_index_memory_bytes._value.get() == 2048 * 1024


def test_semantic_index_total_products_gauge():
    """Test semantic index total products gauge."""
    semantic_index_total_products.set(100)
    assert semantic_index_total_products._value.get() == 100
    
    semantic_index_total_products.set(200)
    assert semantic_index_total_products._value.get() == 200


def test_semantic_index_available_gauge():
    """Test semantic index available gauge."""
    semantic_index_available.set(1)
    assert semantic_index_available._value.get() == 1
    
    semantic_index_available.set(0)
    assert semantic_index_available._value.get() == 0


class TestSemanticSearchMetrics:
    """Test semantic search specific metrics."""
    
    def test_semantic_search_requests_counter(self):
        """Test semantic search requests counter."""
        initial_value = semantic_search_requests_total._value.get()
        semantic_search_requests_total.inc()
        assert semantic_search_requests_total._value.get() == initial_value + 1

    def test_semantic_search_latency_histogram(self):
        """Test semantic search latency histogram."""
        semantic_search_latency_seconds.observe(0.1)
        semantic_search_latency_seconds.observe(0.2)
        semantic_search_latency_seconds.observe(0.3)
        
        # Check that observations were recorded
        samples = list(semantic_search_latency_seconds.collect()[0].samples)
        assert len(samples) > 0

    def test_semantic_embedding_generation_latency_histogram(self):
        """Test embedding generation latency histogram."""
        semantic_embedding_generation_latency_seconds.observe(0.01)
        semantic_embedding_generation_latency_seconds.observe(0.02)
        
        samples = list(semantic_embedding_generation_latency_seconds.collect()[0].samples)
        assert len(samples) > 0

    def test_semantic_faiss_search_latency_histogram(self):
        """Test FAISS search latency histogram."""
        semantic_faiss_search_latency_seconds.observe(0.005)
        semantic_faiss_search_latency_seconds.observe(0.01)
        
        samples = list(semantic_faiss_search_latency_seconds.collect()[0].samples)
        assert len(samples) > 0

    def test_semantic_index_memory_gauge(self):
        """Test semantic index memory gauge."""
        semantic_index_memory_bytes.set(1024 * 1024)  # 1 MB
        assert semantic_index_memory_bytes._value.get() == 1024 * 1024
        
        semantic_index_memory_bytes.set(2048 * 1024)  # 2 MB
        assert semantic_index_memory_bytes._value.get() == 2048 * 1024

    def test_semantic_index_total_products_gauge(self):
        """Test semantic index total products gauge."""
        semantic_index_total_products.set(100)
        assert semantic_index_total_products._value.get() == 100
        
        semantic_index_total_products.set(200)
        assert semantic_index_total_products._value.get() == 200

    def test_semantic_index_available_gauge(self):
        """Test semantic index available gauge."""
        semantic_index_available.set(1)
        assert semantic_index_available._value.get() == 1
        
        semantic_index_available.set(0)
        assert semantic_index_available._value.get() == 0


class TestMetricsInitialization:
    """Test that metrics are properly initialized."""
    
    def test_metrics_registry_exists(self):
        """Test that Prometheus registry exists."""
        assert registry is not None
        assert isinstance(registry, CollectorRegistry)
    
    def test_red_metrics_exist(self):
        """Test that RED metrics are initialized."""
        assert http_requests_total is not None
        assert http_errors_total is not None
        assert http_request_duration_seconds is not None
    
    def test_business_metrics_exist(self):
        """Test that business metrics are initialized."""
        assert search_zero_results_total is not None
        assert cache_hits_total is not None
        assert cache_misses_total is not None
        assert ranking_score_distribution is not None
    
    def test_resource_metrics_exist(self):
        """Test that resource metrics are initialized."""
        assert system_cpu_usage_percent is not None
        assert system_memory_usage_bytes is not None
        assert db_connection_pool_size is not None


class TestEndpointNormalization:
    """Test endpoint path normalization."""
    
    def test_normalize_recommend_endpoint(self):
        """Test that /recommend/{user_id} is normalized."""
        assert normalize_endpoint("/recommend/user123") == "/recommend/{user_id}"
        assert normalize_endpoint("/recommend/abc-def-ghi") == "/recommend/{user_id}"
    
    def test_normalize_search_endpoint(self):
        """Test that /search endpoint is kept as-is."""
        assert normalize_endpoint("/search") == "/search"
        assert normalize_endpoint("/search?q=test") == "/search"
    
    def test_normalize_health_endpoint(self):
        """Test that /health endpoint is kept as-is."""
        assert normalize_endpoint("/health") == "/health"
    
    def test_normalize_metrics_endpoint(self):
        """Test that /metrics endpoint is kept as-is."""
        assert normalize_endpoint("/metrics") == "/metrics"
    
    def test_normalize_other_endpoints(self):
        """Test that other endpoints are kept as-is."""
        assert normalize_endpoint("/events") == "/events"
        assert normalize_endpoint("/unknown/path") == "/unknown/path"


class TestREDMetrics:
    """Test RED metrics (Rate, Errors, Duration)."""
    
    def test_record_http_request_success(self):
        """Test recording successful HTTP request."""
        # Record a successful request
        record_http_request(
            method="GET",
            endpoint="/search",
            status_code=200,
            duration_seconds=0.1,
        )
        
        # Verify request was recorded
        samples = list(http_requests_total.collect()[0].samples)
        assert any(
            s.labels["method"] == "GET"
            and s.labels["endpoint"] == "/search"
            and s.labels["status"] == "200"
            for s in samples
        )
        
        # Verify duration was recorded
        duration_samples = list(http_request_duration_seconds.collect()[0].samples)
        assert any(
            s.labels["method"] == "GET" and s.labels["endpoint"] == "/search"
            for s in duration_samples
        )
    
    def test_record_http_request_4xx_error(self):
        """Test recording 4xx HTTP error."""
        record_http_request(
            method="GET",
            endpoint="/search",
            status_code=400,
            duration_seconds=0.05,
        )
        
        # Verify error was recorded
        samples = list(http_errors_total.collect()[0].samples)
        assert any(
            s.labels["method"] == "GET"
            and s.labels["endpoint"] == "/search"
            and s.labels["status_code"] == "400"
            for s in samples
        )
    
    def test_record_http_request_5xx_error(self):
        """Test recording 5xx HTTP error."""
        record_http_request(
            method="POST",
            endpoint="/events",
            status_code=500,
            duration_seconds=0.2,
        )
        
        # Verify error was recorded
        samples = list(http_errors_total.collect()[0].samples)
        assert any(
            s.labels["method"] == "POST"
            and s.labels["endpoint"] == "/events"
            and s.labels["status_code"] == "500"
            for s in samples
        )
    
    def test_record_http_request_normalizes_endpoint(self):
        """Test that endpoint is normalized when recording."""
        record_http_request(
            method="GET",
            endpoint="/recommend/user123",
            status_code=200,
            duration_seconds=0.1,
        )
        
        # Verify endpoint was normalized
        samples = list(http_requests_total.collect()[0].samples)
        assert any(
            s.labels["endpoint"] == "/recommend/{user_id}" for s in samples
        )


class TestBusinessMetrics:
    """Test business metrics."""
    
    def test_record_search_zero_result(self):
        """Test recording zero-result search."""
        record_search_zero_result(query="test query")
        
        # Verify zero-result was recorded
        samples = list(search_zero_results_total.collect()[0].samples)
        assert any(
            s.labels["query_pattern"] == "test query"[:20].lower() for s in samples
        )
    
    def test_record_search_zero_result_empty_query(self):
        """Test recording zero-result with empty query."""
        record_search_zero_result(query=None)
        
        # Verify zero-result was recorded with "empty" pattern
        samples = list(search_zero_results_total.collect()[0].samples)
        assert any(s.labels["query_pattern"] == "empty" for s in samples)
    
    def test_record_cache_hit(self):
        """Test recording cache hit."""
        record_cache_hit("search")
        record_cache_hit("recommendation")
        
        # Verify cache hits were recorded
        samples = list(cache_hits_total.collect()[0].samples)
        assert any(s.labels["cache_type"] == "search" for s in samples)
        assert any(s.labels["cache_type"] == "recommendation" for s in samples)
    
    def test_record_cache_miss(self):
        """Test recording cache miss."""
        record_cache_miss("search")
        record_cache_miss("features")
        
        # Verify cache misses were recorded
        samples = list(cache_misses_total.collect()[0].samples)
        assert any(s.labels["cache_type"] == "search" for s in samples)
        assert any(s.labels["cache_type"] == "features" for s in samples)
    
    def test_record_ranking_score(self):
        """Test recording ranking score."""
        record_ranking_score(product_id="product123", score=0.75)
        record_ranking_score(product_id="product456", score=0.85)
        
        # Verify ranking scores were recorded
        samples = list(ranking_score_distribution.collect()[0].samples)
        assert any(
            s.labels["product_id"] == "product123" for s in samples
        )
        assert any(
            s.labels["product_id"] == "product456" for s in samples
        )


class TestResourceMetrics:
    """Test resource metrics."""
    
    @patch("app.core.metrics.psutil.cpu_percent")
    @patch("app.core.metrics.psutil.virtual_memory")
    def test_update_resource_metrics(self, mock_memory, mock_cpu):
        """Test updating resource metrics."""
        # Mock CPU and memory values
        mock_cpu.return_value = 45.5
        mock_memory_obj = MagicMock()
        mock_memory_obj.used = 1024 * 1024 * 512  # 512 MB
        mock_memory.return_value = mock_memory_obj
        
        # Update metrics
        update_resource_metrics()
        
        # Verify CPU metric was set
        cpu_value = system_cpu_usage_percent._value.get()
        assert cpu_value == 45.5
        
        # Verify memory metric was set
        memory_value = system_memory_usage_bytes._value.get()
        assert memory_value == 1024 * 1024 * 512
    
    def test_update_db_pool_metrics(self):
        """Test updating database connection pool metrics."""
        update_db_pool_metrics(active=5, idle=10, total=15)
        
        # Verify metrics were set
        active_value = db_connection_pool_size.labels(state="active")._value.get()
        idle_value = db_connection_pool_size.labels(state="idle")._value.get()
        total_value = db_connection_pool_size.labels(state="total")._value.get()
        
        assert active_value == 5
        assert idle_value == 10
        assert total_value == 15
    
    @patch("app.core.metrics.psutil.cpu_percent")
    @patch("app.core.metrics.psutil.virtual_memory")
    def test_update_resource_metrics_handles_errors(self, mock_memory, mock_cpu):
        """Test that resource metrics update handles errors gracefully."""
        # Mock an exception
        mock_cpu.side_effect = Exception("CPU error")
        
        # Should not raise an exception
        update_resource_metrics()


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""
    
    def test_get_metrics_returns_bytes(self):
        """Test that get_metrics returns bytes."""
        metrics_data = get_metrics()
        
        assert isinstance(metrics_data, bytes)
        assert len(metrics_data) > 0
    
    def test_get_metrics_contains_expected_metrics(self):
        """Test that metrics output contains expected metric names."""
        # Record some metrics first
        record_http_request("GET", "/search", 200, 0.1)
        record_search_zero_result("test")
        
        metrics_data = get_metrics().decode("utf-8")
        
        # Should contain our metric names
        assert "http_requests_total" in metrics_data
        assert "http_request_duration_seconds" in metrics_data
        assert "search_zero_results_total" in metrics_data
    
    def test_get_metrics_content_type(self):
        """Test that metrics content type is correct."""
        content_type = get_metrics_content_type()
        
        assert content_type == "text/plain; version=0.0.4; charset=utf-8"
    
    def test_metrics_endpoint_integration(self):
        """Test metrics endpoint via FastAPI test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Make a request to generate some metrics
        client.get("/health")
        
        # Get metrics endpoint
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        # Verify metrics content
        metrics_text = response.text
        assert "http_requests_total" in metrics_text
        assert "# HELP" in metrics_text  # Prometheus format includes help text
        assert "# TYPE" in metrics_text  # Prometheus format includes type declarations


class TestMetricsIntegration:
    """Integration tests for metrics collection."""
    
    def test_metrics_are_incremented_correctly(self):
        """Test that metrics are incremented correctly."""
        # Get initial count
        initial_samples = list(http_requests_total.collect()[0].samples)
        initial_count = sum(
            s.value
            for s in initial_samples
            if s.labels["method"] == "GET"
            and s.labels["endpoint"] == "/search"
            and s.labels["status"] == "200"
        )
        
        # Record multiple requests
        for i in range(5):
            record_http_request("GET", "/search", 200, 0.1)
        
        # Get samples after recording
        samples = list(http_requests_total.collect()[0].samples)
        
        # Find our metric
        final_count = sum(
            s.value
            for s in samples
            if s.labels["method"] == "GET"
            and s.labels["endpoint"] == "/search"
            and s.labels["status"] == "200"
        )
        
        # Verify count increased by 5
        assert final_count == initial_count + 5.0
    
    def test_multiple_endpoints_tracked_separately(self):
        """Test that different endpoints are tracked separately."""
        record_http_request("GET", "/search", 200, 0.1)
        record_http_request("GET", "/recommend/user123", 200, 0.1)
        record_http_request("GET", "/health", 200, 0.1)
        
        # Get samples
        samples = list(http_requests_total.collect()[0].samples)
        
        # Verify all endpoints are tracked
        endpoints = {s.labels["endpoint"] for s in samples if s.labels["method"] == "GET"}
        assert "/search" in endpoints
        assert "/recommend/{user_id}" in endpoints
        assert "/health" in endpoints
    
    def test_error_metrics_separate_from_success(self):
        """Test that error metrics are separate from success metrics."""
        record_http_request("GET", "/search", 200, 0.1)
        record_http_request("GET", "/search", 400, 0.1)
        record_http_request("GET", "/search", 500, 0.1)
        
        # Get samples
        request_samples = list(http_requests_total.collect()[0].samples)
        error_samples = list(http_errors_total.collect()[0].samples)
        
        # Verify requests are counted (all status codes)
        request_count = sum(
            s.value
            for s in request_samples
            if s.labels["method"] == "GET"
            and s.labels["endpoint"] == "/search"
            and s.labels["status"] in ["200", "400", "500"]
        )
        assert request_count >= 3.0  # At least 3 (may be more from other tests)
        
        # Verify errors are counted separately
        error_count = sum(
            s.value
            for s in error_samples
            if s.labels["method"] == "GET"
            and s.labels["endpoint"] == "/search"
        )
        assert error_count >= 2.0  # At least 2 (400 and 500)

