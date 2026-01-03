"""
Compute popularity_score for products based on weighted event counts.

According to FEATURE_DEFINITIONS.md:
- Weighted count: purchase=3, add_to_cart=2, view=1
- Computed: Offline batch
"""
import logging
from typing import Dict, List
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

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
        logger.error("Failed to get Supabase client")
        return {}
    
    try:
        # Get all events grouped by product_id and event_type
        events_response = client.table("events").select("product_id, event_type").execute()
        
        if not events_response.data:
            logger.warning("No events found in database")
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
        
        logger.info(f"Computed popularity scores for {len(product_scores)} products")
        return product_scores
        
    except Exception as e:
        logger.error(f"Error computing popularity scores: {e}", exc_info=True)
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
        logger.error("Failed to get Supabase client")
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
            logger.warning(f"Skipping {len(missing_products)} product(s) referenced in events but not in products table: {list(missing_products)[:5]}...")
        
        if not valid_scores:
            logger.warning("No valid products to update")
            return 0
        
    except Exception as e:
        logger.error(f"Error checking existing products: {e}", exc_info=True)
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
            logger.error(f"Error updating batch {i//batch_size + 1}: {e}", exc_info=True)
    
    logger.info(f"Updated popularity_score for {updated} products")
    return updated


def compute_and_update_popularity_scores() -> int:
    """
    Compute popularity scores and update the database.
    
    Returns:
        Number of products updated
    """
    logger.info("Starting popularity score computation...")
    scores = compute_popularity_scores()
    
    if not scores:
        logger.warning("No scores computed, skipping update")
        return 0
    
    updated = update_popularity_scores_in_db(scores)
    logger.info(f"Popularity score computation completed. Updated {updated} products.")
    return updated

