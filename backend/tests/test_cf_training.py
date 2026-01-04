"""
Tests for CF model training script.
"""
import pytest
import json
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from scipy.sparse import csr_matrix

from app.services.recommendation.collaborative import (
    extract_user_product_interactions,
    build_interaction_matrix,
    validate_interaction_matrix,
)


@pytest.fixture
def sample_interactions():
    """Sample user-product interactions."""
    return [
        ("user1", "product1", 3.0),
        ("user1", "product2", 2.0),
        ("user2", "product1", 1.0),
        ("user2", "product3", 3.0),
        ("user3", "product2", 2.0),
        ("user3", "product3", 1.0),
    ]


@pytest.fixture
def sample_matrix(sample_interactions):
    """Build sample interaction matrix."""
    matrix, _, _ = build_interaction_matrix(sample_interactions)
    return matrix


class TestTrainingPipeline:
    """Test training pipeline components."""
    
    @patch('app.services.recommendation.collaborative.get_supabase_client')
    def test_extract_interactions_success(self, mock_get_client, sample_interactions):
        """Test successful interaction extraction."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [
            {"user_id": "user1", "product_id": "product1", "event_type": "purchase", "timestamp": "2024-01-01T00:00:00Z"},
            {"user_id": "user1", "product_id": "product2", "event_type": "view", "timestamp": "2024-01-01T00:00:00Z"},
        ]
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        interactions = extract_user_product_interactions(days_back=None, min_interactions=1)
        
        assert len(interactions) == 2
    
    @patch('app.services.recommendation.collaborative.get_supabase_client')
    def test_extract_interactions_no_data(self, mock_get_client):
        """Test interaction extraction with no data."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        interactions = extract_user_product_interactions()
        
        assert len(interactions) == 0
    
    def test_build_matrix_from_interactions(self, sample_interactions):
        """Test building matrix from interactions."""
        matrix, user_mapping, product_mapping = build_interaction_matrix(sample_interactions)
        
        assert isinstance(matrix, csr_matrix)
        assert matrix.shape[0] == len(user_mapping)
        assert matrix.shape[1] == len(product_mapping)
        assert matrix.nnz == len(sample_interactions)
    
    def test_validate_matrix_valid(self, sample_matrix):
        """Test validating valid matrix."""
        assert validate_interaction_matrix(
            sample_matrix,
            min_users=1,
            min_products=1,
            min_interactions=1,
        )
    
    def test_validate_matrix_insufficient_users(self):
        """Test validating matrix with insufficient users."""
        matrix = csr_matrix((1, 10))  # 1 user, 10 products
        assert not validate_interaction_matrix(
            matrix,
            min_users=10,
            min_products=1,
            min_interactions=1,
        )
    
    def test_validate_matrix_insufficient_products(self):
        """Test validating matrix with insufficient products."""
        matrix = csr_matrix((10, 1))  # 10 users, 1 product
        assert not validate_interaction_matrix(
            matrix,
            min_users=1,
            min_products=10,
            min_interactions=1,
        )
    
    def test_validate_matrix_insufficient_interactions(self):
        """Test validating matrix with insufficient interactions."""
        matrix = csr_matrix((10, 10))
        assert not validate_interaction_matrix(
            matrix,
            min_users=1,
            min_products=1,
            min_interactions=100,
        )

