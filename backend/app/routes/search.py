"""
Search endpoint for keyword and hybrid search.

GET /search?q={query}&user_id={optional}&k={int}
"""
import os
import time
from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, List
from pydantic import BaseModel

from app.core.logging import get_logger, set_user_id
from app.core.metrics import (
    record_search_zero_result,
    record_cache_hit,
    record_cache_miss,
    record_ranking_score,
    record_query_enhancement,
)
from app.services.search.keyword import search_keywords
from app.services.search.hybrid import hybrid_search
from app.services.search.semantic import get_semantic_search_service
from app.services.search.query_enhancement import get_query_enhancement_service
from app.services.ranking.score import rank_products
from app.services.cache.query_cache import (
    get_cached_search_results,
    cache_search_results,
)

logger = get_logger(__name__)

router = APIRouter()


class SearchResult(BaseModel):
    """Search result model."""
    product_id: str
    score: float
    reason: Optional[str] = None


@router.get("", response_model=List[SearchResult])
async def search(
    request: Request,
    q: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Optional user ID for personalization"),
    k: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """
    Search for products using keyword or hybrid search with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    Uses hybrid search (keyword + semantic) if ENABLE_SEMANTIC_SEARCH=true and semantic search is available.
    Otherwise falls back to keyword search only.
    """
    start_time = time.time()
    query = q.strip() if q else ""
    
    # Set user_id in context if provided
    if user_id:
        set_user_id(user_id)
    
    if not query:
        logger.warning(
            "search_query_empty",
            query=q,
        )
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    # Check cache first (Phase 3.1)
    cached_results = await get_cached_search_results(query, user_id, k)
    if cached_results is not None:
        # Convert cached results to SearchResult models
        results = [SearchResult(**r) for r in cached_results]
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "search_completed_cached",
            query=query,
            user_id=user_id,
            results_count=len(results),
            latency_ms=latency_ms,
        )
        return results
    
    try:
        # Check feature flag for query enhancement
        enable_query_enhancement = os.getenv("ENABLE_QUERY_ENHANCEMENT", "false").lower() == "true"
        
        # Apply query enhancement if enabled
        enhanced_query_obj = None
        search_query = query  # Default to original query
        
        if enable_query_enhancement:
            enhancement_service = get_query_enhancement_service()
            enhanced_query_obj = enhancement_service.enhance(query)
            search_query = enhanced_query_obj.get_final_query()
            
            # Record query enhancement metrics
            record_query_enhancement(
                correction_applied=enhanced_query_obj.correction_applied,
                correction_confidence=enhanced_query_obj.corrected_confidence,
                expansion_applied=enhanced_query_obj.expansion_applied,
                classification=enhanced_query_obj.classification,
                latency_seconds=enhanced_query_obj.enhancement_latency_ms / 1000.0,
            )
            
            logger.info(
                "query_enhancement_applied",
                original_query=query,
                final_query=search_query,
                classification=enhanced_query_obj.classification,
                correction_applied=enhanced_query_obj.correction_applied,
                expansion_applied=enhanced_query_obj.expansion_applied,
            )
        
        # Check feature flag for semantic search
        enable_semantic = os.getenv("ENABLE_SEMANTIC_SEARCH", "false").lower() == "true"
        semantic_service = get_semantic_search_service()
        semantic_available = semantic_service and semantic_service.is_available()
        use_hybrid = enable_semantic and semantic_available
        
        logger.info(
            "search_started",
            query=query,
            enhanced_query=search_query if enable_query_enhancement else None,
            user_id=user_id,
            k=k,
            enable_semantic=enable_semantic,
            semantic_available=semantic_available,
            use_hybrid=use_hybrid,
            enable_query_enhancement=enable_query_enhancement,
        )
        
        # Get candidates from search service (hybrid or keyword only)
        # Use enhanced query for search
        if use_hybrid:
            candidates = hybrid_search(search_query, limit=k * 2)
        else:
            candidates = search_keywords(search_query, limit=k * 2)
        
        if not candidates:
            latency_ms = int((time.time() - start_time) * 1000)
            # Record zero-result metric (use original query for pattern matching)
            record_search_zero_result(query=query)
            logger.info(
                "search_zero_results",
                query=query,
                enhanced_query=search_query if enable_query_enhancement else None,
                user_id=user_id,
                latency_ms=latency_ms,
            )
            return []
        
        # Apply ranking (async, Phase 3.5)
        try:
            ranked = await rank_products(candidates, is_search=True, user_id=user_id)
            
            # Format results and record ranking scores
            results = []
            for product_id, final_score, breakdown in ranked[:k]:
                # Record ranking score for distribution analysis
                record_ranking_score(product_id=product_id, score=final_score)
                results.append(
                    SearchResult(
                        product_id=product_id,
                        score=final_score,
                        reason=f"Ranked score: {final_score:.3f} (search: {breakdown['search_score']:.3f}, popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                    )
                )
        except Exception as ranking_error:
            logger.warning(
                "search_ranking_failed",
                query=query,
                error=str(ranking_error),
                error_type=type(ranking_error).__name__,
            )
            # Fallback: sort by search_score
            candidates.sort(key=lambda x: x[1], reverse=True)
            results = [
                SearchResult(
                    product_id=product_id,
                    score=score,
                    reason=f"Keyword match score: {score:.3f} (ranking unavailable)"
                )
                for product_id, score in candidates[:k]
            ]
        
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "search_completed",
            query=query,
            enhanced_query=search_query if enable_query_enhancement else None,
            user_id=user_id,
            results_count=len(results),
            latency_ms=latency_ms,
            use_hybrid=use_hybrid,
            enable_query_enhancement=enable_query_enhancement,
        )
        
        # Cache results (Phase 3.1)
        # Convert SearchResult models to dicts for caching
        results_dict = [r.dict() for r in results]
        await cache_search_results(query, user_id, k, results_dict)
        
        return results
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "search_error",
            query=query,
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            latency_ms=latency_ms,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error during search")

