"""
Hybrid search service combining keyword and semantic search.

According to RANKING_LOGIC.md:
- For search queries: search_score = max(search_keyword_score, search_semantic_score)
- This ensures the best match (whether exact keyword or semantic similarity) is emphasized
"""
import time
from typing import List, Tuple
from app.core.logging import get_logger
from app.core.tracing import get_tracer, set_span_attribute, record_exception, set_span_status, StatusCode
from app.services.search.keyword import search_keywords
from app.services.search.semantic import get_semantic_search_service

logger = get_logger(__name__)


def hybrid_search(query: str, limit: int = 50) -> List[Tuple[str, float]]:
    """
    Perform hybrid search combining keyword and semantic search.
    
    Merges results using max(keyword_score, semantic_score) per product.
    If one search type fails, falls back to the other.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of (product_id, max_score) tuples, sorted by score descending
        max_score = max(keyword_score, semantic_score) per RANKING_LOGIC.md
    """
    tracer = get_tracer()
    with tracer.start_as_current_span("search.hybrid") as span:
        set_span_attribute("search.query", query)
        set_span_attribute("search.limit", limit)
        set_span_attribute("search.type", "hybrid")
        
        start_time = time.time()
        
        # Get semantic search service
        semantic_service = get_semantic_search_service()
        semantic_available = semantic_service and semantic_service.is_available()
        set_span_attribute("search.semantic_available", semantic_available)
        
        # Perform keyword search
        keyword_start = time.time()
        keyword_results = search_keywords(query, limit=limit * 2)  # Get more candidates for merging
        keyword_latency_ms = int((time.time() - keyword_start) * 1000)
        set_span_attribute("search.keyword_latency_ms", keyword_latency_ms)
        set_span_attribute("search.keyword_results_count", len(keyword_results))
        
        # Perform semantic search if available
        semantic_results = []
        semantic_latency_ms = 0
        if semantic_available:
            try:
                semantic_start = time.time()
                semantic_results = semantic_service.search(query, top_k=limit * 2)
                semantic_latency_ms = int((time.time() - semantic_start) * 1000)
                set_span_attribute("search.semantic_latency_ms", semantic_latency_ms)
                set_span_attribute("search.semantic_results_count", len(semantic_results))
            except Exception as e:
                record_exception(e)
                logger.warning(
                    "hybrid_search_semantic_failed",
                    query=query,
                    error=str(e),
                    error_type=type(e).__name__,
                    message="Falling back to keyword search only.",
                )
                semantic_results = []
        
        # Merge results: max(keyword_score, semantic_score) per product
        merged_scores: dict[str, float] = {}
        
        # Add keyword scores
        for product_id, keyword_score in keyword_results:
            merged_scores[product_id] = keyword_score
        
        # Merge semantic scores (take max)
        for product_id, semantic_score in semantic_results:
            if product_id in merged_scores:
                # Use max of keyword and semantic scores
                merged_scores[product_id] = max(merged_scores[product_id], semantic_score)
            else:
                # Product only in semantic results
                merged_scores[product_id] = semantic_score
        
        # Convert to list and sort by score descending
        merged_results = [
            (product_id, score)
            for product_id, score in merged_scores.items()
        ]
        merged_results.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        merged_results = merged_results[:limit]
        
        total_latency_ms = int((time.time() - start_time) * 1000)
        
        # Set span attributes
        keyword_count = len(keyword_results)
        semantic_count = len(semantic_results)
        merged_count = len(merged_results)
        overlap_count = len(set(p[0] for p in keyword_results) & set(p[0] for p in semantic_results))
        
        set_span_attribute("search.results_count", merged_count)
        set_span_attribute("search.overlap_count", overlap_count)
        set_span_attribute("search.total_latency_ms", total_latency_ms)
        set_span_status(StatusCode.OK)
        
        # Log metrics
        logger.info(
            "hybrid_search_completed",
            query=query,
            keyword_results=keyword_count,
            semantic_results=semantic_count,
            merged_results=merged_count,
            overlap=overlap_count,
            keyword_latency_ms=keyword_latency_ms,
            semantic_latency_ms=semantic_latency_ms,
            total_latency_ms=total_latency_ms,
            semantic_available=semantic_available,
        )
        
        return merged_results

