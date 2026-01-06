"""
Redis cache client wrapper with connection pooling and circuit breaker.

Per CACHING_STRATEGY.md:
- Pool size: 20 connections
- Max overflow: 10 connections
- Connection timeout: 5 seconds
- Retry attempts: 3
"""
import os
import json
import hashlib
from typing import Optional, Any, Dict
import aioredis
from aioredis import Redis
from aioredis.exceptions import RedisError, ConnectionError as RedisConnectionError
from app.core.logging import get_logger
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

logger = get_logger(__name__)

# Global Redis connection pool
_redis_pool: Optional[Redis] = None
_cache_circuit_breaker: Optional[CircuitBreaker] = None


def get_redis_url() -> str:
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://redis:6379")


async def initialize_redis() -> bool:
    """
    Initialize Redis connection pool.
    
    Returns:
        True if initialization successful, False otherwise
    """
    global _redis_pool, _cache_circuit_breaker
    
    try:
        redis_url = get_redis_url()
        logger.info("redis_initializing", url=redis_url)
        
        # Create connection pool
        _redis_pool = await aioredis.from_url(
            redis_url,
            max_connections=20,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            decode_responses=True,  # Automatically decode responses to strings
        )
        
        # Test connection
        await _redis_pool.ping()
        
        # Initialize circuit breaker
        _cache_circuit_breaker = CircuitBreaker(
            name="redis_cache",
            failure_threshold=0.5,
            time_window_seconds=60,
            open_duration_seconds=30,
            half_open_test_percentage=0.1,
        )
        
        logger.info("redis_initialized")
        return True
        
    except Exception as e:
        logger.error(
            "redis_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        _redis_pool = None
        return False


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    
    if _redis_pool:
        try:
            await _redis_pool.close()
            await _redis_pool.connection_pool.disconnect()
            logger.info("redis_closed")
        except Exception as e:
            logger.error(
                "redis_close_failed",
                error=str(e),
                exc_info=True,
            )
        finally:
            _redis_pool = None


def get_redis_client() -> Optional[Redis]:
    """Get Redis client (for use in async context)."""
    return _redis_pool


class CacheClient:
    """
    Redis cache client with circuit breaker protection.
    
    Implements cache-aside pattern:
    1. Check cache
    2. If miss, query database
    3. Store in cache
    4. Return result
    """
    
    def __init__(self):
        self.circuit_breaker = _cache_circuit_breaker
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Returns:
            Cached value if found, None if miss or error
        """
        if not _redis_pool:
            return None
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.state.value == "open":
            logger.debug("cache_circuit_breaker_open", key=key)
            return None
        
        try:
            # Use circuit breaker protection
            if self.circuit_breaker:
                value = await self.circuit_breaker.call_async(
                    _redis_pool.get, key
                )
            else:
                value = await _redis_pool.get(key)
            
            if value is None:
                return None
            
            # Deserialize JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # If not JSON, return as string
                return value
                
        except CircuitBreakerOpenError:
            logger.debug("cache_circuit_breaker_open", key=key)
            return None
        except RedisError as e:
            logger.warning(
                "cache_get_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None
        except Exception as e:
            logger.error(
                "cache_get_unexpected_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
        
        Returns:
            True if successful, False otherwise
        """
        if not _redis_pool:
            return False
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.state.value == "open":
            logger.debug("cache_circuit_breaker_open", key=key)
            return False
        
        try:
            # Serialize value
            if isinstance(value, str):
                serialized = value
            else:
                serialized = json.dumps(value)
            
            # Use circuit breaker protection
            if self.circuit_breaker:
                await self.circuit_breaker.call_async(
                    _redis_pool.setex, key, ttl, serialized
                )
            else:
                await _redis_pool.setex(key, ttl, serialized)
            
            return True
            
        except CircuitBreakerOpenError:
            logger.debug("cache_circuit_breaker_open", key=key)
            return False
        except RedisError as e:
            logger.warning(
                "cache_set_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
        except Exception as e:
            logger.error(
                "cache_set_unexpected_error",
                key=key,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return False
    
    async def delete(self, pattern: str) -> int:
        """
        Delete keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards like 'search:*')
        
        Returns:
            Number of keys deleted
        """
        if not _redis_pool:
            return 0
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.state.value == "open":
            logger.debug("cache_circuit_breaker_open", pattern=pattern)
            return 0
        
        try:
            # Use SCAN to find matching keys (more efficient than KEYS)
            deleted_count = 0
            async for key in _redis_pool.scan_iter(match=pattern):
                if self.circuit_breaker:
                    await self.circuit_breaker.call_async(_redis_pool.delete, key)
                else:
                    await _redis_pool.delete(key)
                deleted_count += 1
            
            return deleted_count
            
        except CircuitBreakerOpenError:
            logger.debug("cache_circuit_breaker_open", pattern=pattern)
            return 0
        except RedisError as e:
            logger.warning(
                "cache_delete_error",
                pattern=pattern,
                error=str(e),
                error_type=type(e).__name__,
            )
            return 0
        except Exception as e:
            logger.error(
                "cache_delete_unexpected_error",
                pattern=pattern,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not _redis_pool:
            return False
        
        try:
            if self.circuit_breaker:
                result = await self.circuit_breaker.call_async(
                    _redis_pool.exists, key
                )
            else:
                result = await _redis_pool.exists(key)
            
            return bool(result)
        except (CircuitBreakerOpenError, RedisError):
            return False
    
    def get_circuit_breaker_metrics(self) -> Optional[Dict]:
        """Get circuit breaker metrics."""
        if self.circuit_breaker:
            return self.circuit_breaker.get_metrics()
        return None


# Global cache client instance
_cache_client: Optional[CacheClient] = None


def get_cache_client() -> CacheClient:
    """Get global cache client instance."""
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
    return _cache_client


def hash_query(query: str) -> str:
    """Generate hash for query string (for cache keys)."""
    return hashlib.md5(query.encode()).hexdigest()

