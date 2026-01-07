"""
LLM-specific caching helpers.

Implements cache-first strategy for Tier 1 agents (intent, rewrite)
using the existing Redis cache client from app.core.cache.

Cache keys (per AI_ARCHITECTURE.md and docs/implementation_plan.md):
- Intent cache:  llm:intent:{hash(query)}
- Rewrite cache: llm:rewrite:{hash(query)}

TTL:
- Intent / Rewrite: 24 hours
"""
from typing import Any, Dict, Optional

from app.core.cache import get_cache_client, hash_query
from app.core.logging import get_logger
from app.core.metrics import (
    record_llm_cache_hit,
    record_llm_cache_miss,
)

logger = get_logger(__name__)

INTENT_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h
REWRITE_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h


def _intent_cache_key(query: str) -> str:
    return f"llm:intent:{hash_query(query)}"


def _rewrite_cache_key(query: str) -> str:
    return f"llm:rewrite:{hash_query(query)}"


async def get_cached_intent(query: str) -> Optional[Dict[str, Any]]:
    """
    Get cached intent classification result for a query.

    Returns:
        Parsed JSON dict if present, None otherwise.
    """
    cache = get_cache_client()
    key = _intent_cache_key(query)

    result = await cache.get(key)
    if result is not None:
        record_llm_cache_hit("intent")
        logger.debug("llm_cache_hit", agent="intent", key=key)
        return result

    record_llm_cache_miss("intent")
    logger.debug("llm_cache_miss", agent="intent", key=key)
    return None


async def cache_intent(query: str, payload: Dict[str, Any]) -> None:
    """Cache intent classification result for a query."""
    cache = get_cache_client()
    key = _intent_cache_key(query)
    success = await cache.set(key, payload, INTENT_CACHE_TTL_SECONDS)
    if not success:
        # Best-effort cache; failures should not affect correctness.
        logger.warning("llm_cache_set_failed", agent="intent", key=key)


async def get_cached_rewrite(query: str) -> Optional[Dict[str, Any]]:
    """
    Get cached query rewrite result for a query.

    Returns:
        Parsed JSON dict if present, None otherwise.
    """
    cache = get_cache_client()
    key = _rewrite_cache_key(query)

    result = await cache.get(key)
    if result is not None:
        record_llm_cache_hit("rewrite")
        logger.debug("llm_cache_hit", agent="rewrite", key=key)
        return result

    record_llm_cache_miss("rewrite")
    logger.debug("llm_cache_miss", agent="rewrite", key=key)
    return None


async def cache_rewrite(query: str, payload: Dict[str, Any]) -> None:
    """Cache query rewrite result for a query."""
    cache = get_cache_client()
    key = _rewrite_cache_key(query)
    success = await cache.set(key, payload, REWRITE_CACHE_TTL_SECONDS)
    if not success:
        logger.warning("llm_cache_set_failed", agent="rewrite", key=key)


