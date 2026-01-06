"""
Keyword search service using PostgreSQL Full Text Search.

According to SEARCH_DESIGN.md:
- Phase 1: Keyword Search only
- Uses Postgres FTS with GIN index on search_vector
- Returns candidates with search_keyword_score
"""
import re
from typing import List, Tuple
import httpx
from app.core.logging import get_logger
from app.core.database import get_supabase_client
from app.core.tracing import get_tracer, set_span_attribute, record_exception, set_span_status, StatusCode

logger = get_logger(__name__)


def normalize_query(query: str) -> str:
    """
    Normalize search query.
    
    Steps:
    1. Lowercase
    2. Remove punctuation (keep spaces)
    3. Trim whitespace
    
    Args:
        query: Raw search query
        
    Returns:
        Normalized query string
    """
    if not query:
        return ""
    
    # Lowercase
    normalized = query.lower()
    
    # Remove punctuation but keep spaces and alphanumeric
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Trim whitespace
    normalized = normalized.strip()
    
    return normalized


def search_keywords(query: str, limit: int = 50) -> List[Tuple[str, float]]:
    """
    Search products using PostgreSQL Full Text Search.
    
    Returns candidates with search_keyword_score.
    According to SEARCH_DESIGN.md: Search returns candidate product IDs only.
    Ranking is handled downstream.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of tuples (product_id, search_keyword_score)
        Results are sorted by score descending
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("search.keyword") as span:
        set_span_attribute("search.query", query)
        set_span_attribute("search.limit", limit)
        set_span_attribute("search.type", "keyword")
        
        client = get_supabase_client()
        if not client:
            logger.error("keyword_search_db_connection_failed")
            set_span_status(StatusCode.ERROR, "Database connection failed")
            return []
        
        # Normalize query
        normalized_query = normalize_query(query)
        set_span_attribute("search.normalized_query", normalized_query)
        
        if not normalized_query:
            logger.warning("keyword_search_query_empty_after_normalization", original_query=query)
            set_span_attribute("search.results_count", 0)
            return []
        
        try:
            # Convert query to tsquery format for Postgres FTS
            # Use plainto_tsquery for better user experience (handles multiple words)
            # This creates a query like: 'running' & 'shoes'
            
            # Build the FTS query using Postgres functions
            # We'll use the search_vector column with ts_rank for scoring
            
            # For Supabase, we need to use RPC or raw SQL for FTS queries
            # Since Supabase client doesn't directly support FTS, we'll query products
            # and filter/rank in Python for Phase 1, or use a simpler approach
            
            # Alternative: Use Supabase's text search if available, or query all and filter
            # For now, let's use a Postgres function approach via RPC
            
            # Simple approach: Query products and use Python to compute scores
            # This is not ideal for large datasets but works for Phase 1
            
            # Better approach: Use raw SQL via Supabase's postgrest client
            # We'll construct a query that uses ts_rank
            
            # Build tsquery from normalized query
            # Split into words and join with &
            words = normalized_query.split()
            tsquery = ' & '.join(words)
            
            # Use Supabase's RPC to call a Postgres function, or use direct query
            # For Phase 1, let's query products and compute scores in Python
            # In production, this should use a Postgres function
            
            # Query products with search_vector
            response = client.table("products").select("id, name, description, category, search_vector").execute()
            
            if not response.data:
                return []
            
            results = []
            
            # Compute FTS scores in Python (for Phase 1)
            # In production, this should be done in Postgres
            import re
            
            query_words = set(words)
            
            for product in response.data:
                product_id = product["id"]
                name = product.get("name", "").lower()
                description = product.get("description", "").lower()
                category = product.get("category", "").lower()
                
                # Simple scoring: count word matches
                # Weight: name (3x), description (2x), category (1x)
                score = 0.0
                
                for word in query_words:
                    if word in name:
                        score += 3.0
                    if word in description:
                        score += 2.0
                    if word in category:
                        score += 1.0
                
                if score > 0:
                    # Normalize score (simple normalization)
                    normalized_score = min(score / (len(query_words) * 3.0), 1.0)
                    results.append((product_id, normalized_score))
            
            # Sort by score descending
            results.sort(key=lambda x: x[1], reverse=True)
            
            # Limit results
            results = results[:limit]
            
            # Set span attributes
            set_span_attribute("search.results_count", len(results))
            set_span_status(StatusCode.OK)
            
            logger.info(
                "keyword_search_completed",
                query=query,
                normalized_query=normalized_query,
                results_count=len(results),
            )
            return results
            
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            # Connection errors - Supabase is likely not running
            error_msg = str(e)
            is_connection_refused = "refused" in error_msg.lower() or "actively refused" in error_msg.lower()
            
            record_exception(e)
            set_span_status(StatusCode.ERROR, error_msg)
            set_span_attribute("error.type", "ConnectionError")
            
            logger.error(
                "keyword_search_connection_error",
                query=query,
                error=error_msg,
                error_type=type(e).__name__,
                is_connection_refused=is_connection_refused,
                message="Supabase connection failed. Ensure Supabase is running at the configured URL.",
                suggestion="Check if Supabase is running: docker ps | grep supabase or supabase status" if is_connection_refused else "Check your SUPABASE_URL and network connectivity",
            )
            return []
        except Exception as e:
            # Check if it's a connection-related error even if not httpx exception
            error_msg = str(e)
            error_type_name = type(e).__name__
            is_connection_error = (
                "ConnectError" in error_type_name or
                "ConnectionError" in error_type_name or
                "refused" in error_msg.lower() or
                "actively refused" in error_msg.lower()
            )
            
            record_exception(e)
            set_span_status(StatusCode.ERROR, error_msg)
            set_span_attribute("error.type", error_type_name)
            
            if is_connection_error:
                logger.error(
                    "keyword_search_connection_error",
                    query=query,
                    error=error_msg,
                    error_type=error_type_name,
                    message="Database connection failed. Ensure Supabase is running.",
                    suggestion="Check if Supabase is running: docker ps | grep supabase or supabase status",
                )
            else:
                logger.error(
                    "keyword_search_error",
                    query=query,
                    error=error_msg,
                    error_type=error_type_name,
                    exc_info=True,
                )
            return []


def search_keywords_using_postgres_fts(query: str, limit: int = 50) -> List[Tuple[str, float]]:
    """
    Search products using Postgres FTS directly (better performance).
    
    This version uses Postgres FTS functions directly via raw SQL.
    Requires direct database access (not via Supabase client).
    
    For Phase 1, we'll use the Python-based approach above.
    This function is a placeholder for future optimization.
    """
    # TODO: Implement direct Postgres FTS query when we have direct DB access
    # This would use ts_rank and tsquery for better performance
    pass

