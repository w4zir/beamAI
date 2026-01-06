"""
Feature cache for product and user features.

Per CACHING_STRATEGY.md:
- Key format: `feature:{product_id}:{feature_name}` or `feature:{user_id}:{feature_name}`
- TTL: 1 hour for products, 24 hours for users, 5 minutes for popularity
- Invalidation: Product updates, user events (after batch job)
"""
from typing import Optional, Any
from app.core.cache import get_cache_client
from app.core.logging import get_logger
from app.core.metrics import record_cache_hit, record_cache_miss

logger = get_logger(__name__)

# TTLs for different feature types
FEATURE_CACHE_TTL_PRODUCT = 3600  # 1 hour
FEATURE_CACHE_TTL_USER = 86400  # 24 hours
FEATURE_CACHE_TTL_POPULARITY = 300  # 5 minutes


def generate_product_feature_key(product_id: str, feature_name: str) -> str:
    """Generate cache key for product feature."""
    return f"feature:{product_id}:{feature_name}"


def generate_user_feature_key(user_id: str, feature_name: str) -> str:
    """Generate cache key for user feature."""
    return f"feature:{user_id}:{feature_name}"


async def get_cached_product_feature(
    product_id: str,
    feature_name: str
) -> Optional[Any]:
    """
    Get cached product feature.
    
    Returns:
        Cached feature value if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_product_feature_key(product_id, feature_name)
    
    result = await cache.get(key)
    
    if result is not None:
        record_cache_hit("feature", "product")
        logger.debug("cache_hit", cache_type="feature", feature=feature_name, product_id=product_id)
        return result
    else:
        record_cache_miss("feature", "product")
        logger.debug("cache_miss", cache_type="feature", feature=feature_name, product_id=product_id)
        return None


async def cache_product_feature(
    product_id: str,
    feature_name: str,
    value: Any,
    ttl: Optional[int] = None
) -> bool:
    """
    Cache product feature.
    
    Args:
        product_id: Product ID
        feature_name: Feature name
        value: Feature value
        ttl: Time to live (defaults to FEATURE_CACHE_TTL_PRODUCT)
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_product_feature_key(product_id, feature_name)
    
    # Use specific TTL for popularity score
    if feature_name == "popularity_score":
        cache_ttl = FEATURE_CACHE_TTL_POPULARITY
    else:
        cache_ttl = ttl or FEATURE_CACHE_TTL_PRODUCT
    
    success = await cache.set(key, value, cache_ttl)
    
    if success:
        logger.debug("cache_set", cache_type="feature", feature=feature_name, product_id=product_id)
    else:
        logger.warning("cache_set_failed", cache_type="feature", feature=feature_name, product_id=product_id)
    
    return success


async def get_cached_user_feature(
    user_id: str,
    feature_name: str
) -> Optional[Any]:
    """
    Get cached user feature.
    
    Returns:
        Cached feature value if found, None otherwise
    """
    cache = get_cache_client()
    key = generate_user_feature_key(user_id, feature_name)
    
    result = await cache.get(key)
    
    if result is not None:
        record_cache_hit("feature", "user")
        logger.debug("cache_hit", cache_type="feature", feature=feature_name, user_id=user_id)
        return result
    else:
        record_cache_miss("feature", "user")
        logger.debug("cache_miss", cache_type="feature", feature=feature_name, user_id=user_id)
        return None


async def cache_user_feature(
    user_id: str,
    feature_name: str,
    value: Any,
    ttl: Optional[int] = None
) -> bool:
    """
    Cache user feature.
    
    Args:
        user_id: User ID
        feature_name: Feature name
        value: Feature value
        ttl: Time to live (defaults to FEATURE_CACHE_TTL_USER)
    
    Returns:
        True if cached successfully, False otherwise
    """
    cache = get_cache_client()
    key = generate_user_feature_key(user_id, feature_name)
    cache_ttl = ttl or FEATURE_CACHE_TTL_USER
    
    success = await cache.set(key, value, cache_ttl)
    
    if success:
        logger.debug("cache_set", cache_type="feature", feature=feature_name, user_id=user_id)
    else:
        logger.warning("cache_set_failed", cache_type="feature", feature=feature_name, user_id=user_id)
    
    return success


async def invalidate_product_features(product_id: str) -> int:
    """
    Invalidate all cached features for a product.
    
    Returns:
        Number of keys invalidated
    """
    cache = get_cache_client()
    pattern = f"feature:{product_id}:*"
    
    count = await cache.delete(pattern)
    logger.info("cache_invalidated", cache_type="feature", pattern=pattern, count=count)
    return count


async def invalidate_user_features(user_id: str) -> int:
    """
    Invalidate all cached features for a user.
    
    Returns:
        Number of keys invalidated
    """
    cache = get_cache_client()
    pattern = f"feature:{user_id}:*"
    
    count = await cache.delete(pattern)
    logger.info("cache_invalidated", cache_type="feature", pattern=pattern, count=count)
    return count

