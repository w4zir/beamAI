"""
Semantic search service using FAISS and SentenceTransformers.

According to SEARCH_DESIGN.md:
- Phase 2: Semantic Search
- SentenceTransformers for embeddings
- FAISS for approximate nearest neighbor search
- Offline index build, in-memory load
"""
import os
import json
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.core.logging import get_logger
from app.core.database import get_supabase_client

logger = get_logger(__name__)

# Model configuration
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Default index paths
DEFAULT_INDEX_DIR = Path(__file__).parent.parent.parent.parent / "data" / "indices"
DEFAULT_INDEX_PATH = DEFAULT_INDEX_DIR / "faiss_index.index"
DEFAULT_METADATA_PATH = DEFAULT_INDEX_DIR / "index_metadata.json"


class SemanticSearchService:
    """
    Semantic search service using FAISS and SentenceTransformers.
    
    Handles:
    - Model loading (SentenceTransformers)
    - Index loading from disk
    - Query embedding generation
    - FAISS search execution
    - Score normalization (cosine similarity)
    """
    
    def __init__(self, index_path: Optional[str] = None, metadata_path: Optional[str] = None):
        """
        Initialize semantic search service.
        
        Args:
            index_path: Path to FAISS index file (default: backend/data/indices/faiss_index.index)
            metadata_path: Path to index metadata JSON (default: backend/data/indices/index_metadata.json)
        """
        self.index_path = Path(index_path) if index_path else DEFAULT_INDEX_PATH
        self.metadata_path = Path(metadata_path) if metadata_path else DEFAULT_METADATA_PATH
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.metadata: Optional[Dict] = None
        self.product_id_mapping: Dict[int, str] = {}  # index position -> product_id
        self._is_available = False
        
    def load_model(self) -> bool:
        """
        Load SentenceTransformers model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            logger.info(
                "semantic_model_loading",
                model_name=MODEL_NAME,
            )
            start_time = time.time()
            self.model = SentenceTransformer(MODEL_NAME)
            load_time_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "semantic_model_loaded",
                model_name=MODEL_NAME,
                load_time_ms=load_time_ms,
            )
            return True
        except Exception as e:
            logger.error(
                "semantic_model_load_failed",
                model_name=MODEL_NAME,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return False
    
    def load_index(self) -> bool:
        """
        Load FAISS index and metadata from disk.
        
        Returns:
            True if index loaded successfully, False otherwise
        """
        if not self.index_path.exists():
            logger.warning(
                "semantic_index_not_found",
                index_path=str(self.index_path),
                message="Semantic search will be disabled. Run build_faiss_index.py to create index.",
            )
            return False
        
        if not self.metadata_path.exists():
            logger.warning(
                "semantic_metadata_not_found",
                metadata_path=str(self.metadata_path),
                message="Index metadata not found. Index may be corrupted.",
            )
            return False
        
        try:
            logger.info(
                "semantic_index_loading",
                index_path=str(self.index_path),
            )
            start_time = time.time()
            
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_path))
            
            # Load metadata
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
            
            # Build product_id mapping (reverse: index position -> product_id)
            product_id_mapping = self.metadata.get("product_id_mapping", {})
            self.product_id_mapping = {
                int(k): v for k, v in product_id_mapping.items()
            }
            
            # Validate index dimensions
            expected_dim = self.metadata.get("embedding_dim", EMBEDDING_DIM)
            if self.index.d != expected_dim:
                logger.error(
                    "semantic_index_dimension_mismatch",
                    expected_dim=expected_dim,
                    actual_dim=self.index.d,
                    message="Index dimension mismatch. Rebuild index.",
                )
                self.index = None
                self.metadata = None
                return False
            
            load_time_ms = int((time.time() - start_time) * 1000)
            total_products = self.metadata.get("total_products", 0)
            
            logger.info(
                "semantic_index_loaded",
                index_path=str(self.index_path),
                total_products=total_products,
                index_type=self.metadata.get("index_type", "unknown"),
                load_time_ms=load_time_ms,
            )
            
            self._is_available = True
            return True
            
        except Exception as e:
            logger.error(
                "semantic_index_load_failed",
                index_path=str(self.index_path),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            self.index = None
            self.metadata = None
            return False
    
    def initialize(self) -> bool:
        """
        Initialize service: load model and index.
        
        Returns:
            True if both model and index loaded successfully, False otherwise
        """
        model_loaded = self.load_model()
        if not model_loaded:
            return False
        
        index_loaded = self.load_index()
        if not index_loaded:
            logger.warning(
                "semantic_search_partially_available",
                message="Model loaded but index not available. Semantic search disabled.",
            )
            return False
        
        return True
    
    def is_available(self) -> bool:
        """
        Check if semantic search is ready.
        
        Returns:
            True if both model and index are loaded, False otherwise
        """
        return self._is_available and self.model is not None and self.index is not None
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text using SentenceTransformers.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector (384-dim) or None if generation fails
        """
        if not self.model:
            logger.error(
                "semantic_embedding_model_not_loaded",
                message="Model not loaded. Cannot generate embedding.",
            )
            return None
        
        if not text or not text.strip():
            logger.warning(
                "semantic_embedding_empty_text",
                message="Empty text provided for embedding generation.",
            )
            return None
        
        try:
            start_time = time.time()
            # Generate embedding (returns numpy array)
            embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.debug(
                "semantic_embedding_generated",
                text_length=len(text),
                latency_ms=latency_ms,
            )
            
            return embedding
            
        except Exception as e:
            logger.error(
                "semantic_embedding_generation_failed",
                text_length=len(text) if text else 0,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None
    
    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Search for products using semantic similarity.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of (product_id, search_semantic_score) tuples, sorted by score descending
            Returns empty list if search fails or service is not available
        """
        if not self.is_available():
            logger.warning(
                "semantic_search_not_available",
                query=query,
                message="Semantic search service not available. Returning empty results.",
            )
            return []
        
        if not query or not query.strip():
            logger.warning(
                "semantic_search_empty_query",
                message="Empty query provided for semantic search.",
            )
            return []
        
        try:
            start_time = time.time()
            
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            if query_embedding is None:
                logger.warning(
                    "semantic_search_embedding_failed",
                    query=query,
                    message="Failed to generate query embedding. Returning empty results.",
                )
                return []
            
            # Reshape for FAISS (1 x embedding_dim)
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            
            # Search FAISS index
            search_start = time.time()
            k = min(top_k, self.index.ntotal)  # Don't search for more than available
            distances, indices = self.index.search(query_embedding, k)
            search_latency_ms = int((time.time() - search_start) * 1000)
            
            # Convert distances to similarity scores (cosine similarity)
            # FAISS L2 distance: smaller distance = higher similarity
            # Convert to similarity: similarity = 1 / (1 + distance)
            # Since we normalized embeddings, L2 distance can be converted to cosine similarity
            # For normalized vectors: cosine_sim = 1 - (distance^2 / 2)
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for invalid results
                    continue
                
                # Convert L2 distance to cosine similarity
                # For normalized vectors: cosine_sim = 1 - (distance^2 / 2)
                # Clamp to [0, 1] range
                cosine_similarity = max(0.0, min(1.0, 1.0 - (distance ** 2) / 2.0))
                
                # Get product_id from mapping
                product_id = self.product_id_mapping.get(int(idx))
                if not product_id:
                    logger.warning(
                        "semantic_search_product_id_missing",
                        index_position=int(idx),
                        message="Product ID not found in mapping. Skipping result.",
                    )
                    continue
                
                results.append((product_id, float(cosine_similarity)))
            
            total_latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "semantic_search_completed",
                query=query,
                results_count=len(results),
                top_k=top_k,
                search_latency_ms=search_latency_ms,
                total_latency_ms=total_latency_ms,
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "semantic_search_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return []


# Global singleton instance
_semantic_search_service: Optional[SemanticSearchService] = None


def get_semantic_search_service() -> Optional[SemanticSearchService]:
    """
    Get global semantic search service instance.
    
    Returns:
        SemanticSearchService instance or None if not initialized
    """
    return _semantic_search_service


def initialize_semantic_search(index_path: Optional[str] = None, metadata_path: Optional[str] = None) -> bool:
    """
    Initialize global semantic search service.
    
    Args:
        index_path: Optional path to FAISS index file
        metadata_path: Optional path to index metadata JSON
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _semantic_search_service
    
    _semantic_search_service = SemanticSearchService(index_path=index_path, metadata_path=metadata_path)
    success = _semantic_search_service.initialize()
    
    if success:
        logger.info("semantic_search_initialized")
    else:
        logger.warning("semantic_search_initialization_failed")
    
    return success

