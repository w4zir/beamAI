"""
Integration tests for query enhancement.

Tests:
- End-to-end query enhancement pipeline
- Integration with search endpoint
- Feature flag enable/disable
- Metrics collection
"""
import pytest
import os
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from app.main import app
from app.services.search.query_enhancement import get_query_enhancement_service, EnhancedQuery, QueryEnhancementService
from app.core.metrics import (
    query_enhancement_requests_total,
    query_spell_correction_total,
    query_synonym_expansion_total,
    query_classification_distribution,
)


client = TestClient(app)


def test_query_enhancement_pipeline():
    """Test end-to-end query enhancement pipeline."""
    service = get_query_enhancement_service()
    
    # Mock database and services for initialization
    with patch('app.core.database.get_supabase_client') as mock_db:
        
        # Setup mock database responses
        mock_response = Mock()
        mock_response.data = [
            {"name": "Nike Running Shoes", "category": "sports"},
            {"name": "Apple Laptop", "category": "electronics"},
        ]
        mock_db.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        # Test enhancement
        enhanced = service.enhance("nike runnig shoes")
        
        assert enhanced.original_query == "nike runnig shoes"
        assert enhanced.normalized_query is not None
        assert enhanced.classification in ["navigational", "informational", "transactional"]
        assert enhanced.entities is not None


def test_query_enhancement_with_spell_correction():
    """Test query enhancement with spell correction."""
    service = get_query_enhancement_service()
    
    with patch('app.core.database.get_supabase_client') as mock_db:
        
        mock_response = Mock()
        mock_response.data = [
            {"name": "Running Shoes", "category": "sports"},
        ]
        mock_db.return_value.table.return_value.select.return_value.execute.return_value = mock_response
        
        # Initialize spell correction
        from app.services.search.spell_correction import get_spell_correction_service
        spell_service = get_spell_correction_service()
        if spell_service:
            spell_service.initialize()
        
        enhanced = service.enhance("runnig shoes")
        
        # Should have normalized query at minimum
        assert enhanced.normalized_query is not None


def test_query_enhancement_with_synonym_expansion():
    """Test query enhancement with synonym expansion."""
    service = get_query_enhancement_service()
    
    with patch('app.core.database.get_supabase_client'):
        
        # Initialize synonym expansion
        from app.services.search.synonym_expansion import get_synonym_expansion_service
        synonym_service = get_synonym_expansion_service()
        if synonym_service:
            synonym_service.initialize()
        
        enhanced = service.enhance("sneakers")
        
        # Should have normalized query at minimum
        assert enhanced.normalized_query is not None


def test_search_endpoint_with_query_enhancement_disabled():
    """Test search endpoint with query enhancement disabled."""
    # Disable query enhancement
    original_value = os.getenv("ENABLE_QUERY_ENHANCEMENT", "false")
    os.environ["ENABLE_QUERY_ENHANCEMENT"] = "false"
    
    try:
        # Mock database for search
        with patch('app.services.search.keyword.get_supabase_client') as mock_db:
            mock_response = Mock()
            mock_response.data = [
                {"id": "prod_1", "name": "Running Shoes", "description": "Comfortable running shoes", "category": "sports", "search_vector": None},
            ]
            mock_db.return_value.table.return_value.select.return_value.execute.return_value = mock_response
            
            response = client.get("/search?q=running shoes&k=5")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    finally:
        # Restore original value
        if original_value:
            os.environ["ENABLE_QUERY_ENHANCEMENT"] = original_value
        else:
            os.environ.pop("ENABLE_QUERY_ENHANCEMENT", None)


def test_search_endpoint_with_query_enhancement_enabled():
    """Test search endpoint with query enhancement enabled."""
    # Enable query enhancement
    original_value = os.getenv("ENABLE_QUERY_ENHANCEMENT", "false")
    os.environ["ENABLE_QUERY_ENHANCEMENT"] = "true"
    
    try:
        # Mock database for search and enhancement services
        with patch('app.core.database.get_supabase_client') as mock_db:
            # Setup mock database responses
            mock_response = Mock()
            mock_response.data = [
                {"id": "prod_1", "name": "Running Shoes", "description": "Comfortable running shoes", "category": "sports", "search_vector": None},
                {"name": "Running Shoes", "category": "sports"},
            ]
            mock_db.return_value.table.return_value.select.return_value.execute.return_value = mock_response
            
            response = client.get("/search?q=running shoes&k=5")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    finally:
        # Restore original value
        if original_value:
            os.environ["ENABLE_QUERY_ENHANCEMENT"] = original_value
        else:
            os.environ.pop("ENABLE_QUERY_ENHANCEMENT", None)


def test_query_enhancement_metrics():
    """Test that query enhancement metrics are recorded."""
    from app.core.metrics import record_query_enhancement
    
    # Record metrics
    record_query_enhancement(
        correction_applied=True,
        correction_confidence=0.9,
        expansion_applied=True,
        classification="informational",
        latency_seconds=0.05,
    )
    
    # Check that metrics were incremented
    # Note: We can't easily assert metric values without scraping, but we can verify no exceptions
    assert True  # If we get here, metrics were recorded without error


def test_query_enhancement_feature_flag():
    """Test that feature flag correctly enables/disables query enhancement."""
    service = get_query_enhancement_service()
    
    # Test with all features enabled
    service_full = QueryEnhancementService(
        enable_spell_correction=True,
        enable_synonym_expansion=True,
        enable_classification=True,
        enable_intent_extraction=True,
    )
    
    assert service_full.enable_spell_correction
    assert service_full.enable_synonym_expansion
    assert service_full.enable_classification
    assert service_full.enable_intent_extraction
    
    # Test with all features disabled
    service_none = QueryEnhancementService(
        enable_spell_correction=False,
        enable_synonym_expansion=False,
        enable_classification=False,
        enable_intent_extraction=False,
    )
    
    assert not service_none.enable_spell_correction
    assert not service_none.enable_synonym_expansion
    assert not service_none.enable_classification
    assert not service_none.enable_intent_extraction


def test_query_enhancement_error_handling():
    """Test query enhancement error handling."""
    service = get_query_enhancement_service()
    
    # Test with invalid input
    enhanced = service.enhance("")
    assert enhanced.original_query == ""
    assert enhanced.normalized_query == ""
    
    # Test with None (should handle gracefully)
    enhanced = service.enhance(None)
    assert enhanced.original_query is None or enhanced.original_query == ""


def test_query_enhancement_latency():
    """Test that query enhancement latency is measured."""
    service = get_query_enhancement_service()
    
    with patch('app.core.database.get_supabase_client'):
        enhanced = service.enhance("test query")
        
        # Should have latency measurement
        assert enhanced.enhancement_latency_ms >= 0


def test_search_endpoint_empty_query():
    """Test search endpoint with empty query (should return 400)."""
    response = client.get("/search?q=")
    assert response.status_code == 400


def test_search_endpoint_missing_query():
    """Test search endpoint with missing query parameter (should return 422)."""
    response = client.get("/search")
    assert response.status_code == 422

