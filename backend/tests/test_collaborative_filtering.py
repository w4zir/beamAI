"""
Unit tests for collaborative filtering service.
"""
import pytest
import json
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.recommendation.collaborative import (
    CollaborativeFilteringService,
    extract_user_product_interactions,
    build_interaction_matrix,
    validate_interaction_matrix,
    get_event_weights,
    get_collaborative_filtering_service,
    initialize_collaborative_filtering,
    DEFAULT_MODEL_DIR,
)


@pytest.fixture
def temp_model_dir(tmp_path):
    """Create temporary model directory."""
    model_dir = tmp_path / "models" / "cf"
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir


@pytest.fixture
def sample_interactions():
    """Sample user-product interactions."""
    return [
        ("user1", "product1", 3.0),
        ("user1", "product2", 2.0),
        ("user2", "product1", 1.0),
        ("user2", "product3", 3.0),
        ("user3", "product2", 2.0),
    ]


@pytest.fixture
def sample_matrix_and_mappings(sample_interactions):
    """Build sample interaction matrix."""
    matrix, user_mapping, product_mapping = build_interaction_matrix(sample_interactions)
    return matrix, user_mapping, product_mapping


@pytest.fixture
def sample_model_artifacts(temp_model_dir, sample_matrix_and_mappings):
    """Create sample model artifacts."""
    matrix, user_mapping, product_mapping = sample_matrix_and_mappings
    
    # Create factor matrices (small for testing)
    num_factors = 5
    num_users = len(user_mapping)
    num_products = len(product_mapping)
    
    user_factors = np.random.randn(num_users, num_factors).astype(np.float32)
    item_factors = np.random.randn(num_products, num_factors).astype(np.float32)
    
    # Save artifacts
    user_factors_path = temp_model_dir / "user_factors.npy"
    item_factors_path = temp_model_dir / "item_factors.npy"
    user_mapping_path = temp_model_dir / "user_id_mapping.json"
    product_mapping_path = temp_model_dir / "product_id_mapping.json"
    metadata_path = temp_model_dir / "model_metadata.json"
    
    np.save(user_factors_path, user_factors)
    np.save(item_factors_path, item_factors)
    
    with open(user_mapping_path, 'w') as f:
        json.dump({k: int(v) for k, v in user_mapping.items()}, f)
    
    with open(product_mapping_path, 'w') as f:
        json.dump({k: int(v) for k, v in product_mapping.items()}, f)
    
    metadata = {
        "version": "1.0.0",
        "training_date": datetime.utcnow().isoformat() + "Z",
        "model_type": "ImplicitALS",
        "parameters": {
            "factors": num_factors,
            "regularization": 0.1,
            "iterations": 15,
            "alpha": 1.0,
        },
        "training_metrics": {
            "num_users": num_users,
            "num_products": num_products,
            "num_interactions": matrix.nnz,
            "sparsity": 0.5,
        },
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f)
    
    return {
        "user_factors": user_factors,
        "item_factors": item_factors,
        "user_mapping": user_mapping,
        "product_mapping": product_mapping,
        "user_factors_path": user_factors_path,
        "item_factors_path": item_factors_path,
        "user_mapping_path": user_mapping_path,
        "product_mapping_path": product_mapping_path,
        "metadata_path": metadata_path,
    }


class TestEventWeights:
    """Test event weight functions."""
    
    def test_get_event_weights(self):
        """Test getting event weights."""
        weights = get_event_weights()
        assert weights["purchase"] == 3.0
        assert weights["add_to_cart"] == 2.0
        assert weights["view"] == 1.0


class TestDataExtraction:
    """Test data extraction functions."""
    
    @patch('app.services.recommendation.collaborative.get_supabase_client')
    def test_extract_user_product_interactions(self, mock_get_client):
        """Test extracting user-product interactions."""
        # Mock Supabase client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            {"user_id": "user1", "product_id": "product1", "event_type": "purchase", "timestamp": "2024-01-01T00:00:00Z"},
            {"user_id": "user1", "product_id": "product2", "event_type": "view", "timestamp": "2024-01-01T00:00:00Z"},
            {"user_id": "user2", "product_id": "product1", "event_type": "add_to_cart", "timestamp": "2024-01-01T00:00:00Z"},
        ]
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        interactions = extract_user_product_interactions(days_back=None, min_interactions=1)
        
        assert len(interactions) == 3
        # Check that weights are applied correctly
        user1_product1 = [x for x in interactions if x[0] == "user1" and x[1] == "product1"][0]
        assert user1_product1[2] == 3.0  # purchase weight
    
    def test_build_interaction_matrix(self, sample_interactions):
        """Test building interaction matrix."""
        matrix, user_mapping, product_mapping = build_interaction_matrix(sample_interactions)
        
        assert matrix.shape[0] == len(user_mapping)
        assert matrix.shape[1] == len(product_mapping)
        assert matrix.nnz == len(sample_interactions)
        assert "user1" in user_mapping
        assert "product1" in product_mapping
    
    def test_validate_interaction_matrix_valid(self, sample_matrix_and_mappings):
        """Test validating valid interaction matrix."""
        matrix, _, _ = sample_matrix_and_mappings
        is_valid, warning = validate_interaction_matrix(matrix, min_users=1, min_products=1, min_interactions=1)
        assert is_valid
        assert warning is None
    
    def test_validate_interaction_matrix_invalid(self):
        """Test validating invalid interaction matrix."""
        from scipy.sparse import csr_matrix
        empty_matrix = csr_matrix((0, 0))
        is_valid, warning = validate_interaction_matrix(empty_matrix, min_users=1, min_products=1, min_interactions=1)
        assert not is_valid


class TestCollaborativeFilteringService:
    """Test CollaborativeFilteringService class."""
    
    def test_service_initialization_missing_files(self, temp_model_dir):
        """Test service initialization with missing files."""
        service = CollaborativeFilteringService(
            user_factors_path=temp_model_dir / "user_factors.npy",
            item_factors_path=temp_model_dir / "item_factors.npy",
            user_mapping_path=temp_model_dir / "user_id_mapping.json",
            product_mapping_path=temp_model_dir / "product_id_mapping.json",
            metadata_path=temp_model_dir / "model_metadata.json",
        )
        
        assert not service.initialize()
        assert not service.is_available()
    
    def test_service_initialization_success(self, sample_model_artifacts):
        """Test successful service initialization."""
        artifacts = sample_model_artifacts
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        assert service.is_available()
        assert len(service.user_id_to_index) > 0
        assert len(service.product_id_to_index) > 0
    
    def test_compute_user_product_affinity_unavailable(self, temp_model_dir):
        """Test computing affinity when service unavailable."""
        service = CollaborativeFilteringService(
            user_factors_path=temp_model_dir / "user_factors.npy",
            item_factors_path=temp_model_dir / "item_factors.npy",
            user_mapping_path=temp_model_dir / "user_id_mapping.json",
            product_mapping_path=temp_model_dir / "product_id_mapping.json",
            metadata_path=temp_model_dir / "model_metadata.json",
        )
        
        score = service.compute_user_product_affinity("user1", "product1")
        assert score == 0.0
    
    def test_compute_user_product_affinity_success(self, sample_model_artifacts):
        """Test computing affinity successfully."""
        artifacts = sample_model_artifacts
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        
        # Get a valid user and product from mappings
        user_id = list(artifacts["user_mapping"].keys())[0]
        product_id = list(artifacts["product_mapping"].keys())[0]
        
        score = service.compute_user_product_affinity(user_id, product_id)
        
        assert 0.0 <= score <= 1.0
    
    def test_compute_user_product_affinities_batch(self, sample_model_artifacts):
        """Test batch computing affinities."""
        artifacts = sample_model_artifacts
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        
        user_id = list(artifacts["user_mapping"].keys())[0]
        product_ids = list(artifacts["product_mapping"].keys())[:2]
        
        scores = service.compute_user_product_affinities(user_id, product_ids)
        
        assert len(scores) == len(product_ids)
        for product_id in product_ids:
            assert product_id in scores
            assert 0.0 <= scores[product_id] <= 1.0
    
    @patch('app.services.recommendation.collaborative.get_supabase_client')
    def test_cold_start_user(self, mock_get_client, sample_model_artifacts):
        """Test cold start handling for new users."""
        artifacts = sample_model_artifacts
        
        # Mock Supabase client to return low interaction count
        mock_client = Mock()
        mock_response = Mock()
        mock_response.count = 2  # Less than MIN_USER_INTERACTIONS (5)
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        
        # New user with few interactions
        score = service.compute_user_product_affinity("new_user", "product1")
        assert score == 0.0
    
    def test_cold_start_product(self, sample_model_artifacts):
        """Test cold start handling for new products."""
        artifacts = sample_model_artifacts
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        
        user_id = list(artifacts["user_mapping"].keys())[0]
        
        # New product not in training
        score = service.compute_user_product_affinity(user_id, "new_product")
        assert score == 0.0
    
    def test_get_user_factors(self, sample_model_artifacts):
        """Test getting user factors."""
        artifacts = sample_model_artifacts
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        
        user_id = list(artifacts["user_mapping"].keys())[0]
        factors = service.get_user_factors(user_id)
        
        assert factors is not None
        assert isinstance(factors, np.ndarray)
        assert len(factors.shape) == 1
    
    def test_clear_cache(self, sample_model_artifacts):
        """Test clearing cache."""
        artifacts = sample_model_artifacts
        service = CollaborativeFilteringService(
            user_factors_path=artifacts["user_factors_path"],
            item_factors_path=artifacts["item_factors_path"],
            user_mapping_path=artifacts["user_mapping_path"],
            product_mapping_path=artifacts["product_mapping_path"],
            metadata_path=artifacts["metadata_path"],
        )
        
        assert service.initialize()
        
        user_id = list(artifacts["user_mapping"].keys())[0]
        service.get_user_factors(user_id)
        
        assert user_id in service._user_factor_cache
        
        service.clear_cache()
        assert len(service._user_factor_cache) == 0


class TestGlobalService:
    """Test global service functions."""
    
    def test_get_collaborative_filtering_service_none(self):
        """Test getting CF service when not initialized."""
        # Reset global service
        import app.services.recommendation.collaborative as cf_module
        cf_module._cf_service = None
        
        service = get_collaborative_filtering_service()
        assert service is None
    
    @patch('app.services.recommendation.collaborative.CollaborativeFilteringService')
    def test_initialize_collaborative_filtering(self, mock_service_class, sample_model_artifacts):
        """Test initializing global CF service."""
        # Reset global service
        import app.services.recommendation.collaborative as cf_module
        cf_module._cf_service = None
        
        # Mock service
        mock_service = Mock()
        mock_service.initialize.return_value = True
        mock_service.is_available.return_value = True
        mock_service_class.return_value = mock_service
        
        result = initialize_collaborative_filtering()
        
        assert result is True
        assert get_collaborative_filtering_service() is not None

