"""
Recommendation endpoint for product recommendations.

GET /recommend/{user_id}?k={int}
"""
from fastapi import APIRouter, Path, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import logging

from app.services.recommendation.popularity import get_popularity_recommendations
from app.services.ranking.score import rank_products
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


class RecommendResult(BaseModel):
    """Recommendation result model."""
    product_id: str
    score: float
    reason: Optional[str] = None


@router.get("/{user_id}", response_model=List[RecommendResult])
async def recommend(
    user_id: str = Path(..., description="User ID"),
    k: int = Query(10, ge=1, le=100, description="Number of recommendations to return")
):
    """
    Get product recommendations for a user with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    try:
        # Verify user exists
        client = get_supabase_client()
        if client:
            user_check = client.table("users").select("id").eq("id", user_id).limit(1).execute()
            if not user_check.data:
                logger.warning(f"User {user_id} not found, but continuing with recommendations")
        
        # Get candidates from recommendation service
        candidate_ids = get_popularity_recommendations(user_id=user_id, limit=k * 2)
        
        if not candidate_ids:
            logger.warning(f"No recommendations found for user {user_id}")
            return []
        
        # Convert to candidates format (product_id, search_score=0 for recommendations)
        candidates = [(product_id, 0.0) for product_id in candidate_ids]
        
        # Apply ranking (is_search=False for recommendations)
        try:
            ranked = rank_products(candidates, is_search=False, user_id=user_id)
            
            # Format results
            results = [
                RecommendResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
        except Exception as ranking_error:
            logger.warning(f"Ranking failed, falling back to popularity sort: {ranking_error}")
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
        
        logger.info(f"Recommendations for user {user_id} returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in recommend endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during recommendation")

