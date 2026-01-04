"""
Build FAISS index from product embeddings.

This script:
1. Loads all products from database
2. Generates embeddings for product descriptions (name + description)
3. Builds FAISS index (IndexFlatL2 for < 10K products, IndexIVFFlat for >= 10K)
4. Saves index and metadata to disk
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import configure_logging, get_logger
from app.core.database import get_supabase_client

# Configure logging
configure_logging(log_level="INFO", json_output=False)
logger = get_logger(__name__)

# Configuration
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
INDEX_VERSION = "1.0.0"
SMALL_DATASET_THRESHOLD = 10000  # Use IndexFlatL2 for < 10K products

# Default paths
DEFAULT_INDEX_DIR = Path(__file__).parent.parent / "data" / "indices"
DEFAULT_INDEX_PATH = DEFAULT_INDEX_DIR / "faiss_index.index"
DEFAULT_METADATA_PATH = DEFAULT_INDEX_DIR / "index_metadata.json"


def load_products() -> List[Dict]:
    """
    Load all products from database.
    
    Returns:
        List of product dictionaries with id, name, description, category
    """
    client = get_supabase_client()
    if not client:
        logger.error("build_index_db_connection_failed")
        return []
    
    try:
        logger.info("build_index_loading_products")
        response = client.table("products").select("id, name, description, category").execute()
        
        if not response.data:
            logger.warning("build_index_no_products")
            return []
        
        products = response.data
        logger.info(
            "build_index_products_loaded",
            count=len(products),
        )
        return products
        
    except Exception as e:
        logger.error(
            "build_index_load_products_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return []


def prepare_product_text(product: Dict) -> str:
    """
    Prepare text for embedding from product data.
    
    Combines name, description, and category into a single text string.
    
    Args:
        product: Product dictionary with name, description, category
        
    Returns:
        Combined text string for embedding
    """
    name = product.get("name", "").strip()
    description = product.get("description", "").strip()
    category = product.get("category", "").strip()
    
    # Combine fields with spaces
    parts = []
    if name:
        parts.append(name)
    if description:
        parts.append(description)
    if category:
        parts.append(category)
    
    text = " ".join(parts)
    
    # Handle empty text
    if not text:
        logger.warning(
            "build_index_empty_product_text",
            product_id=product.get("id", "unknown"),
            message="Product has no text content. Using placeholder.",
        )
        text = "product"  # Placeholder for empty products
    
    return text


def generate_embeddings(products: List[Dict], model: SentenceTransformer) -> Tuple[np.ndarray, List[str]]:
    """
    Generate embeddings for all products.
    
    Args:
        products: List of product dictionaries
        model: SentenceTransformer model
        
    Returns:
        Tuple of (embeddings array, product_ids list)
    """
    logger.info(
        "build_index_generating_embeddings",
        product_count=len(products),
    )
    
    start_time = time.time()
    
    # Prepare texts
    texts = []
    product_ids = []
    
    for product in products:
        product_id = product.get("id")
        if not product_id:
            logger.warning(
                "build_index_product_missing_id",
                product=product,
                message="Skipping product without ID.",
            )
            continue
        
        text = prepare_product_text(product)
        texts.append(text)
        product_ids.append(product_id)
    
    if not texts:
        logger.error("build_index_no_texts_to_embed")
        return np.array([]), []
    
    # Generate embeddings in batches (model handles batching internally)
    try:
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # Normalize for cosine similarity
            show_progress_bar=True,
        )
        
        generation_time = time.time() - start_time
        logger.info(
            "build_index_embeddings_generated",
            count=len(embeddings),
            time_seconds=round(generation_time, 2),
        )
        
        return embeddings, product_ids
        
    except Exception as e:
        logger.error(
            "build_index_embedding_generation_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return np.array([]), []


def build_faiss_index(embeddings: np.ndarray, product_count: int) -> faiss.Index:
    """
    Build FAISS index from embeddings.
    
    Args:
        embeddings: Numpy array of embeddings (N x EMBEDDING_DIM)
        product_count: Number of products
        
    Returns:
        FAISS index
    """
    logger.info(
        "build_index_building_faiss_index",
        product_count=product_count,
        embedding_dim=EMBEDDING_DIM,
    )
    
    start_time = time.time()
    
    # Choose index type based on dataset size
    if product_count < SMALL_DATASET_THRESHOLD:
        # IndexFlatL2: Exact search, faster for small datasets
        index_type = "IndexFlatL2"
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        logger.info(
            "build_index_using_flat_index",
            reason="Small dataset (< 10K products)",
        )
    else:
        # IndexIVFFlat: Approximate search, faster for large datasets
        index_type = "IndexIVFFlat"
        nlist = min(100, int(np.sqrt(product_count)))  # Number of clusters
        quantizer = faiss.IndexFlatL2(EMBEDDING_DIM)
        index = faiss.IndexIVFFlat(quantizer, EMBEDDING_DIM, nlist)
        
        # Train index (required for IVFFlat)
        logger.info("build_index_training_ivf_index")
        index.train(embeddings)
        
        logger.info(
            "build_index_using_ivf_index",
            nlist=nlist,
            reason="Large dataset (>= 10K products)",
        )
    
    # Add embeddings to index
    # Convert to float32 (required by FAISS)
    embeddings_float32 = embeddings.astype('float32')
    index.add(embeddings_float32)
    
    build_time = time.time() - start_time
    logger.info(
        "build_index_faiss_index_built",
        index_type=index_type,
        total_vectors=index.ntotal,
        build_time_seconds=round(build_time, 2),
    )
    
    return index, index_type


def save_index(index: faiss.Index, product_ids: List[str], index_type: str, index_path: Path, metadata_path: Path):
    """
    Save FAISS index and metadata to disk.
    
    Args:
        index: FAISS index
        product_ids: List of product IDs (in same order as index)
        index_type: Type of index (e.g., "IndexFlatL2")
        index_path: Path to save index file
        metadata_path: Path to save metadata JSON
    """
    # Create directory if it doesn't exist
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Save FAISS index
        logger.info("build_index_saving_faiss_index", path=str(index_path))
        faiss.write_index(index, str(index_path))
        
        # Build product_id mapping (index position -> product_id)
        product_id_mapping = {str(i): product_id for i, product_id in enumerate(product_ids)}
        
        # Create metadata
        metadata = {
            "version": INDEX_VERSION,
            "build_date": datetime.utcnow().isoformat() + "Z",
            "model_name": MODEL_NAME,
            "embedding_dim": EMBEDDING_DIM,
            "index_type": index_type,
            "total_products": len(product_ids),
            "product_id_mapping": product_id_mapping,
        }
        
        # Save metadata
        logger.info("build_index_saving_metadata", path=str(metadata_path))
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(
            "build_index_saved",
            index_path=str(index_path),
            metadata_path=str(metadata_path),
            total_products=len(product_ids),
        )
        
    except Exception as e:
        logger.error(
            "build_index_save_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


def main():
    """Main function to build FAISS index."""
    logger.info("build_index_started")
    
    # Load SentenceTransformer model
    logger.info("build_index_loading_model", model_name=MODEL_NAME)
    try:
        model = SentenceTransformer(MODEL_NAME)
        logger.info("build_index_model_loaded")
    except Exception as e:
        logger.error(
            "build_index_model_load_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        sys.exit(1)
    
    # Load products from database
    products = load_products()
    if not products:
        logger.error("build_index_no_products_to_index")
        sys.exit(1)
    
    # Generate embeddings
    embeddings, product_ids = generate_embeddings(products, model)
    if len(embeddings) == 0:
        logger.error("build_index_no_embeddings_generated")
        sys.exit(1)
    
    if len(embeddings) != len(product_ids):
        logger.error(
            "build_index_embedding_mismatch",
            embedding_count=len(embeddings),
            product_id_count=len(product_ids),
        )
        sys.exit(1)
    
    # Build FAISS index
    index, index_type = build_faiss_index(embeddings, len(product_ids))
    
    # Save index and metadata
    save_index(
        index=index,
        product_ids=product_ids,
        index_type=index_type,
        index_path=DEFAULT_INDEX_PATH,
        metadata_path=DEFAULT_METADATA_PATH,
    )
    
    logger.info(
        "build_index_completed",
        total_products=len(product_ids),
        index_path=str(DEFAULT_INDEX_PATH),
        metadata_path=str(DEFAULT_METADATA_PATH),
    )


if __name__ == "__main__":
    main()

