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
    
    Args:
        scores: Dictionary mapping product_id to popularity_score
        
    Returns:
        Number of products updated
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return 0
    
    updated = 0
    
    # Update in batches for better performance
    batch_size = 50
    product_ids = list(scores.keys())
    
    for i in range(0, len(product_ids), batch_size):
        batch_ids = product_ids[i:i + batch_size]
        batch_updates = []
        
        for product_id in batch_ids:
            batch_updates.append({
                "id": product_id,
                "popularity_score": scores[product_id]
            })
        
        try:
            # Use upsert to update existing products
            response = client.table("products").upsert(
                batch_updates,
                on_conflict="id"
            ).execute()
            updated += len(batch_updates)
        except Exception as e:
            logger.error(f"Error updating batch {i//batch_size + 1}: {e}")
    
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

