"""
Search endpoint for keyword search.

GET /search?q={query}&user_id={optional}&k={int}
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.services.search.keyword import search_keywords
from app.services.ranking.score import rank_products

logger = logging.getLogger(__name__)

router = APIRouter()


class SearchResult(BaseModel):
    """Search result model."""
    product_id: str
    score: float
    reason: Optional[str] = None


@router.get("", response_model=List[SearchResult])
async def search(
    q: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Optional user ID for personalization"),
    k: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """
    Search for products using keyword search with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    try:
        # Get candidates from search service
        candidates = search_keywords(q.strip(), limit=k * 2)
        
        if not candidates:
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
            logger.warning(f"Ranking failed, falling back to popularity sort: {ranking_error}")
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
        
        logger.info(f"Search query '{q}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during search")

