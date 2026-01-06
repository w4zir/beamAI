"""
Train collaborative filtering model using Implicit ALS.

This script:
1. Extracts user-product interactions from events table
2. Builds sparse interaction matrix
3. Trains Implicit ALS model
4. Saves model artifacts (user_factors, item_factors, mappings, metadata)
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional

import numpy as np
from scipy.sparse import csr_matrix
import implicit

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import configure_logging, get_logger
from app.services.recommendation.collaborative import (
    extract_user_product_interactions,
    build_interaction_matrix,
    validate_interaction_matrix,
    DEFAULT_MODEL_DIR,
    DEFAULT_USER_FACTORS_PATH,
    DEFAULT_ITEM_FACTORS_PATH,
    DEFAULT_USER_MAPPING_PATH,
    DEFAULT_PRODUCT_MAPPING_PATH,
    DEFAULT_METADATA_PATH,
    MODEL_VERSION,
    DEFAULT_FACTORS,
    DEFAULT_REGULARIZATION,
    DEFAULT_ITERATIONS,
    DEFAULT_ALPHA,
)

# Configure logging
configure_logging(log_level="INFO", json_output=False)
logger = get_logger(__name__)


def train_als_model(
    matrix: csr_matrix,
    factors: int = DEFAULT_FACTORS,
    regularization: float = DEFAULT_REGULARIZATION,
    iterations: int = DEFAULT_ITERATIONS,
    alpha: float = DEFAULT_ALPHA,
) -> implicit.als.AlternatingLeastSquares:
    """
    Train Implicit ALS model.
    
    Args:
        matrix: Sparse interaction matrix (CSR format)
        factors: Number of latent factors
        regularization: L2 regularization parameter
        iterations: Number of ALS iterations
        alpha: Confidence scaling for implicit feedback
        
    Returns:
        Trained ALS model
    """
    logger.info(
        "cf_training_started",
        factors=factors,
        regularization=regularization,
        iterations=iterations,
        alpha=alpha,
        matrix_shape=matrix.shape,
        num_interactions=matrix.nnz,
    )
    
    start_time = time.time()
    
    # Initialize model
    model = implicit.als.AlternatingLeastSquares(
        factors=factors,
        regularization=regularization,
        iterations=iterations,
        alpha=alpha,
        random_state=42,  # For reproducibility
    )
    
    # Train model
    # Note: implicit expects item-user matrix (transpose)
    model.fit(matrix.T)
    
    training_time = time.time() - start_time
    
    logger.info(
        "cf_training_completed",
        training_time_seconds=training_time,
        factors=factors,
    )
    
    return model


def save_model_artifacts(
    model: implicit.als.AlternatingLeastSquares,
    user_id_to_index: Dict[str, int],
    product_id_to_index: Dict[str, int],
    matrix: csr_matrix,
    factors: int,
    regularization: float,
    iterations: int,
    alpha: float,
    user_factors_path: Path = DEFAULT_USER_FACTORS_PATH,
    item_factors_path: Path = DEFAULT_ITEM_FACTORS_PATH,
    user_mapping_path: Path = DEFAULT_USER_MAPPING_PATH,
    product_mapping_path: Path = DEFAULT_PRODUCT_MAPPING_PATH,
    metadata_path: Path = DEFAULT_METADATA_PATH,
) -> None:
    """
    Save model artifacts to disk.
    
    Args:
        model: Trained ALS model
        user_id_to_index: User ID to matrix index mapping
        product_id_to_index: Product ID to matrix index mapping
        matrix: Interaction matrix (for metadata)
        factors: Model parameters
        regularization: Model parameters
        iterations: Model parameters
        alpha: Model parameters
        user_factors_path: Path to save user factors
        item_factors_path: Path to save item factors
        user_mapping_path: Path to save user mapping
        product_mapping_path: Path to save product mapping
        metadata_path: Path to save metadata
    """
    # Create directory if it doesn't exist
    user_factors_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("cf_saving_model_artifacts")
        
        # Save factor matrices
        # Note: We fit on matrix.T (transpose), so implicit treats:
        # - Rows of matrix.T (products) as users -> model.user_factors
        # - Columns of matrix.T (users) as items -> model.item_factors
        # But semantically we want:
        # - user_factors for users (columns of matrix.T) -> model.item_factors
        # - item_factors for products (rows of matrix.T) -> model.user_factors
        # So we need to swap them when saving
        user_factors = model.item_factors  # columns of matrix.T = users
        item_factors = model.user_factors   # rows of matrix.T = products
        
        np.save(user_factors_path, user_factors)
        np.save(item_factors_path, item_factors)
        
        logger.info(
            "cf_factors_saved",
            user_factors_shape=user_factors.shape,
            item_factors_shape=item_factors.shape,
        )
        
        # Save mappings (convert int keys to strings for JSON)
        user_mapping_json = {str(k): int(v) for k, v in user_id_to_index.items()}
        product_mapping_json = {str(k): int(v) for k, v in product_id_to_index.items()}
        
        with open(user_mapping_path, 'w') as f:
            json.dump(user_mapping_json, f, indent=2)
        
        with open(product_mapping_path, 'w') as f:
            json.dump(product_mapping_json, f, indent=2)
        
        logger.info(
            "cf_mappings_saved",
            num_users=len(user_mapping_json),
            num_products=len(product_mapping_json),
        )
        
        # Calculate sparsity
        sparsity = 1.0 - (matrix.nnz / (matrix.shape[0] * matrix.shape[1]))
        
        # Create metadata
        metadata = {
            "version": MODEL_VERSION,
            "training_date": datetime.utcnow().isoformat() + "Z",
            "model_type": "ImplicitALS",
            "parameters": {
                "factors": factors,
                "regularization": regularization,
                "iterations": iterations,
                "alpha": alpha,
            },
            "training_metrics": {
                "num_users": matrix.shape[0],
                "num_products": matrix.shape[1],
                "num_interactions": matrix.nnz,
                "sparsity": sparsity,
            },
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(
            "cf_model_saved",
            user_factors_path=str(user_factors_path),
            item_factors_path=str(item_factors_path),
            user_mapping_path=str(user_mapping_path),
            product_mapping_path=str(product_mapping_path),
            metadata_path=str(metadata_path),
        )
        
    except Exception as e:
        logger.error(
            "cf_model_save_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


def validate_model(
    model: implicit.als.AlternatingLeastSquares,
    matrix: csr_matrix
) -> bool:
    """
    Validate trained model.
    
    Args:
        model: Trained ALS model
        matrix: Interaction matrix (user-product matrix)
        
    Returns:
        True if model is valid, False otherwise
    """
    try:
        # Note: model.fit() was called with matrix.T (transpose)
        # implicit treats rows as users and columns as items
        # So after transpose: matrix.T has shape (num_products, num_users)
        # - model.user_factors corresponds to rows of matrix.T (products)
        # - model.item_factors corresponds to columns of matrix.T (users)
        # Validation checks dimensions before we swap them during save
        
        # Check that user_factors match number of products (rows of transposed matrix)
        if model.user_factors.shape[0] != matrix.shape[1]:
            logger.error(
                "cf_model_validation_failed",
                reason="user_factors_dimension_mismatch",
                expected=matrix.shape[1],
                actual=model.user_factors.shape[0],
            )
            return False
        
        # Check that item_factors match number of users (columns of transposed matrix)
        if model.item_factors.shape[0] != matrix.shape[0]:
            logger.error(
                "cf_model_validation_failed",
                reason="item_factors_dimension_mismatch",
                expected=matrix.shape[0],
                actual=model.item_factors.shape[0],
            )
            return False
        
        # Check that factors are consistent
        if model.user_factors.shape[1] != model.item_factors.shape[1]:
            logger.error(
                "cf_model_validation_failed",
                reason="factor_dimension_mismatch",
                user_factors_dim=model.user_factors.shape[1],
                item_factors_dim=model.item_factors.shape[1],
            )
            return False
        
        logger.info("cf_model_validation_passed")
        return True
        
    except Exception as e:
        logger.error(
            "cf_model_validation_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return False


def main(
    days_back: Optional[int] = 90,
    factors: int = DEFAULT_FACTORS,
    regularization: float = DEFAULT_REGULARIZATION,
    iterations: int = DEFAULT_ITERATIONS,
    alpha: float = DEFAULT_ALPHA,
    min_interactions: int = 1,
    min_matrix_users: int = 10,
    min_matrix_products: int = 10,
    min_matrix_interactions: int = 100,
):
    """
    Main function to train CF model.
    
    Args:
        days_back: Number of days to look back for interactions (None for all time)
        factors: Number of latent factors
        regularization: L2 regularization parameter
        iterations: Number of ALS iterations
        alpha: Confidence scaling for implicit feedback
        min_interactions: Minimum interactions per user-product pair
        min_matrix_users: Minimum number of users required for matrix validation
        min_matrix_products: Minimum number of products required for matrix validation
        min_matrix_interactions: Minimum number of interactions required for matrix validation
    """
    logger.info("cf_training_pipeline_started")
    
    start_time = time.time()
    
    # Extract interactions
    logger.info("cf_extracting_interactions", days_back=days_back)
    interactions = extract_user_product_interactions(
        days_back=days_back,
        min_interactions=min_interactions,
    )
    
    if not interactions:
        logger.error("cf_training_no_interactions")
        sys.exit(1)
    
    # Build interaction matrix
    logger.info("cf_building_matrix")
    matrix, user_id_to_index, product_id_to_index = build_interaction_matrix(interactions)
    
    # Validate matrix
    if not validate_interaction_matrix(
        matrix,
        min_users=min_matrix_users,
        min_products=min_matrix_products,
        min_interactions=min_matrix_interactions,
    ):
        logger.error("cf_training_matrix_validation_failed")
        sys.exit(1)
    
    # Train model
    logger.info("cf_training_model")
    model = train_als_model(
        matrix=matrix,
        factors=factors,
        regularization=regularization,
        iterations=iterations,
        alpha=alpha,
    )
    
    # Validate model
    if not validate_model(model, matrix):
        logger.error("cf_training_model_validation_failed")
        sys.exit(1)
    
    # Save model artifacts
    logger.info("cf_saving_artifacts")
    save_model_artifacts(
        model=model,
        user_id_to_index=user_id_to_index,
        product_id_to_index=product_id_to_index,
        matrix=matrix,
        factors=factors,
        regularization=regularization,
        iterations=iterations,
        alpha=alpha,
    )
    
    total_time = time.time() - start_time
    
    logger.info(
        "cf_training_pipeline_completed",
        total_time_seconds=total_time,
        num_users=len(user_id_to_index),
        num_products=len(product_id_to_index),
        num_interactions=matrix.nnz,
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train collaborative filtering model")
    parser.add_argument(
        "--days-back",
        type=int,
        default=90,
        help="Number of days to look back for interactions (default: 90, use 0 for all time)",
    )
    parser.add_argument(
        "--factors",
        type=int,
        default=DEFAULT_FACTORS,
        help=f"Number of latent factors (default: {DEFAULT_FACTORS})",
    )
    parser.add_argument(
        "--regularization",
        type=float,
        default=DEFAULT_REGULARIZATION,
        help=f"L2 regularization parameter (default: {DEFAULT_REGULARIZATION})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_ITERATIONS,
        help=f"Number of ALS iterations (default: {DEFAULT_ITERATIONS})",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_ALPHA,
        help=f"Confidence scaling for implicit feedback (default: {DEFAULT_ALPHA})",
    )
    parser.add_argument(
        "--min-interactions",
        type=int,
        default=1,
        help="Minimum interactions per user-product pair (default: 1)",
    )
    parser.add_argument(
        "--min-matrix-users",
        type=int,
        default=10,
        help="Minimum number of users required for matrix validation (default: 10)",
    )
    parser.add_argument(
        "--min-matrix-products",
        type=int,
        default=10,
        help="Minimum number of products required for matrix validation (default: 10)",
    )
    parser.add_argument(
        "--min-matrix-interactions",
        type=int,
        default=100,
        help="Minimum number of interactions required for matrix validation (default: 100)",
    )
    
    args = parser.parse_args()
    
    days_back = args.days_back if args.days_back > 0 else None
    
    main(
        days_back=days_back,
        factors=args.factors,
        regularization=args.regularization,
        iterations=args.iterations,
        alpha=args.alpha,
        min_interactions=args.min_interactions,
        min_matrix_users=args.min_matrix_users,
        min_matrix_products=args.min_matrix_products,
        min_matrix_interactions=args.min_matrix_interactions,
    )

