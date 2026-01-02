"""
Feature retrieval for ranking service.

Fetches features needed for ranking:
- popularity_score from products table
- freshness_score computed on-demand
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.core.database import get_supabase_client
from app.services.features.freshness import compute_freshness_score_from_string

logger = logging.getLogger(__name__)


def get_product_features(product_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get features for a list of products.
    
    Returns:
        Dictionary mapping product_id to feature dict:
        {
            "popularity_score": float,
            "freshness_score": float
        }
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return {}
    
    try:
        # Fetch products with popularity_score and created_at
        response = client.table("products").select(
            "id, popularity_score, created_at"
        ).in_("id", product_ids).execute()
        
        if not response.data:
            return {}
        
        features = {}
        
        for product in response.data:
            product_id = product["id"]
            popularity_score = product.get("popularity_score", 0.0) or 0.0
            created_at = product.get("created_at")
            
            # Compute freshness score
            freshness_score = 0.0
            if created_at:
                freshness_score = compute_freshness_score_from_string(created_at)
            
            features[product_id] = {
                "popularity_score": float(popularity_score),
                "freshness_score": freshness_score
            }
        
        logger.debug(f"Retrieved features for {len(features)} products")
        return features
        
    except Exception as e:
        logger.error(f"Error retrieving product features: {e}", exc_info=True)
        return {}


def get_single_product_features(product_id: str) -> Optional[Dict[str, float]]:
    """
    Get features for a single product.
    
    Returns:
        Feature dict or None if product not found
    """
    features = get_product_features([product_id])
    return features.get(product_id)

