"""
Compute popularity_score for products based on weighted event counts.

According to FEATURE_DEFINITIONS.md:
- Weighted count: purchase=3, add_to_cart=2, view=1
- Computed: Offline batch
"""
from typing import Dict, List
from app.core.logging import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)

# Event type weights as per specification
EVENT_WEIGHTS = {
    "purchase": 3.0,
    "add_to_cart": 2.0,
    "view": 1.0
}


def compute_popularity_scores() -> Dict[str, float]:
    """
    Compute popularity scores for all products based on weighted event counts.
    
    Returns:
        Dictionary mapping product_id to popularity_score
    """
    client = get_supabase_client()
    if not client:
        logger.error("popularity_computation_db_connection_failed")
        return {}
    
    try:
        # Get all events grouped by product_id and event_type
        events_response = client.table("events").select("product_id, event_type").execute()
        
        if not events_response.data:
            logger.warning("popularity_computation_no_events")
            return {}
        
        # Aggregate scores by product
        product_scores: Dict[str, float] = {}
        
        for event in events_response.data:
            product_id = event["product_id"]
            event_type = event["event_type"]
            weight = EVENT_WEIGHTS.get(event_type, 0.0)
            
            if product_id not in product_scores:
                product_scores[product_id] = 0.0
            
            product_scores[product_id] += weight
        
        # Normalize scores (optional: can be adjusted based on business needs)
        # For now, we'll use raw weighted counts
        
        logger.info(
            "popularity_scores_computed",
            products_count=len(product_scores),
            events_count=len(events_response.data),
        )
        return product_scores
        
    except Exception as e:
        logger.error(
            "popularity_computation_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return {}


def update_popularity_scores_in_db(scores: Dict[str, float]) -> int:
    """
    Update popularity_score in products table.
    Only updates existing products (does not create new ones).
    
    Args:
        scores: Dictionary mapping product_id to popularity_score
        
    Returns:
        Number of products updated
    """
    client = get_supabase_client()
    if not client:
        logger.error("popularity_update_db_connection_failed")
        return 0
    
    if not scores:
        return 0
    
    # First, verify which products exist in the database
    try:
        product_ids_list = list(scores.keys())
        # Query existing products
        existing_response = client.table("products").select("id").in_("id", product_ids_list).execute()
        existing_product_ids = {row["id"] for row in existing_response.data}
        
        # Filter scores to only include existing products
        valid_scores = {pid: score for pid, score in scores.items() if pid in existing_product_ids}
        
        missing_products = set(product_ids_list) - existing_product_ids
        if missing_products:
            logger.warning(
                "popularity_update_missing_products",
                missing_count=len(missing_products),
                sample_missing=list(missing_products)[:5],
            )
        
        if not valid_scores:
            logger.warning("popularity_update_no_valid_products")
            return 0
        
    except Exception as e:
        logger.error(
            "popularity_update_check_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return 0
    
    updated = 0
    
    # Update in batches for better performance
    batch_size = 50
    valid_product_ids = list(valid_scores.keys())
    
    for i in range(0, len(valid_product_ids), batch_size):
        batch_ids = valid_product_ids[i:i + batch_size]
        
        try:
            # Update each product in the batch
            # Note: Supabase PostgREST doesn't support bulk updates with different values per row
            # So we update them individually, but batch the database calls
            for product_id in batch_ids:
                response = client.table("products").update({
                    "popularity_score": valid_scores[product_id]
                }).eq("id", product_id).execute()
                
                if response.data:
                    updated += 1
                    
        except Exception as e:
            logger.error(
                "popularity_update_batch_error",
                batch_number=i//batch_size + 1,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
    
    logger.info(
        "popularity_scores_updated",
        updated_count=updated,
        total_count=len(valid_scores),
    )
    return updated


def compute_and_update_popularity_scores() -> int:
    """
    Compute popularity scores and update the database.
    
    Returns:
        Number of products updated
    """
    logger.info("popularity_computation_started")
    scores = compute_popularity_scores()
    
    if not scores:
        logger.warning("popularity_computation_no_scores")
        return 0
    
    updated = update_popularity_scores_in_db(scores)
    logger.info(
        "popularity_computation_completed",
        updated_count=updated,
    )
    return updated

