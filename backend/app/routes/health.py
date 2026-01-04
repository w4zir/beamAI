"""
Health check endpoint.
"""
from fastapi import APIRouter

from app.core.logging import get_logger
from app.services.search.semantic import get_semantic_search_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "ok",
        "message": "API is running"
    }


@router.get("/semantic")
async def semantic_search_health():
    """
    Health check endpoint for semantic search index.
    
    Returns:
        Status of semantic search service including:
        - availability: whether semantic search is available
        - index_loaded: whether FAISS index is loaded
        - model_loaded: whether embedding model is loaded
        - total_products: number of products in index
        - index_memory_bytes: approximate memory usage of index
    """
    semantic_service = get_semantic_search_service()
    
    if not semantic_service:
        return {
            "status": "unavailable",
            "available": False,
            "index_loaded": False,
            "model_loaded": False,
            "message": "Semantic search service not initialized"
        }
    
    is_available = semantic_service.is_available()
    index_loaded = semantic_service.index is not None
    model_loaded = semantic_service.model is not None
    
    response = {
        "status": "ok" if is_available else "unavailable",
        "available": is_available,
        "index_loaded": index_loaded,
        "model_loaded": model_loaded,
    }
    
    if index_loaded and semantic_service.metadata:
        response["total_products"] = semantic_service.metadata.get("total_products", 0)
        response["index_type"] = semantic_service.metadata.get("index_type", "unknown")
        response["index_version"] = semantic_service.metadata.get("version", "unknown")
        response["build_date"] = semantic_service.metadata.get("build_date", "unknown")
        
        # Calculate memory usage
        index_memory_bytes = semantic_service._calculate_index_memory()
        response["index_memory_bytes"] = index_memory_bytes
    
    if not is_available:
        if not model_loaded:
            response["message"] = "Embedding model not loaded"
        elif not index_loaded:
            response["message"] = "FAISS index not loaded. Run build_faiss_index.py to create index."
        else:
            response["message"] = "Semantic search service unavailable"
    else:
        response["message"] = "Semantic search is ready"
    
    return response

