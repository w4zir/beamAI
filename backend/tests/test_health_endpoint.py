"""
Integration tests for health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient
import json
import tempfile
from pathlib import Path
import faiss
import numpy as np

from app.main import app
from app.services.search.semantic import initialize_semantic_search, MODEL_NAME, EMBEDDING_DIM


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for test index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_index(temp_index_dir):
    """Create sample FAISS index for testing."""
    index_path = temp_index_dir / "faiss_index.index"
    metadata_path = temp_index_dir / "index_metadata.json"
    
    # Create sample index
    embeddings = np.random.rand(5, EMBEDDING_DIM).astype('float32')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(embeddings)
    faiss.write_index(index, str(index_path))
    
    # Create metadata
    metadata = {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "index_type": "IndexFlatL2",
        "total_products": 5,
        "product_id_mapping": {str(i): f"prod_{i}" for i in range(5)},
    }
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    return index_path, metadata_path


def test_basic_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "message" in data


def test_semantic_health_check_uninitialized(client):
    """Test semantic health check when service is not initialized."""
    # Reset the global service
    from app.services.search.semantic import _semantic_search_service
    import app.services.search.semantic as semantic_module
    semantic_module._semantic_search_service = None
    
    response = client.get("/health/semantic")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unavailable"
    assert data["available"] is False
    assert data["index_loaded"] is False
    assert data["model_loaded"] is False


def test_semantic_health_check_no_index(client):
    """Test semantic health check when index is not available."""
    # Initialize service without index
    initialize_semantic_search()
    
    response = client.get("/health/semantic")
    assert response.status_code == 200
    data = response.json()
    
    # Service may be initialized but index not loaded
    assert "available" in data
    assert "index_loaded" in data
    assert "model_loaded" in data


def test_semantic_health_check_with_index(client, temp_index_dir, sample_index):
    """Test semantic health check when index is available."""
    index_path, metadata_path = sample_index
    
    # Initialize service with test index
    initialize_semantic_search(
        index_path=str(index_path),
        metadata_path=str(metadata_path)
    )
    
    response = client.get("/health/semantic")
    assert response.status_code == 200
    data = response.json()
    
    if data["available"]:
        assert data["index_loaded"] is True
        assert data["model_loaded"] is True
        assert "total_products" in data
        assert "index_type" in data
        assert "index_version" in data
        assert "build_date" in data
        assert "index_memory_bytes" in data
        assert data["index_memory_bytes"] > 0
        assert data["message"] == "Semantic search is ready"


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST
    
    # Check that metrics text contains expected metrics
    metrics_text = response.text
    assert "semantic_search_requests_total" in metrics_text
    assert "semantic_search_latency_seconds" in metrics_text
    assert "semantic_index_memory_bytes" in metrics_text
    assert "semantic_index_total_products" in metrics_text
    assert "semantic_index_available" in metrics_text


def test_metrics_endpoint_format(client):
    """Test that metrics endpoint returns valid Prometheus format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    
    # Prometheus format should have metric_name{labels} value
    metrics_text = response.text
    lines = metrics_text.split('\n')
    
    # Should have at least some metric lines
    metric_lines = [line for line in lines if line and not line.startswith('#')]
    assert len(metric_lines) > 0
    
    # Check format: metric_name{labels} value or metric_name value
    for line in metric_lines[:10]:  # Check first 10 metric lines
        if '{' in line:
            # Has labels: metric_name{label="value"} value
            assert '}' in line
        else:
            # No labels: metric_name value
            parts = line.split()
            assert len(parts) >= 2  # metric_name and value

