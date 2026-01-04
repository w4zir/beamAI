"""
Unit tests for semantic search service.
"""
import pytest
import numpy as np
import faiss
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.search.semantic import SemanticSearchService, MODEL_NAME, EMBEDDING_DIM


@pytest.fixture
def temp_index_dir():
    """Create temporary directory for test index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    # Create 3 sample embeddings (3 products)
    np.random.seed(42)
    embeddings = np.random.rand(3, EMBEDDING_DIM).astype('float32')
    # Normalize for cosine similarity
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
def semantic_service(temp_index_dir):
    """Create semantic search service with temp paths."""
    index_path = temp_index_dir / "test_index.index"
    metadata_path = temp_index_dir / "test_metadata.json"
    return SemanticSearchService(index_path=str(index_path), metadata_path=str(metadata_path))


def test_semantic_service_initialization(semantic_service):
    """Test semantic service initialization."""
    assert semantic_service.model is None
    assert semantic_service.index is None
    assert semantic_service.metadata is None
    assert not semantic_service.is_available()


def test_load_model_success(semantic_service):
    """Test successful model loading."""
    success = semantic_service.load_model()
    assert success
    assert semantic_service.model is not None
    assert semantic_service.model.get_sentence_embedding_dimension() == EMBEDDING_DIM


def test_load_model_failure(semantic_service):
    """Test model loading failure handling."""
    with patch('app.services.search.semantic.SentenceTransformer', side_effect=Exception("Model load failed")):
        success = semantic_service.load_model()
        assert not success
        assert semantic_service.model is None


def test_load_index_not_found(semantic_service):
    """Test index loading when file doesn't exist."""
    success = semantic_service.load_index()
    assert not success
    assert semantic_service.index is None


def test_load_index_success(semantic_service, mock_faiss_index, sample_product_ids, temp_index_dir):
    """Test successful index loading."""
    # Save index
    index_path = semantic_service.index_path
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
    with open(semantic_service.metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    # Load model first
    semantic_service.load_model()
    
    # Load index
    success = semantic_service.load_index()
    assert success
    assert semantic_service.index is not None
    assert semantic_service.index.ntotal == len(sample_product_ids)
    assert semantic_service.metadata is not None
    assert len(semantic_service.product_id_mapping) == len(sample_product_ids)


def test_load_index_dimension_mismatch(semantic_service, temp_index_dir):
    """Test index loading with dimension mismatch."""
    # Create index with wrong dimension
    wrong_index = faiss.IndexFlatL2(128)  # Wrong dimension
    faiss.write_index(wrong_index, str(semantic_service.index_path))
    
    # Save metadata with wrong dimension
    metadata = {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,  # Says 384 but index is 128
        "index_type": "IndexFlatL2",
        "total_products": 0,
        "product_id_mapping": {},
    }
    with open(semantic_service.metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    semantic_service.load_model()
    success = semantic_service.load_index()
    assert not success
    assert semantic_service.index is None


def test_generate_embedding_success(semantic_service):
    """Test successful embedding generation."""
    semantic_service.load_model()
    embedding = semantic_service.generate_embedding("test query")
    
    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (EMBEDDING_DIM,)


def test_generate_embedding_empty_text(semantic_service):
    """Test embedding generation with empty text."""
    semantic_service.load_model()
    embedding = semantic_service.generate_embedding("")
    assert embedding is None


def test_generate_embedding_no_model(semantic_service):
    """Test embedding generation without model."""
    embedding = semantic_service.generate_embedding("test query")
    assert embedding is None


def test_search_not_available(semantic_service):
    """Test search when service is not available."""
    results = semantic_service.search("test query")
    assert results == []


def test_search_empty_query(semantic_service, mock_faiss_index, sample_product_ids, temp_index_dir):
    """Test search with empty query."""
    # Setup service
    faiss.write_index(mock_faiss_index, str(semantic_service.index_path))
    metadata = {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "index_type": "IndexFlatL2",
        "total_products": len(sample_product_ids),
        "product_id_mapping": {str(i): pid for i, pid in enumerate(sample_product_ids)},
    }
    with open(semantic_service.metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    semantic_service.load_model()
    semantic_service.load_index()
    
    results = semantic_service.search("")
    assert results == []


def test_search_success(semantic_service, mock_faiss_index, sample_product_ids, temp_index_dir):
    """Test successful search."""
    # Setup service
    faiss.write_index(mock_faiss_index, str(semantic_service.index_path))
    metadata = {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "index_type": "IndexFlatL2",
        "total_products": len(sample_product_ids),
        "product_id_mapping": {str(i): pid for i, pid in enumerate(sample_product_ids)},
    }
    with open(semantic_service.metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    semantic_service.load_model()
    semantic_service.load_index()
    
    # Search
    results = semantic_service.search("test query", top_k=2)
    
    assert len(results) <= 2
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
    assert all(isinstance(r[0], str) and isinstance(r[1], float) for r in results)
    assert all(0.0 <= r[1] <= 1.0 for r in results)  # Scores should be in [0, 1]


def test_initialize_success(semantic_service, mock_faiss_index, sample_product_ids, temp_index_dir):
    """Test successful service initialization."""
    # Setup index files
    faiss.write_index(mock_faiss_index, str(semantic_service.index_path))
    metadata = {
        "version": "1.0.0",
        "build_date": "2024-01-01T00:00:00Z",
        "model_name": MODEL_NAME,
        "embedding_dim": EMBEDDING_DIM,
        "index_type": "IndexFlatL2",
        "total_products": len(sample_product_ids),
        "product_id_mapping": {str(i): pid for i, pid in enumerate(sample_product_ids)},
    }
    with open(semantic_service.metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    success = semantic_service.initialize()
    assert success
    assert semantic_service.is_available()


def test_initialize_model_failure(semantic_service):
    """Test initialization when model loading fails."""
    with patch('app.services.search.semantic.SentenceTransformer', side_effect=Exception("Model load failed")):
        success = semantic_service.initialize()
        assert not success
        assert not semantic_service.is_available()


def test_initialize_index_failure(semantic_service):
    """Test initialization when index loading fails."""
    semantic_service.load_model()
    success = semantic_service.initialize()
    # Model loaded but index not found
    assert not success
    assert not semantic_service.is_available()

