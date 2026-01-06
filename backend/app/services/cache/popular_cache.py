"""
Popular products cache for fast recommendations.

Per CACHING_STRATEGY.md:
- Key format: `popular:{category}:{k}` or `popular:global:{k}`
- TTL: 5 minutes
- Invalidation: Popularity score batch job completion, product availability changes
"""
from typing import List, Optional, Dict, Any
from app.core.cache import get_cache_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# TTL for popular products: 5 minutes
POPULAR_CACHE_TTL = 300


def generate_popular_cache_key(category: Optional[str], k: int) -> str:
    """Generate cache key for popular products."""
    category_part = category or "global"
    return f"popular:{category_part}:{k}"


async def get_cached_popular_products(
    category: Optional[str],
    k: int
) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached popular products.
    
    Returns:
        Cached products if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_popular_cache_key(category, k)
    
    result = await cache.get(key)
    
    if result is not None:
        logger.debug("cache_hit", cache_type="popular", key=key)
        return result
    else:
        logger.debug("cache_miss", cache_type="popular", key=key)
        return None


async def cache_popular_products(
    category: Optional[str],
    k: int,
    products: List[Dict[str, Any]]
) -> bool:
    """
    Cache popular products.
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_popular_cache_key(category, k)
    
    success = await cache.set(key, products, POPULAR_CACHE_TTL)
    
    if success:
        logger.debug("cache_set", cache_type="popular", key=key, products_count=len(products))
    else:
        logger.warning("cache_set_failed", cache_type="popular", key=key)
    
    return success


async def invalidate_popular_cache(category: Optional[str] = None) -> int:
    """
    Invalidate popular products cache entries.
    
    Args:
        category: If provided, invalidate only entries for this category. Otherwise, invalidate all.
    
    Returns:
        Number of keys invalidated
    """
    cache = get_cache_client()
    
    if category:
        pattern = f"popular:{category}:*"
    else:
        pattern = "popular:*"
    
    count = await cache.delete(pattern)
    logger.info("cache_invalidated", cache_type="popular", pattern=pattern, count=count)
    return count

