"""
Unit tests for Redis cache implementation (Phase 3.1).
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.cache import CacheClient, initialize_redis, close_redis, get_cache_client
from app.services.cache.query_cache import (
    get_cached_search_results,
    cache_search_results,
    generate_search_cache_key,
)


@pytest.mark.asyncio
async def test_cache_client_get_set():
    """Test cache client get and set operations."""
    with patch("app.core.cache.get_redis_client") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        
        cache = CacheClient()
        
        # Test set
        mock_redis.setex = AsyncMock(return_value=True)
        success = await cache.set("test_key", {"data": "value"}, 300)
        assert success is True
        
        # Test get
        mock_redis.get = AsyncMock(return_value='{"data": "value"}')
        result = await cache.get("test_key")
        assert result == {"data": "value"}


@pytest.mark.asyncio
async def test_cache_client_circuit_breaker():
    """Test cache client with circuit breaker open."""
    with patch("app.core.cache.get_redis_client") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        
        cache = CacheClient()
        cache.circuit_breaker = MagicMock()
        cache.circuit_breaker.state.value = "open"
        
        # Should return None when circuit breaker is open
        result = await cache.get("test_key")
        assert result is None
        
        success = await cache.set("test_key", "value", 300)
        assert success is False


@pytest.mark.asyncio
async def test_query_cache_key_generation():
    """Test query cache key generation."""
    key1 = generate_search_cache_key("test query", "user123", 10)
    key2 = generate_search_cache_key("test query", "user123", 10)
    key3 = generate_search_cache_key("different query", "user123", 10)
    
    # Same query should generate same key
    assert key1 == key2
    
    # Different query should generate different key
    assert key1 != key3


@pytest.mark.asyncio
async def test_query_cache_operations():
    """Test query cache get and set operations."""
    with patch("app.services.cache.query_cache.get_cache_client") as mock_get_cache:
        mock_cache = AsyncMock()
        mock_get_cache.return_value = mock_cache
        
        # Test cache miss
        mock_cache.get = AsyncMock(return_value=None)
        result = await get_cached_search_results("test query", "user123", 10)
        assert result is None
        
        # Test cache hit
        cached_data = [{"product_id": "prod1", "score": 0.9}]
        mock_cache.get = AsyncMock(return_value=cached_data)
        result = await get_cached_search_results("test query", "user123", 10)
        assert result == cached_data
        
        # Test cache set
        mock_cache.set = AsyncMock(return_value=True)
        success = await cache_search_results("test query", "user123", 10, cached_data)
        assert success is True

