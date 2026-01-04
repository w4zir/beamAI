"""
Unit tests for hybrid search service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.search.hybrid import hybrid_search
from app.services.search.semantic import get_semantic_search_service


@pytest.fixture
def mock_keyword_results():
    """Mock keyword search results."""
    return [
        ("prod_1", 0.9),
        ("prod_2", 0.7),
        ("prod_3", 0.5),
    ]


@pytest.fixture
def mock_semantic_results():
    """Mock semantic search results."""
    return [
        ("prod_2", 0.8),
        ("prod_3", 0.6),
        ("prod_4", 0.4),
    ]


@patch('app.services.search.hybrid.search_keywords')
@patch('app.services.search.hybrid.get_semantic_search_service')
def test_hybrid_search_both_available(mock_get_semantic, mock_keyword_search, mock_keyword_results, mock_semantic_results):
    """Test hybrid search when both keyword and semantic search are available."""
    # Setup mocks
    mock_keyword_search.return_value = mock_keyword_results
    
    mock_semantic_service = MagicMock()
    mock_semantic_service.is_available.return_value = True
    mock_semantic_service.search.return_value = mock_semantic_results
    mock_get_semantic.return_value = mock_semantic_service
    
    # Execute
    results = hybrid_search("test query", limit=10)
    
    # Verify
    assert len(results) > 0
    # prod_1: only in keyword (0.9)
    # prod_2: in both, max(0.7, 0.8) = 0.8
    # prod_3: in both, max(0.5, 0.6) = 0.6
    # prod_4: only in semantic (0.4)
    
    # Check that max scores are used
    result_dict = dict(results)
    assert result_dict["prod_1"] == 0.9
    assert result_dict["prod_2"] == 0.8  # max of 0.7 and 0.8
    assert result_dict["prod_3"] == 0.6  # max of 0.5 and 0.6
    assert result_dict["prod_4"] == 0.4
    
    # Results should be sorted by score descending
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True)


@patch('app.services.search.hybrid.search_keywords')
@patch('app.services.search.hybrid.get_semantic_search_service')
def test_hybrid_search_keyword_only(mock_get_semantic, mock_keyword_search, mock_keyword_results):
    """Test hybrid search when semantic search is not available."""
    # Setup mocks
    mock_keyword_search.return_value = mock_keyword_results
    
    mock_semantic_service = MagicMock()
    mock_semantic_service.is_available.return_value = False
    mock_get_semantic.return_value = mock_semantic_service
    
    # Execute
    results = hybrid_search("test query", limit=10)
    
    # Verify - should only have keyword results
    assert len(results) == len(mock_keyword_results)
    result_dict = dict(results)
    assert result_dict["prod_1"] == 0.9
    assert result_dict["prod_2"] == 0.7
    assert result_dict["prod_3"] == 0.5


@patch('app.services.search.hybrid.search_keywords')
@patch('app.services.search.hybrid.get_semantic_search_service')
def test_hybrid_search_semantic_fails(mock_get_semantic, mock_keyword_search, mock_keyword_results):
    """Test hybrid search when semantic search fails."""
    # Setup mocks
    mock_keyword_search.return_value = mock_keyword_results
    
    mock_semantic_service = MagicMock()
    mock_semantic_service.is_available.return_value = True
    mock_semantic_service.search.side_effect = Exception("Semantic search failed")
    mock_get_semantic.return_value = mock_semantic_service
    
    # Execute - should fallback to keyword only
    results = hybrid_search("test query", limit=10)
    
    # Verify - should only have keyword results
    assert len(results) == len(mock_keyword_results)
    result_dict = dict(results)
    assert result_dict["prod_1"] == 0.9
    assert result_dict["prod_2"] == 0.7
    assert result_dict["prod_3"] == 0.5


@patch('app.services.search.hybrid.search_keywords')
@patch('app.services.search.hybrid.get_semantic_search_service')
def test_hybrid_search_limit(mock_get_semantic, mock_keyword_search, mock_keyword_results, mock_semantic_results):
    """Test that hybrid search respects limit."""
    # Setup mocks
    mock_keyword_search.return_value = mock_keyword_results
    
    mock_semantic_service = MagicMock()
    mock_semantic_service.is_available.return_value = True
    mock_semantic_service.search.return_value = mock_semantic_results
    mock_get_semantic.return_value = mock_semantic_service
    
    # Execute with limit
    results = hybrid_search("test query", limit=2)
    
    # Verify limit is respected
    assert len(results) <= 2


@patch('app.services.search.hybrid.search_keywords')
@patch('app.services.search.hybrid.get_semantic_search_service')
def test_hybrid_search_empty_keyword(mock_get_semantic, mock_keyword_search, mock_semantic_results):
    """Test hybrid search when keyword search returns empty."""
    # Setup mocks
    mock_keyword_search.return_value = []
    
    mock_semantic_service = MagicMock()
    mock_semantic_service.is_available.return_value = True
    mock_semantic_service.search.return_value = mock_semantic_results
    mock_get_semantic.return_value = mock_semantic_service
    
    # Execute
    results = hybrid_search("test query", limit=10)
    
    # Verify - should only have semantic results
    assert len(results) == len(mock_semantic_results)
    result_dict = dict(results)
    assert result_dict["prod_2"] == 0.8
    assert result_dict["prod_3"] == 0.6
    assert result_dict["prod_4"] == 0.4


@patch('app.services.search.hybrid.search_keywords')
@patch('app.services.search.hybrid.get_semantic_search_service')
def test_hybrid_search_empty_semantic(mock_get_semantic, mock_keyword_search, mock_keyword_results):
    """Test hybrid search when semantic search returns empty."""
    # Setup mocks
    mock_keyword_search.return_value = mock_keyword_results
    
    mock_semantic_service = MagicMock()
    mock_semantic_service.is_available.return_value = True
    mock_semantic_service.search.return_value = []
    mock_get_semantic.return_value = mock_semantic_service
    
    # Execute
    results = hybrid_search("test query", limit=10)
    
    # Verify - should only have keyword results
    assert len(results) == len(mock_keyword_results)
    result_dict = dict(results)
    assert result_dict["prod_1"] == 0.9
    assert result_dict["prod_2"] == 0.7
    assert result_dict["prod_3"] == 0.5

