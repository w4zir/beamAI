"""
Unit tests for FAISS index building script.
"""
import sys
import pytest
import numpy as np
import faiss
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path for script imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.search.semantic import EMBEDDING_DIM


def test_prepare_product_text():
    """Test product text preparation."""
    from scripts.build_faiss_index import prepare_product_text
    
    # Test with all fields
    product = {
        "id": "prod_1",
        "name": "Test Product",
        "description": "A test product description",
        "category": "Electronics",
    }
    text = prepare_product_text(product)
    assert "Test Product" in text
    assert "A test product description" in text
    assert "Electronics" in text
    
    # Test with missing fields
    product = {
        "id": "prod_2",
        "name": "Test Product",
    }
    text = prepare_product_text(product)
    assert "Test Product" in text
    
    # Test with empty fields
    product = {
        "id": "prod_3",
        "name": "",
        "description": "",
        "category": "",
    }
    text = prepare_product_text(product)
    assert text == "product"  # Placeholder for empty products


@patch('scripts.build_faiss_index.SentenceTransformer')
def test_generate_embeddings(mock_model_class):
    """Test embedding generation."""
    from scripts.build_faiss_index import generate_embeddings
    
    # Setup mock model
    mock_model = MagicMock()
    mock_embeddings = np.random.rand(3, EMBEDDING_DIM).astype('float32')
    # Normalize
    norms = np.linalg.norm(mock_embeddings, axis=1, keepdims=True)
    mock_embeddings = mock_embeddings / norms
    mock_model.encode.return_value = mock_embeddings
    mock_model_class.return_value = mock_model
    
    # Test data
    products = [
        {"id": "prod_1", "name": "Product 1", "description": "Description 1"},
        {"id": "prod_2", "name": "Product 2", "description": "Description 2"},
        {"id": "prod_3", "name": "Product 3", "description": "Description 3"},
    ]
    
    embeddings, product_ids = generate_embeddings(products, mock_model)
    
    assert len(embeddings) == 3
    assert len(product_ids) == 3
    assert embeddings.shape == (3, EMBEDDING_DIM)
    assert product_ids == ["prod_1", "prod_2", "prod_3"]


def test_build_faiss_index_small_dataset():
    """Test FAISS index building for small dataset."""
    from scripts.build_faiss_index import build_faiss_index, SMALL_DATASET_THRESHOLD
    
    # Create sample embeddings
    np.random.seed(42)
    embeddings = np.random.rand(100, EMBEDDING_DIM).astype('float32')
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    
    index, index_type = build_faiss_index(embeddings, 100)
    
    assert index is not None
    assert index.ntotal == 100
    assert index_type == "IndexFlatL2"  # Should use Flat for < 10K products


def test_build_faiss_index_large_dataset():
    """Test FAISS index building for large dataset."""
    from scripts.build_faiss_index import build_faiss_index, SMALL_DATASET_THRESHOLD
    
    # Create sample embeddings (simulate large dataset)
    np.random.seed(42)
    embeddings = np.random.rand(SMALL_DATASET_THRESHOLD, EMBEDDING_DIM).astype('float32')
    # Normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    
    index, index_type = build_faiss_index(embeddings, SMALL_DATASET_THRESHOLD)
    
    assert index is not None
    assert index.ntotal == SMALL_DATASET_THRESHOLD
    assert index_type == "IndexIVFFlat"  # Should use IVF for >= 10K products


def test_save_index():
    """Test index saving."""
    from scripts.build_faiss_index import save_index
    
    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = Path(tmpdir) / "test_index.index"
        metadata_path = Path(tmpdir) / "test_metadata.json"
        
        # Create test index
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        test_embeddings = np.random.rand(3, EMBEDDING_DIM).astype('float32')
        index.add(test_embeddings)
        
        product_ids = ["prod_1", "prod_2", "prod_3"]
        
        save_index(
            index=index,
            product_ids=product_ids,
            index_type="IndexFlatL2",
            index_path=index_path,
            metadata_path=metadata_path,
        )
        
        # Verify index file exists
        assert index_path.exists()
        
        # Verify metadata file exists and is valid
        assert metadata_path.exists()
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["total_products"] == 3
        assert metadata["index_type"] == "IndexFlatL2"
        assert metadata["embedding_dim"] == EMBEDDING_DIM
        assert len(metadata["product_id_mapping"]) == 3
        
        # Verify index can be loaded
        loaded_index = faiss.read_index(str(index_path))
        assert loaded_index.ntotal == 3

