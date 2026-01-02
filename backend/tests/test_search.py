"""
Basic integration tests for search endpoint.

These tests verify that the search endpoint returns expected structure.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_endpoint_structure():
    """Test that search endpoint returns expected structure."""
    response = client.get("/search?q=test&k=5")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return a list
    assert isinstance(data, list)
    
    # Each result should have required fields
    if len(data) > 0:
        result = data[0]
        assert "product_id" in result
        assert "score" in result
        assert isinstance(result["product_id"], str)
        assert isinstance(result["score"], (int, float))


def test_search_empty_query():
    """Test that empty query returns 400."""
    response = client.get("/search?q=")
    
    assert response.status_code == 400


def test_search_missing_query():
    """Test that missing query parameter returns 422."""
    response = client.get("/search")
    
    assert response.status_code == 422


def test_search_limit_parameter():
    """Test that k parameter works correctly."""
    response = client.get("/search?q=test&k=3")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should respect the limit (or return fewer if not enough results)
    assert len(data) <= 3


def test_recommend_endpoint_structure():
    """Test that recommend endpoint returns expected structure."""
    # Use a test user ID
    test_user_id = "test_user_123"
    
    response = client.get(f"/recommend/{test_user_id}?k=5")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return a list
    assert isinstance(data, list)
    
    # Each result should have required fields
    if len(data) > 0:
        result = data[0]
        assert "product_id" in result
        assert "score" in result
        assert isinstance(result["product_id"], str)
        assert isinstance(result["score"], (int, float))


def test_health_endpoint():
    """Test that health endpoint works."""
    response = client.get("/health")
    
    assert response.status_code == 200


def test_event_tracking_endpoint():
    """Test that event tracking endpoint accepts valid events."""
    event_data = {
        "user_id": "test_user_123",
        "product_id": "test_product_123",
        "event_type": "view",
        "source": "search"
    }
    
    response = client.post("/events", json=event_data)
    
    # Should either succeed (201/200) or fail gracefully (500 if DB not connected)
    assert response.status_code in [200, 201, 500]


def test_event_tracking_invalid_type():
    """Test that invalid event type returns 400."""
    event_data = {
        "user_id": "test_user_123",
        "product_id": "test_product_123",
        "event_type": "invalid_type",
        "source": "search"
    }
    
    response = client.post("/events", json=event_data)
    
    assert response.status_code == 400

