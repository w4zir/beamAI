"""
Feature retrieval for ranking service.

Fetches features needed for ranking:
- popularity_score from products table
- freshness_score computed on-demand
"""
from typing import Dict, List, Optional
from datetime import datetime
from app.core.logging import get_logger
from app.core.database import get_supabase_client
from app.core.tracing import get_tracer, set_span_attribute, record_exception, set_span_status, StatusCode
from app.services.features.freshness import compute_freshness_score_from_string

logger = get_logger(__name__)


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
    tracer = get_tracer()
    with tracer.start_as_current_span("features.fetch") as span:
        set_span_attribute("features.product_ids_count", len(product_ids))
        
        client = get_supabase_client()
        if not client:
            logger.error("feature_retrieval_db_connection_failed", product_ids_count=len(product_ids))
            set_span_status(StatusCode.ERROR, "Database connection failed")
            return {}
        
        try:
            # Fetch products with popularity_score and created_at
            with tracer.start_as_current_span("database.query") as db_span:
                set_span_attribute("db.query", "SELECT id, popularity_score, created_at FROM products")
                set_span_attribute("db.table", "products")
                
                response = client.table("products").select(
                    "id, popularity_score, created_at"
                ).in_("id", product_ids).execute()
                
                set_span_attribute("db.results_count", len(response.data) if response.data else 0)
            
            if not response.data:
                logger.warning(
                    "feature_retrieval_no_data",
                    product_ids_count=len(product_ids),
                )
                set_span_attribute("features.retrieved_count", 0)
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
            
            # Set span attributes
            set_span_attribute("features.retrieved_count", len(features))
            set_span_status(StatusCode.OK)
            
            logger.debug(
                "features_retrieved",
                requested_count=len(product_ids),
                retrieved_count=len(features),
            )
            return features
            
        except Exception as e:
            record_exception(e)
            set_span_status(StatusCode.ERROR, str(e))
            logger.error(
                "feature_retrieval_error",
                product_ids_count=len(product_ids),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return {}


def get_single_product_features(product_id: str) -> Optional[Dict[str, float]]:
    """
    Get features for a single product.
    
    Returns:
        Feature dict or None if product not found
    """
    features = get_product_features([product_id])
    return features.get(product_id)

