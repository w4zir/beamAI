"""
Unit tests for rate limiting (Phase 3.2).
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from starlette.datastructures import Headers
from app.core.rate_limit import (
    RateLimitMiddleware,
    get_client_ip,
    get_api_key,
    RATE_LIMITS,
)


def test_get_client_ip_from_forwarded_for():
    """Test extracting IP from X-Forwarded-For header."""
    headers = Headers({"X-Forwarded-For": "192.168.1.1, 10.0.0.1"})
    request = MagicMock()
    request.headers = headers
    request.client = None
    
    ip = get_client_ip(request)
    assert ip == "192.168.1.1"


def test_get_client_ip_from_real_ip():
    """Test extracting IP from X-Real-IP header."""
    headers = Headers({"X-Real-IP": "192.168.1.2"})
    request = MagicMock()
    request.headers = headers
    request.client = None
    
    ip = get_client_ip(request)
    assert ip == "192.168.1.2"


def test_get_client_ip_from_client():
    """Test extracting IP from request client."""
    request = MagicMock()
    request.headers = Headers({})
    request.client = MagicMock()
    request.client.host = "192.168.1.3"
    
    ip = get_client_ip(request)
    assert ip == "192.168.1.3"


def test_get_api_key_from_authorization():
    """Test extracting API key from Authorization header."""
    headers = Headers({"Authorization": "Bearer test_api_key_123"})
    request = MagicMock()
    request.headers = headers
    
    api_key = get_api_key(request)
    assert api_key == "test_api_key_123"


def test_get_api_key_from_apikey():
    """Test extracting API key from ApiKey format."""
    headers = Headers({"Authorization": "ApiKey test_key"})
    request = MagicMock()
    request.headers = headers
    
    api_key = get_api_key(request)
    assert api_key == "test_key"


@pytest.mark.asyncio
async def test_rate_limit_middleware_whitelist():
    """Test rate limit middleware with whitelisted IP."""
    app = MagicMock()
    middleware = RateLimitMiddleware(app, redis_client=None)
    middleware.add_to_whitelist("192.168.1.1")
    
    request = MagicMock()
    request.url.path = "/search"
    request.query_params = {}
    request.headers = Headers({})
    request.client = MagicMock()
    request.client.host = "192.168.1.1"
    
    async def call_next(req):
        return MagicMock()
    
    # Should bypass rate limiting
    response = await middleware.dispatch(request, call_next)
    assert response is not None


@pytest.mark.asyncio
async def test_rate_limit_middleware_blacklist():
    """Test rate limit middleware with blacklisted IP."""
    app = MagicMock()
    middleware = RateLimitMiddleware(app, redis_client=None)
    middleware.add_to_blacklist("192.168.1.1")
    
    request = MagicMock()
    request.url.path = "/search"
    request.query_params = {}
    request.headers = Headers({})
    request.client = MagicMock()
    request.client.host = "192.168.1.1"
    
    async def call_next(req):
        return MagicMock()
    
    # Should return 403
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rate_limit_check_with_redis():
    """Test rate limit check using Redis."""
    mock_redis = AsyncMock()
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.zremrangebyscore = AsyncMock(return_value=0)
    mock_redis.zcard = AsyncMock(return_value=5)  # 5 requests in window
    mock_redis.expire = AsyncMock(return_value=True)
    
    app = MagicMock()
    middleware = RateLimitMiddleware(app, redis_client=mock_redis)
    
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        identifier="test_ip",
        limit=100,
        window=60,
        endpoint="/search",
    )
    
    assert allowed is True  # 5 < 100
    assert remaining == 95


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    """Test rate limit when limit is exceeded."""
    mock_redis = AsyncMock()
    mock_redis.zadd = AsyncMock(return_value=1)
    mock_redis.zremrangebyscore = AsyncMock(return_value=0)
    mock_redis.zcard = AsyncMock(return_value=150)  # Exceeds limit of 100
    mock_redis.expire = AsyncMock(return_value=True)
    
    app = MagicMock()
    middleware = RateLimitMiddleware(app, redis_client=mock_redis)
    
    allowed, remaining, reset_time = await middleware._check_rate_limit(
        identifier="test_ip",
        limit=100,
        window=60,
        endpoint="/search",
    )
    
    assert allowed is False
    assert remaining == 0

