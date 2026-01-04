"""
Unit tests for Prometheus metrics.
"""
import pytest
from prometheus_client import REGISTRY

from app.core.metrics import (
    semantic_search_requests_total,
    semantic_search_latency_seconds,
    semantic_embedding_generation_latency_seconds,
    semantic_faiss_search_latency_seconds,
    semantic_index_memory_bytes,
    semantic_index_total_products,
    semantic_index_available,
    get_metrics,
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


def test_get_metrics():
    """Test get_metrics function returns valid Prometheus format."""
    metrics_text, content_type = get_metrics()
    
    assert isinstance(metrics_text, bytes)
    assert content_type == "text/plain; version=0.0.4; charset=utf-8"
    
    # Check that metrics text contains expected metric names
    metrics_str = metrics_text.decode('utf-8')
    assert 'semantic_search_requests_total' in metrics_str
    assert 'semantic_search_latency_seconds' in metrics_str
    assert 'semantic_index_memory_bytes' in metrics_str

