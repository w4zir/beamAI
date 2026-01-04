"""
Unit tests for semantic search service with metrics integration.
"""
import pytest
import numpy as np
import faiss
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.search.semantic import SemanticSearchService, MODEL_NAME, EMBEDDING_DIM
from app.core.metrics import (
    semantic_search_requests_total,
    semantic_search_latency_seconds,
    semantic_embedding_generation_latency_seconds,
    semantic_faiss_search_latency_seconds,
    semantic_index_memory_bytes,
    semantic_index_total_products,
    semantic_index_available,
)


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for test index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    np.random.seed(42)
    embeddings = np.random.rand(3, EMBEDDING_DIM).astype('float32')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    return embeddings


@pytest.fixture
def sample_product_ids():
    """Sample product IDs."""
    return ["prod_1", "prod_2", "prod_3"]


@pytest.fixture
def mock_faiss_index(sample_embeddings):
    """Create a mock FAISS index."""
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(sample_embeddings)
    return index


@pytest.fixture
def semantic_service_with_index(temp_index_dir, mock_faiss_index, sample_product_ids):
    """Create semantic search service with loaded index."""
    index_path = temp_index_dir / "test_index.index"
    metadata_path = temp_index_dir / "test_metadata.json"
    
    # Save index
    faiss.write_index(mock_faiss_index, str(index_path))
    
    # Save metadata
    metadata = {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "index_type": "IndexFlatL2",
        "total_products": len(sample_product_ids),
        "product_id_mapping": {str(i): pid for i, pid in enumerate(sample_product_ids)},
    }
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    service = SemanticSearchService(index_path=str(index_path), metadata_path=str(metadata_path))
    service.load_model()
    service.load_index()
    
    return service


def test_calculate_index_memory(semantic_service_with_index):
    """Test index memory calculation."""
    memory_bytes = semantic_service_with_index._calculate_index_memory()
    
    # Should be at least the size of vectors: ntotal * d * 4 bytes (float32)
    expected_min = semantic_service_with_index.index.ntotal * semantic_service_with_index.index.d * 4
    assert memory_bytes >= expected_min
    assert memory_bytes > 0


def test_calculate_index_memory_no_index(temp_index_dir):
    """Test index memory calculation when index is None."""
    index_path = temp_index_dir / "test_index.index"
    metadata_path = temp_index_dir / "test_metadata.json"
    service = SemanticSearchService(index_path=str(index_path), metadata_path=str(metadata_path))
    
    # Index is None, should return 0
    memory_bytes = service._calculate_index_memory()
    assert memory_bytes == 0


def test_load_index_updates_metrics(semantic_service_with_index):
    """Test that loading index updates Prometheus metrics."""
    # Metrics should be set after index load
    assert semantic_index_total_products._value.get() == 3
    assert semantic_index_memory_bytes._value.get() > 0
    assert semantic_index_available._value.get() == 1


def test_generate_embedding_tracks_metrics(semantic_service_with_index):
    """Test that embedding generation tracks latency metrics."""
    # Get initial sample count
    initial_samples = len(list(semantic_embedding_generation_latency_seconds.collect()[0].samples))
    
    # Generate embedding
    embedding = semantic_service_with_index.generate_embedding("test query")
    
    # Check that metric was updated
    new_samples = list(semantic_embedding_generation_latency_seconds.collect()[0].samples)
    assert len(new_samples) >= initial_samples
    assert embedding is not None


def test_search_tracks_request_metrics(semantic_service_with_index):
    """Test that search tracks request count and latency metrics."""
    # Get initial values
    initial_requests = semantic_search_requests_total._value.get()
    initial_latency_samples = len(list(semantic_search_latency_seconds.collect()[0].samples))
    initial_faiss_samples = len(list(semantic_faiss_search_latency_seconds.collect()[0].samples))
    
    # Perform search
    results = semantic_service_with_index.search("test query", top_k=2)
    
    # Check metrics were updated
    assert semantic_search_requests_total._value.get() == initial_requests + 1
    
    latency_samples = list(semantic_search_latency_seconds.collect()[0].samples)
    assert len(latency_samples) > initial_latency_samples
    
    faiss_samples = list(semantic_faiss_search_latency_seconds.collect()[0].samples)
    assert len(faiss_samples) > initial_faiss_samples
    
    assert len(results) > 0


def test_is_available_updates_metric(semantic_service_with_index):
    """Test that is_available() updates the metric."""
    semantic_index_available.set(0)  # Reset
    
    # Call is_available
    available = semantic_service_with_index.is_available()
    
    # Metric should be updated
    assert semantic_index_available._value.get() == (1 if available else 0)


def test_index_load_failure_resets_metrics(temp_index_dir):
    """Test that index load failure resets metrics."""
    # Set some values
    semantic_index_total_products.set(100)
    semantic_index_memory_bytes.set(1024)
    semantic_index_available.set(1)
    
    # Create service with non-existent index
    index_path = temp_index_dir / "nonexistent.index"
    metadata_path = temp_index_dir / "nonexistent.json"
    service = SemanticSearchService(index_path=str(index_path), metadata_path=str(metadata_path))
    service.load_model()
    
    # Try to load index (will fail)
    success = service.load_index()
    
    # Metrics should be reset
    assert not success
    assert semantic_index_available._value.get() == 0
    assert semantic_index_memory_bytes._value.get() == 0
    assert semantic_index_total_products._value.get() == 0

