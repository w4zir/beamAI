"""
Query result cache for search and recommendation endpoints.

Per CACHING_STRATEGY.md:
- Key format: `search:{query_hash}:{user_id}:{k}` or `recommend:{user_id}:{category}:{k}`
- TTL: 5 minutes
- Invalidation: Product updates, ranking weight changes
"""
import hashlib
from typing import List, Optional, Dict, Any
from app.core.cache import get_cache_client, hash_query
from app.core.logging import get_logger
from app.core.metrics import record_cache_hit, record_cache_miss

logger = get_logger(__name__)

# TTL for query results: 5 minutes
QUERY_CACHE_TTL = 300


def generate_search_cache_key(query: str, user_id: Optional[str], k: int) -> str:
    """Generate cache key for search results."""
    query_hash = hash_query(query)
    user_part = user_id or "anonymous"
    return f"search:{query_hash}:{user_part}:{k}"


def generate_recommend_cache_key(user_id: str, category: Optional[str], k: int) -> str:
    """Generate cache key for recommendation results."""
    category_part = category or "global"
    return f"recommend:{user_id}:{category_part}:{k}"


async def get_cached_search_results(
    query: str,
    user_id: Optional[str],
    k: int
) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached search results.
    
    Returns:
        Cached results if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_search_cache_key(query, user_id, k)
    
    result = await cache.get(key)
    
    if result is not None:
        record_cache_hit("search", "query_result")
        logger.debug("cache_hit", cache_type="search", key=key)
        return result
    else:
        record_cache_miss("search", "query_result")
        logger.debug("cache_miss", cache_type="search", key=key)
        return None


async def cache_search_results(
    query: str,
    user_id: Optional[str],
    k: int,
    results: List[Dict[str, Any]]
) -> bool:
    """
    Cache search results.
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_search_cache_key(query, user_id, k)
    
    success = await cache.set(key, results, QUERY_CACHE_TTL)
    
    if success:
        logger.debug("cache_set", cache_type="search", key=key, results_count=len(results))
    else:
        logger.warning("cache_set_failed", cache_type="search", key=key)
    
    return success


async def get_cached_recommend_results(
    user_id: str,
    category: Optional[str],
    k: int
) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached recommendation results.
    
    Returns:
        Cached results if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_recommend_cache_key(user_id, category, k)
    
    result = await cache.get(key)
    
    if result is not None:
        record_cache_hit("recommendation", "query_result")
        logger.debug("cache_hit", cache_type="recommendation", key=key)
        return result
    else:
        record_cache_miss("recommendation", "query_result")
        logger.debug("cache_miss", cache_type="recommendation", key=key)
        return None


async def cache_recommend_results(
    user_id: str,
    category: Optional[str],
    k: int,
    results: List[Dict[str, Any]]
) -> bool:
    """
    Cache recommendation results.
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_recommend_cache_key(user_id, category, k)
    
    success = await cache.set(key, results, QUERY_CACHE_TTL)
    
    if success:
        logger.debug("cache_set", cache_type="recommendation", key=key, results_count=len(results))
    else:
        logger.warning("cache_set_failed", cache_type="recommendation", key=key)
    
    return success


async def invalidate_search_cache(query: Optional[str] = None) -> int:
    """
    Invalidate search cache entries.
    
    Args:
        query: If provided, invalidate only entries for this query. Otherwise, invalidate all.
    
    Returns:
        Number of keys invalidated
    """
    cache = get_cache_client()
    
    if query:
        query_hash = hash_query(query)
        pattern = f"search:{query_hash}:*"
    else:
        pattern = "search:*"
    
    count = await cache.delete(pattern)
    logger.info("cache_invalidated", cache_type="search", pattern=pattern, count=count)
    return count


async def invalidate_recommend_cache(user_id: Optional[str] = None) -> int:
    """
    Invalidate recommendation cache entries.
    
    Args:
        user_id: If provided, invalidate only entries for this user. Otherwise, invalidate all.
    
    Returns:
        Number of keys invalidated
    """
    cache = get_cache_client()
    
    if user_id:
        pattern = f"recommend:{user_id}:*"
    else:
        pattern = "recommend:*"
    
    count = await cache.delete(pattern)
    logger.info("cache_invalidated", cache_type="recommendation", pattern=pattern, count=count)
    return count

