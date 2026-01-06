"""
Ranking configuration cache for ranking weights and configuration.

Per CACHING_STRATEGY.md:
- Key format: `ranking:weights:{category}` or `ranking:config:global`
- TTL: 1 day (or until manual refresh)
- Invalidation: Ranking weight updates, experiment configuration changes
"""
from typing import Optional, Dict, Any
from app.core.cache import get_cache_client
from app.core.logging import get_logger

logger = get_logger(__name__)

# TTL for ranking config: 1 day
RANKING_CACHE_TTL = 86400


def generate_ranking_weights_key(category: Optional[str] = None) -> str:
    """Generate cache key for ranking weights."""
    if category:
        return f"ranking:weights:{category}"
    return "ranking:weights:global"


def generate_ranking_config_key() -> str:
    """Generate cache key for ranking configuration."""
    return "ranking:config:global"


async def get_cached_ranking_weights(
    category: Optional[str] = None
) -> Optional[Dict[str, float]]:
    """
    Get cached ranking weights.
    
    Returns:
        Cached weights if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_ranking_weights_key(category)
    
    result = await cache.get(key)
    
    if result is not None:
        logger.debug("cache_hit", cache_type="ranking", key=key)
        return result
    else:
        logger.debug("cache_miss", cache_type="ranking", key=key)
        return None


async def cache_ranking_weights(
    weights: Dict[str, float],
    category: Optional[str] = None
) -> bool:
    """
    Cache ranking weights.
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_ranking_weights_key(category)
    
    success = await cache.set(key, weights, RANKING_CACHE_TTL)
    
    if success:
        logger.debug("cache_set", cache_type="ranking", key=key)
    else:
        logger.warning("cache_set_failed", cache_type="ranking", key=key)
    
    return success


async def get_cached_ranking_config() -> Optional[Dict[str, Any]]:
    """
    Get cached ranking configuration.
    
    Returns:
        Cached config if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_ranking_config_key()
    
    result = await cache.get(key)
    
    if result is not None:
        logger.debug("cache_hit", cache_type="ranking_config", key=key)
        return result
    else:
        logger.debug("cache_miss", cache_type="ranking_config", key=key)
        return None


async def cache_ranking_config(config: Dict[str, Any]) -> bool:
    """
    Cache ranking configuration.
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_ranking_config_key()
    
    success = await cache.set(key, config, RANKING_CACHE_TTL)
    
    if success:
        logger.debug("cache_set", cache_type="ranking_config", key=key)
    else:
        logger.warning("cache_set_failed", cache_type="ranking_config", key=key)
    
    return success


async def invalidate_ranking_cache(category: Optional[str] = None) -> int:
    """
    Invalidate ranking cache entries.
    
    Args:
        category: If provided, invalidate only entries for this category. Otherwise, invalidate all.
    
    Returns:
        Number of keys invalidated
    """
    cache = get_cache_client()
    
    if category:
        pattern = f"ranking:weights:{category}"
    else:
        pattern = "ranking:*"
    
    count = await cache.delete(pattern)
    logger.info("cache_invalidated", cache_type="ranking", pattern=pattern, count=count)
    return count

