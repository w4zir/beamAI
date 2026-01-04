"""
Popularity-based recommendation service.

According to RECOMMENDATION_DESIGN.md:
- Baseline Models: Global popularity, Category-level popularity
- Cold Start Strategy: Popularity-based fallback
"""
from typing import List, Optional
from app.core.logging import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)


def get_popularity_recommendations(
    user_id: Optional[str] = None,
    limit: int = 10,
    category: Optional[str] = None
) -> List[str]:
    """
    Get product recommendations based on global popularity.
    
    Returns candidate product IDs ordered by popularity_score.
    According to RECOMMENDATION_DESIGN.md: Returns candidates only.
    Ranking is handled downstream.
    
    Args:
        user_id: Optional user ID (for future personalization)
        limit: Maximum number of recommendations
        category: Optional category filter
        
    Returns:
        List of product IDs ordered by popularity_score (descending)
    """
    client = get_supabase_client()
    if not client:
        logger.error("popularity_recommendations_db_connection_failed")
        return []
    
    try:
        # Build query
        query = client.table("products").select("id, popularity_score")
        
        # Filter by category if provided
        if category:
            query = query.eq("category", category)
        
        # Order by popularity_score descending
        query = query.order("popularity_score", desc=True)
        
        # Limit results
        query = query.limit(limit * 2)  # Get more candidates for ranking later
        
        response = query.execute()
        
        if not response.data:
            logger.warning(
                "popularity_recommendations_no_products",
                user_id=user_id,
                category=category,
            )
            return []
        
        # Extract product IDs
        product_ids = [product["id"] for product in response.data]
        
        logger.info(
            "popularity_recommendations_completed",
            user_id=user_id,
            category=category,
            candidates_count=len(product_ids),
        )
        return product_ids
        
    except Exception as e:
        logger.error(
            "popularity_recommendations_error",
            user_id=user_id,
            category=category,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return []


def get_category_recommendations(
    user_id: str,
    category: str,
    limit: int = 10
) -> List[str]:
    """
    Get category-level popularity recommendations.
    
    Args:
        user_id: User ID
        category: Product category
        limit: Maximum number of recommendations
        
    Returns:
        List of product IDs ordered by popularity_score within category
    """
    return get_popularity_recommendations(user_id=user_id, limit=limit, category=category)

