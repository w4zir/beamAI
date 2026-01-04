"""
Integration tests for collaborative filtering with ranking service.
"""
import pytest
import json
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.ranking.score import rank_products
from app.services.recommendation.collaborative import (
    CollaborativeFilteringService,
    initialize_collaborative_filtering,
    get_collaborative_filtering_service,
)


@pytest.fixture
def sample_cf_service(tmp_path):
    """Create a sample CF service for testing."""
    model_dir = tmp_path / "models" / "cf"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Create minimal model artifacts
    user_factors = np.random.randn(2, 5).astype(np.float32)
    item_factors = np.random.randn(3, 5).astype(np.float32)
    
    user_factors_path = model_dir / "user_factors.npy"
    item_factors_path = model_dir / "item_factors.npy"
    user_mapping_path = model_dir / "user_id_mapping.json"
    product_mapping_path = model_dir / "product_id_mapping.json"
    metadata_path = model_dir / "model_metadata.json"
    
    np.save(user_factors_path, user_factors)
    np.save(item_factors_path, item_factors)
    
    user_mapping = {"user1": 0, "user2": 1}
    product_mapping = {"product1": 0, "product2": 1, "product3": 2}
    
    with open(user_mapping_path, 'w') as f:
        json.dump(user_mapping, f)
    
    with open(product_mapping_path, 'w') as f:
        json.dump(product_mapping, f)
    
    metadata = {
        "version": "1.0.0",
        "training_date": "2024-01-01T00:00:00Z",
        "model_type": "ImplicitALS",
        "parameters": {"factors": 5, "regularization": 0.1, "iterations": 15, "alpha": 1.0},
        "training_metrics": {"num_users": 2, "num_products": 3, "num_interactions": 5, "sparsity": 0.5},
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    service = CollaborativeFilteringService(
        user_factors_path=user_factors_path,
        item_factors_path=item_factors_path,
        user_mapping_path=user_mapping_path,
        product_mapping_path=product_mapping_path,
        metadata_path=metadata_path,
    )
    
    service.initialize()
    return service


@pytest.fixture
def mock_product_features():
    """Mock product features."""
    return {
        "product1": {"popularity_score": 0.8, "freshness_score": 0.9},
        "product2": {"popularity_score": 0.6, "freshness_score": 0.7},
        "product3": {"popularity_score": 0.5, "freshness_score": 0.6},
    }


@patch('app.services.ranking.features.get_product_features')
def test_ranking_without_cf(mock_get_features, mock_product_features):
    """Test ranking without CF service."""
    # Reset global CF service
    import app.services.recommendation.collaborative as cf_module
    cf_module._cf_service = None
    
    mock_get_features.return_value = mock_product_features
    
    candidates = [("product1", 0.9), ("product2", 0.7), ("product3", 0.5)]
    ranked = rank_products(candidates, is_search=True, user_id=None)
    
    assert len(ranked) == 3
    # Check that cf_score is 0.0 when CF not available
    for product_id, final_score, breakdown in ranked:
        assert breakdown["cf_score"] == 0.0


@patch('app.services.ranking.features.get_product_features')
@patch('app.services.recommendation.collaborative.get_collaborative_filtering_service')
def test_ranking_with_cf(mock_get_cf_service, mock_get_features, sample_cf_service, mock_product_features):
    """Test ranking with CF service."""
    mock_get_cf_service.return_value = sample_cf_service
    mock_get_features.return_value = mock_product_features
    
    candidates = [("product1", 0.9), ("product2", 0.7), ("product3", 0.5)]
    ranked = rank_products(candidates, is_search=True, user_id="user1")
    
    assert len(ranked) == 3
    # Check that cf_score is computed (may be 0.0 for cold start, but should be present)
    for product_id, final_score, breakdown in ranked:
        assert "cf_score" in breakdown
        assert 0.0 <= breakdown["cf_score"] <= 1.0


@patch('app.services.ranking.features.get_product_features')
@patch('app.services.recommendation.collaborative.get_collaborative_filtering_service')
def test_ranking_recommendations_with_cf(mock_get_cf_service, mock_get_features, sample_cf_service, mock_product_features):
    """Test ranking recommendations with CF."""
    mock_get_cf_service.return_value = sample_cf_service
    mock_get_features.return_value = mock_product_features
    
    # For recommendations, search_score should be 0
    candidates = [("product1", 0.0), ("product2", 0.0), ("product3", 0.0)]
    ranked = rank_products(candidates, is_search=False, user_id="user1")
    
    assert len(ranked) == 3
    for product_id, final_score, breakdown in ranked:
        assert breakdown["search_score"] == 0.0
        assert "cf_score" in breakdown


@patch('app.services.ranking.features.get_product_features')
@patch('app.services.recommendation.collaborative.get_collaborative_filtering_service')
@patch('app.services.recommendation.collaborative.get_supabase_client')
def test_ranking_cold_start_user(mock_get_client, mock_get_cf_service, mock_get_features, sample_cf_service, mock_product_features):
    """Test ranking with cold start user."""
    # Mock Supabase to return low interaction count
    mock_client = Mock()
    mock_response = Mock()
    mock_response.count = 2  # Less than MIN_USER_INTERACTIONS (5)
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    mock_get_client.return_value = mock_client
    
    mock_get_cf_service.return_value = sample_cf_service
    mock_get_features.return_value = mock_product_features
    
    candidates = [("product1", 0.9), ("product2", 0.7)]
    ranked = rank_products(candidates, is_search=True, user_id="new_user")
    
    assert len(ranked) == 2
    # CF scores should be 0.0 for cold start user
    for product_id, final_score, breakdown in ranked:
        assert breakdown["cf_score"] == 0.0


@patch('app.services.ranking.features.get_product_features')
@patch('app.services.recommendation.collaborative.get_collaborative_filtering_service')
def test_ranking_cf_computation_error(mock_get_cf_service, mock_get_features, mock_product_features):
    """Test ranking when CF computation fails."""
    # Mock CF service that raises error
    mock_cf_service = Mock()
    mock_cf_service.is_available.return_value = True
    mock_cf_service.compute_user_product_affinities.side_effect = Exception("CF computation failed")
    mock_get_cf_service.return_value = mock_cf_service
    
    mock_get_features.return_value = mock_product_features
    
    candidates = [("product1", 0.9), ("product2", 0.7)]
    ranked = rank_products(candidates, is_search=True, user_id="user1")
    
    # Should still return results with cf_score=0.0
    assert len(ranked) == 2
    for product_id, final_score, breakdown in ranked:
        assert breakdown["cf_score"] == 0.0

