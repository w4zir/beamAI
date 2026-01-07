"""
Feature retrieval for ranking service.

Fetches features needed for ranking:
- popularity_score from products table
- freshness_score computed on-demand

Phase 3.5: Converted to async for better concurrency.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from app.core.logging import get_logger
from app.core.database_router import execute_read_query
from app.core.tracing import get_tracer, set_span_attribute, record_exception, set_span_status, StatusCode
from app.services.features.freshness import compute_freshness_score_from_string
from app.services.cache.feature_cache import (
    get_cached_product_feature,
    cache_product_feature,
)

logger = get_logger(__name__)


async def get_product_features(product_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get features for a list of products (async, with caching and batch fetching).
    
    Phase 3.5: Converted to async, uses connection pool, batch fetching, and feature cache.
    
    Returns:
        Dictionary mapping product_id to feature dict:
        {
            "popularity_score": float,
            "freshness_score": float
        }
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("features.fetch") as span:
        set_span_attribute("features.product_ids_count", len(product_ids))
        
        if not product_ids:
            return {}
        
        features = {}
        uncached_ids = []
        
        # Check cache for each product (Phase 3.1)
        cache_tasks = [
            get_cached_product_feature(product_id, "popularity_score")
            for product_id in product_ids
        ]
        cached_popularity = await asyncio.gather(*cache_tasks, return_exceptions=True)
        
        cache_tasks_freshness = [
            get_cached_product_feature(product_id, "freshness_score")
            for product_id in product_ids
        ]
        cached_freshness = await asyncio.gather(*cache_tasks_freshness, return_exceptions=True)
        
        # Process cached results and identify uncached products
        for i, product_id in enumerate(product_ids):
            pop_score = cached_popularity[i] if not isinstance(cached_popularity[i], Exception) else None
            fresh_score = cached_freshness[i] if not isinstance(cached_freshness[i], Exception) else None
            
            if pop_score is not None and fresh_score is not None:
                # Both features cached
                features[product_id] = {
                    "popularity_score": float(pop_score),
                    "freshness_score": float(fresh_score),
                }
            else:
                # Need to fetch from database
                uncached_ids.append(product_id)
        
        # Fetch uncached products from database (batch query)
        if uncached_ids:
            try:
                # Build parameterized query
                placeholders = ",".join([f"${i+1}" for i in range(len(uncached_ids))])
                query = f"""
                    SELECT id, popularity_score, created_at
                    FROM products
                    WHERE id IN ({placeholders})
                """
                
                with tracer.start_as_current_span("database.query") as db_span:
                    set_span_attribute("db.query", "SELECT id, popularity_score, created_at FROM products")
                    set_span_attribute("db.table", "products")
                    set_span_attribute("db.uncached_count", len(uncached_ids))
                    
                    # Execute async query
                    rows = await execute_read_query(
                        query,
                        *uncached_ids,
                        query_type="feature",
                    )
                    
                    set_span_attribute("db.results_count", len(rows))
                
                # Process database results
                for row in rows:
                    product_id = row["id"]
                    popularity_score = row.get("popularity_score", 0.0) or 0.0
                    created_at = row.get("created_at")
                    
                    # Compute freshness score
                    freshness_score = 0.0
                    if created_at:
                        # Handle both string and datetime objects
                        if isinstance(created_at, str):
                            freshness_score = compute_freshness_score_from_string(created_at)
                        else:
                            freshness_score = compute_freshness_score_from_string(str(created_at))
                    
                    features[product_id] = {
                        "popularity_score": float(popularity_score),
                        "freshness_score": freshness_score,
                    }
                    
                    # Cache features (async, fire and forget)
                    asyncio.create_task(cache_product_feature(product_id, "popularity_score", float(popularity_score)))
                    asyncio.create_task(cache_product_feature(product_id, "freshness_score", freshness_score))
                
                # Set span attributes
                set_span_attribute("features.retrieved_count", len(features))
                set_span_status(StatusCode.OK)
                
            except Exception as e:
                record_exception(e)
                set_span_status(StatusCode.ERROR, str(e))
                logger.error(
                    "feature_retrieval_error",
                    product_ids_count=len(product_ids),
                    uncached_count=len(uncached_ids),
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                # Return cached features even if DB fetch failed
                pass
        
        logger.debug(
            "features_retrieved",
            requested_count=len(product_ids),
            retrieved_count=len(features),
            cached_count=len(product_ids) - len(uncached_ids),
        )
        return features


async def get_single_product_features(product_id: str) -> Optional[Dict[str, float]]:
    """
    Get features for a single product (async).
    
    Returns:
        Feature dict or None if product not found
    """
    features = await get_product_features([product_id])
    return features.get(product_id)

