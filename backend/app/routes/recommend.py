"""
Recommendation endpoint for product recommendations.

GET /recommend/{user_id}?k={int}
"""
import time
from fastapi import APIRouter, Path, Query, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel

from app.core.logging import get_logger, set_user_id
from app.core.metrics import (
    record_search_zero_result,
    record_cache_hit,
    record_cache_miss,
    record_ranking_score,
)
from app.services.recommendation.popularity import get_popularity_recommendations
from app.services.ranking.score import rank_products
from app.core.database import get_supabase_client
from app.services.cache.query_cache import (
    get_cached_recommend_results,
    cache_recommend_results,
)

logger = get_logger(__name__)

router = APIRouter()


class RecommendResult(BaseModel):
    """Recommendation result model."""
    product_id: str
    score: float
    reason: Optional[str] = None


@router.get("/{user_id}", response_model=List[RecommendResult])
async def recommend(
    request: Request,
    user_id: str = Path(..., description="User ID"),
    k: int = Query(10, ge=1, le=100, description="Number of recommendations to return")
):
    """
    Get product recommendations for a user with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    start_time = time.time()
    
    # Set user_id in context
    set_user_id(user_id)
    
    # Check cache first (Phase 3.1)
    cached_results = await get_cached_recommend_results(user_id, None, k)
    if cached_results is not None:
        # Convert cached results to RecommendResult models
        results = [RecommendResult(**r) for r in cached_results]
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "recommendation_completed_cached",
            user_id=user_id,
            results_count=len(results),
            latency_ms=latency_ms,
        )
        return results
    
    try:
        logger.info(
            "recommendation_started",
            user_id=user_id,
            k=k,
        )
        
        # Verify user exists
        client = get_supabase_client()
        if client:
            user_check = client.table("users").select("id").eq("id", user_id).limit(1).execute()
            if not user_check.data:
                logger.warning(
                    "recommendation_user_not_found",
                    user_id=user_id,
                )
        
        # Get candidates from recommendation service
        candidate_ids = get_popularity_recommendations(user_id=user_id, limit=k * 2)
        
        if not candidate_ids:
            latency_ms = int((time.time() - start_time) * 1000)
            # Record zero-result metric (for recommendations, query is None)
            record_search_zero_result(query=None)
            logger.info(
                "recommendation_zero_results",
                user_id=user_id,
                latency_ms=latency_ms,
            )
            return []
        
        # Convert to candidates format (product_id, search_score=0 for recommendations)
        candidates = [(product_id, 0.0) for product_id in candidate_ids]
        
        # Apply ranking (is_search=False for recommendations, async Phase 3.5)
        try:
            ranked = await rank_products(candidates, is_search=False, user_id=user_id)
            
            # Format results and record ranking scores
            results = []
            for product_id, final_score, breakdown in ranked[:k]:
                # Record ranking score for distribution analysis
                record_ranking_score(product_id=product_id, score=final_score)
                results.append(
                    RecommendResult(
                        product_id=product_id,
                        score=final_score,
                        reason=f"Ranked score: {final_score:.3f} (cf: {breakdown['cf_score']:.3f}, popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                    )
                )
        except Exception as ranking_error:
            logger.warning(
                "recommendation_ranking_failed",
                user_id=user_id,
                error=str(ranking_error),
                error_type=type(ranking_error).__name__,
            )
            # Fallback: use popularity scores
            if client:
                products = client.table("products").select("id, popularity_score").in_("id", candidate_ids).execute()
                score_map = {p["id"]: p.get("popularity_score", 0.0) or 0.0 for p in products.data}
            else:
                score_map = {}
            
            # Sort by popularity
            sorted_candidates = sorted(candidate_ids, key=lambda pid: score_map.get(pid, 0.0), reverse=True)
            
            results = [
                RecommendResult(
                    product_id=product_id,
                    score=score_map.get(product_id, 0.0),
                    reason=f"Popularity score: {score_map.get(product_id, 0.0):.3f} (ranking unavailable)"
                )
                for product_id in sorted_candidates[:k]
            ]
        
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "recommendation_completed",
            user_id=user_id,
            results_count=len(results),
            latency_ms=latency_ms,
        )
        
        # Cache results (Phase 3.1)
        # Convert RecommendResult models to dicts for caching
        results_dict = [r.dict() for r in results]
        await cache_recommend_results(user_id, None, k, results_dict)
        
        return results
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "recommendation_error",
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
            latency_ms=latency_ms,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error during recommendation")

