"""
Search endpoint for keyword search.

GET /search?q={query}&user_id={optional}&k={int}
"""
import time
from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, List
from pydantic import BaseModel

from app.core.logging import get_logger, set_user_id
from app.services.search.keyword import search_keywords
from app.services.ranking.score import rank_products

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
    Search for products using keyword search with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    start_time = time.time()
    query = q.strip() if q else ""
    cache_hit = False  # TODO: Implement caching in Phase 2
    
    # Set user_id in context if provided
    if user_id:
        set_user_id(user_id)
    
    if not query:
        logger.warning(
            "search_query_empty",
            query=q,
        )
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    try:
        logger.info(
            "search_started",
            query=query,
            user_id=user_id,
            k=k,
        )
        
        # Get candidates from search service
        candidates = search_keywords(query, limit=k * 2)
        
        if not candidates:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "search_zero_results",
                query=query,
                user_id=user_id,
                latency_ms=latency_ms,
                cache_hit=cache_hit,
            )
            return []
        
        # Apply ranking
        try:
            ranked = rank_products(candidates, is_search=True, user_id=user_id)
            
            # Format results
            results = [
                SearchResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (search: {breakdown['search_score']:.3f}, popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
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
            user_id=user_id,
            results_count=len(results),
            latency_ms=latency_ms,
            cache_hit=cache_hit,
        )
        
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

