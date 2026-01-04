"""
Ranking service implementing Phase 1 formula.

According to RANKING_LOGIC.md Phase 1:
final_score = (
    0.4 * search_score +
    0.3 * cf_score +
    0.2 * popularity_score +
    0.1 * freshness_score
)

For search: search_score = max(search_keyword_score, search_semantic_score)
  - Hybrid search already computes max(keyword_score, semantic_score) per RANKING_LOGIC.md
  - This service receives the merged search_score from hybrid search
For recommendations: search_score = 0
cf_score: Uses collaborative filtering scores when available (Phase 3.2), otherwise 0.0
"""
from typing import List, Tuple, Dict, Optional
from app.core.logging import get_logger
from app.services.ranking.features import get_product_features
from app.services.recommendation.collaborative import get_collaborative_filtering_service

logger = get_logger(__name__)

# Phase 1 weights (global)
WEIGHTS = {
    "search_score": 0.4,
    "cf_score": 0.3,
    "popularity_score": 0.2,
    "freshness_score": 0.1
}


def compute_final_score(
    search_score: float,
    cf_score: float,
    popularity_score: float,
    freshness_score: float
) -> float:
    """
    Compute final ranking score using Phase 1 formula.
    
    Args:
        search_score: Search relevance score (0 for recommendations)
        cf_score: Collaborative filtering score (0 in Phase 1)
        popularity_score: Product popularity score
        freshness_score: Product freshness score
        
    Returns:
        Final ranking score
    """
    final_score = (
        WEIGHTS["search_score"] * search_score +
        WEIGHTS["cf_score"] * cf_score +
        WEIGHTS["popularity_score"] * popularity_score +
        WEIGHTS["freshness_score"] * freshness_score
    )
    
    return final_score


def rank_products(
    candidates: List[Tuple[str, float]],
    is_search: bool = True,
    user_id: Optional[str] = None
) -> List[Tuple[str, float, Dict[str, float]]]:
    """
    Rank products using Phase 1 formula.
    
    Args:
        candidates: List of (product_id, search_score) tuples
          - For search: search_score is max(keyword_score, semantic_score) from hybrid search
          - For recommendations: search_score is 0
        is_search: True if this is a search query, False if recommendations
        user_id: Optional user ID (for future personalization)
        
    Returns:
        List of (product_id, final_score, breakdown) tuples, sorted by final_score descending
        breakdown contains individual feature scores for explainability
    """
    if not candidates:
        logger.info(
            "ranking_started",
            is_search=is_search,
            user_id=user_id,
            candidates_count=0,
        )
        return []
    
    logger.info(
        "ranking_started",
        is_search=is_search,
        user_id=user_id,
        candidates_count=len(candidates),
        weights=WEIGHTS,
    )
    
    # Extract product IDs and search scores
    product_ids = [product_id for product_id, _ in candidates]
    search_scores = {product_id: score for product_id, score in candidates}
    
    # Get product features
    features = get_product_features(product_ids)
    
    if not features:
        logger.warning(
            "ranking_no_features",
            is_search=is_search,
            user_id=user_id,
            candidates_count=len(candidates),
        )
        # Fallback: return candidates sorted by search_score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [
            (product_id, score, {"search_score": score, "cf_score": 0.0, "popularity_score": 0.0, "freshness_score": 0.0})
            for product_id, score in candidates
        ]
    
    # Get CF scores if user_id provided and CF service available
    cf_scores: Dict[str, float] = {}
    cf_service = get_collaborative_filtering_service()
    if user_id and cf_service and cf_service.is_available():
        try:
            cf_scores = cf_service.compute_user_product_affinities(user_id, product_ids)
            logger.debug(
                "ranking_cf_scores_computed",
                user_id=user_id,
                products_count=len(cf_scores),
            )
        except Exception as e:
            logger.warning(
                "ranking_cf_computation_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                message="Falling back to cf_score=0.0",
            )
            cf_scores = {}
    
    # Compute final scores
    ranked_results = []
    
    for product_id, search_score in candidates:
        if product_id not in features:
            logger.warning(
                "ranking_product_features_missing",
                product_id=product_id,
                is_search=is_search,
                user_id=user_id,
            )
            continue
        
        product_features = features[product_id]
        popularity_score = product_features.get("popularity_score", 0.0)
        freshness_score = product_features.get("freshness_score", 0.0)
        
        # For recommendations, search_score is 0
        if not is_search:
            search_score = 0.0
        
        # Get CF score (0.0 if not available)
        cf_score = cf_scores.get(product_id, 0.0)
        
        # Compute final score
        final_score = compute_final_score(
            search_score=search_score,
            cf_score=cf_score,
            popularity_score=popularity_score,
            freshness_score=freshness_score
        )
        
        # Create breakdown for explainability
        breakdown = {
            "search_score": search_score,
            "cf_score": cf_score,
            "popularity_score": popularity_score,
            "freshness_score": freshness_score
        }
        
        # Log ranking for each product
        logger.debug(
            "ranking_product_scored",
            product_id=product_id,
            final_score=final_score,
            score_breakdown=breakdown,
            feature_values={
                "popularity_score": popularity_score,
                "freshness_score": freshness_score,
                "cf_score": cf_score,
            },
            is_search=is_search,
            user_id=user_id,
        )
        
        ranked_results.append((product_id, final_score, breakdown))
    
    # Sort by final_score descending
    ranked_results.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(
        "ranking_completed",
        is_search=is_search,
        user_id=user_id,
        ranked_count=len(ranked_results),
        candidates_count=len(candidates),
    )
    
    return ranked_results

