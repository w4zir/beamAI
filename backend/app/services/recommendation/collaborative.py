"""
Collaborative filtering service using Implicit ALS.

According to RECOMMENDATION_DESIGN.md:
- Implicit ALS for collaborative filtering
- Input: user-product interaction matrix
- Training frequency: nightly or batch

According to FEATURE_DEFINITIONS.md:
- user_product_affinity: Strength of user's interaction with product
- Source: Collaborative filtering model output
- Used by: Recommendation ranking
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import numpy as np
from scipy.sparse import csr_matrix
import implicit

from app.core.logging import get_logger
from app.core.database import get_supabase_client
from app.services.features.popularity import EVENT_WEIGHTS
from app.core.metrics import (
    cf_scoring_requests_total,
    cf_scoring_latency_seconds,
    cf_cold_start_total,
)

logger = get_logger(__name__)

# Model configuration
MODEL_VERSION = "1.0.0"
DEFAULT_FACTORS = 50
DEFAULT_REGULARIZATION = 0.1
DEFAULT_ITERATIONS = 15
DEFAULT_ALPHA = 1.0

# Cold start thresholds
MIN_USER_INTERACTIONS = 5  # Minimum interactions before using CF scores

# Default model paths
DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent.parent / "data" / "models" / "cf"
DEFAULT_USER_FACTORS_PATH = DEFAULT_MODEL_DIR / "user_factors.npy"
DEFAULT_ITEM_FACTORS_PATH = DEFAULT_MODEL_DIR / "item_factors.npy"
DEFAULT_USER_MAPPING_PATH = DEFAULT_MODEL_DIR / "user_id_mapping.json"
DEFAULT_PRODUCT_MAPPING_PATH = DEFAULT_MODEL_DIR / "product_id_mapping.json"
DEFAULT_METADATA_PATH = DEFAULT_MODEL_DIR / "model_metadata.json"


def get_event_weights() -> Dict[str, float]:
    """
    Get event type weights for interaction matrix.
    
    Uses same weights as popularity scoring for consistency.
    
    Returns:
        Dictionary mapping event_type to weight
    """
    return EVENT_WEIGHTS.copy()


def extract_user_product_interactions(
    days_back: Optional[int] = 90,
    min_interactions: int = 1
) -> List[Tuple[str, str, float]]:
    """
    Extract user-product interactions from events table.
    
    Args:
        days_back: Number of days to look back (None for all time)
        min_interactions: Minimum number of interactions per user-product pair
        
    Returns:
        List of (user_id, product_id, weighted_score) tuples
    """
    client = get_supabase_client()
    if not client:
        logger.error("cf_data_extraction_db_connection_failed")
        return []
    
    try:
        # Build query
        query = client.table("events").select("user_id, product_id, event_type, timestamp")
        
        # Filter by date if specified
        if days_back:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            query = query.gte("timestamp", cutoff_date.isoformat())
        
        response = query.execute()
        
        if not response.data:
            logger.warning("cf_data_extraction_no_events")
            return []
        
        # Aggregate interactions by user-product pair
        interaction_map: Dict[Tuple[str, str], float] = {}
        event_weights = get_event_weights()
        
        for event in response.data:
            user_id = event["user_id"]
            product_id = event["product_id"]
            event_type = event["event_type"]
            
            weight = event_weights.get(event_type, 0.0)
            if weight > 0:
                key = (user_id, product_id)
                interaction_map[key] = interaction_map.get(key, 0.0) + weight
        
        # Filter by minimum interactions
        interactions = [
            (user_id, product_id, score)
            for (user_id, product_id), score in interaction_map.items()
            if score >= min_interactions
        ]
        
        logger.info(
            "cf_data_extraction_completed",
            total_events=len(response.data),
            unique_pairs=len(interactions),
            days_back=days_back,
        )
        return interactions
        
    except Exception as e:
        logger.error(
            "cf_data_extraction_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return []


def build_interaction_matrix(
    interactions: List[Tuple[str, str, float]]
) -> Tuple[csr_matrix, Dict[str, int], Dict[str, int]]:
    """
    Build sparse interaction matrix from user-product interactions.
    
    Args:
        interactions: List of (user_id, product_id, score) tuples
        
    Returns:
        Tuple of (sparse_matrix, user_id_to_index, product_id_to_index)
    """
    if not interactions:
        logger.warning("cf_matrix_building_no_interactions")
        return csr_matrix((0, 0)), {}, {}
    
    # Create mappings
    user_ids = sorted(set(user_id for user_id, _, _ in interactions))
    product_ids = sorted(set(product_id for _, product_id, _ in interactions))
    
    user_id_to_index = {user_id: idx for idx, user_id in enumerate(user_ids)}
    product_id_to_index = {product_id: idx for idx, product_id in enumerate(product_ids)}
    
    # Build sparse matrix
    rows = []
    cols = []
    data = []
    
    for user_id, product_id, score in interactions:
        user_idx = user_id_to_index[user_id]
        product_idx = product_id_to_index[product_id]
        rows.append(user_idx)
        cols.append(product_idx)
        data.append(score)
    
    matrix = csr_matrix(
        (data, (rows, cols)),
        shape=(len(user_ids), len(product_ids)),
        dtype=np.float32
    )
    
    sparsity = 1.0 - (matrix.nnz / (matrix.shape[0] * matrix.shape[1]))
    
    logger.info(
        "cf_matrix_building_completed",
        num_users=len(user_ids),
        num_products=len(product_ids),
        num_interactions=matrix.nnz,
        sparsity=sparsity,
    )
    
    return matrix, user_id_to_index, product_id_to_index


def validate_interaction_matrix(
    matrix: csr_matrix,
    min_users: int = 10,
    min_products: int = 10,
    min_interactions: int = 100,
    strict: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validate interaction matrix meets minimum requirements.
    
    Args:
        matrix: Sparse interaction matrix
        min_users: Minimum number of users required
        min_products: Minimum number of products required
        min_interactions: Minimum number of interactions required
        strict: If True, fail validation when below threshold. If False, allow training
                with warning if within 10% of threshold.
        
    Returns:
        Tuple of (is_valid, warning_message). warning_message is None if no warning.
    """
    # Check users
    if matrix.shape[0] < min_users:
        threshold_90 = int(min_users * 0.9)
        if not strict and matrix.shape[0] >= threshold_90:
            warning = (
                f"Number of users ({matrix.shape[0]}) is below recommended minimum "
                f"({min_users}) but within acceptable range. Training will proceed with warning."
            )
            logger.warning(
                "cf_matrix_validation_warning",
                reason="insufficient_users",
                num_users=matrix.shape[0],
                min_users=min_users,
            )
            return True, warning
        logger.warning(
            "cf_matrix_validation_failed",
            reason="insufficient_users",
            num_users=matrix.shape[0],
            min_users=min_users,
        )
        return False, None
    
    # Check products
    if matrix.shape[1] < min_products:
        threshold_90 = int(min_products * 0.9)
        if not strict and matrix.shape[1] >= threshold_90:
            warning = (
                f"Number of products ({matrix.shape[1]}) is below recommended minimum "
                f"({min_products}) but within acceptable range. Training will proceed with warning."
            )
            logger.warning(
                "cf_matrix_validation_warning",
                reason="insufficient_products",
                num_products=matrix.shape[1],
                min_products=min_products,
            )
            return True, warning
        logger.warning(
            "cf_matrix_validation_failed",
            reason="insufficient_products",
            num_products=matrix.shape[1],
            min_products=min_products,
        )
        return False, None
    
    # Check interactions
    if matrix.nnz < min_interactions:
        threshold_90 = int(min_interactions * 0.9)
        if not strict and matrix.nnz >= threshold_90:
            warning = (
                f"Number of interactions ({matrix.nnz}) is below recommended minimum "
                f"({min_interactions}) but within acceptable range. Training will proceed with warning. "
                f"Model quality may be reduced."
            )
            logger.warning(
                "cf_matrix_validation_warning",
                reason="insufficient_interactions",
                num_interactions=matrix.nnz,
                min_interactions=min_interactions,
            )
            return True, warning
        logger.warning(
            "cf_matrix_validation_failed",
            reason="insufficient_interactions",
            num_interactions=matrix.nnz,
            min_interactions=min_interactions,
        )
        return False, None
    
    logger.info("cf_matrix_validation_passed")
    return True, None


class CollaborativeFilteringService:
    """
    Collaborative filtering service using Implicit ALS.
    
    Handles:
    - Model loading from disk
    - CF score computation for user-product pairs
    - Cold start handling
    - Batch scoring
    """
    
    def __init__(
        self,
        user_factors_path: Optional[Path] = None,
        item_factors_path: Optional[Path] = None,
        user_mapping_path: Optional[Path] = None,
        product_mapping_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
    ):
        """
        Initialize CF service.
        
        Args:
            user_factors_path: Path to user factors numpy file
            item_factors_path: Path to item factors numpy file
            user_mapping_path: Path to user ID mapping JSON
            product_mapping_path: Path to product ID mapping JSON
            metadata_path: Path to model metadata JSON
        """
        self.user_factors_path = user_factors_path or DEFAULT_USER_FACTORS_PATH
        self.item_factors_path = item_factors_path or DEFAULT_ITEM_FACTORS_PATH
        self.user_mapping_path = user_mapping_path or DEFAULT_USER_MAPPING_PATH
        self.product_mapping_path = product_mapping_path or DEFAULT_PRODUCT_MAPPING_PATH
        self.metadata_path = metadata_path or DEFAULT_METADATA_PATH
        
        self.user_factors: Optional[np.ndarray] = None
        self.item_factors: Optional[np.ndarray] = None
        self.user_id_to_index: Dict[str, int] = {}
        self.product_id_to_index: Dict[str, int] = {}
        self.index_to_user_id: Dict[int, str] = {}
        self.index_to_product_id: Dict[int, str] = {}
        self.metadata: Optional[Dict] = None
        self._available = False
        
        # In-memory cache for user factors (per-request, not persistent)
        self._user_factor_cache: Dict[str, np.ndarray] = {}
    
    def initialize(self) -> bool:
        """
        Initialize service: load model artifacts.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Load metadata first
            if not self.metadata_path.exists():
                logger.warning(
                    "cf_service_metadata_missing",
                    path=str(self.metadata_path),
                )
                return False
            
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
            
            # Load user and product mappings
            if not self.user_mapping_path.exists() or not self.product_mapping_path.exists():
                logger.warning(
                    "cf_service_mappings_missing",
                    user_mapping=str(self.user_mapping_path),
                    product_mapping=str(self.product_mapping_path),
                )
                return False
            
            with open(self.user_mapping_path, 'r') as f:
                user_mapping_data = json.load(f)
                self.user_id_to_index = {k: int(v) for k, v in user_mapping_data.items()}
                self.index_to_user_id = {int(v): k for k, v in user_mapping_data.items()}
            
            with open(self.product_mapping_path, 'r') as f:
                product_mapping_data = json.load(f)
                self.product_id_to_index = {k: int(v) for k, v in product_mapping_data.items()}
                self.index_to_product_id = {int(v): k for k, v in product_mapping_data.items()}
            
            # Load factor matrices
            if not self.user_factors_path.exists() or not self.item_factors_path.exists():
                logger.warning(
                    "cf_service_factors_missing",
                    user_factors=str(self.user_factors_path),
                    item_factors=str(self.item_factors_path),
                )
                return False
            
            self.user_factors = np.load(self.user_factors_path)
            self.item_factors = np.load(self.item_factors_path)
            
            # Validate dimensions
            if self.user_factors.shape[1] != self.item_factors.shape[1]:
                logger.error(
                    "cf_service_dimension_mismatch",
                    user_factors_dim=self.user_factors.shape,
                    item_factors_dim=self.item_factors.shape,
                )
                return False
            
            self._available = True
            
            logger.info(
                "cf_service_initialized",
                num_users=len(self.user_id_to_index),
                num_products=len(self.product_id_to_index),
                factors=self.user_factors.shape[1],
                model_version=self.metadata.get("version", "unknown"),
            )
            return True
            
        except Exception as e:
            logger.error(
                "cf_service_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return False
    
    def is_available(self) -> bool:
        """Check if CF service is available."""
        return self._available
    
    def get_user_interaction_count(self, user_id: str) -> int:
        """
        Get number of interactions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of interactions (0 if user not found)
        """
        client = get_supabase_client()
        if not client:
            return 0
        
        try:
            response = client.table("events").select("id", count="exact").eq("user_id", user_id).execute()
            return response.count or 0
        except Exception:
            return 0
    
    def handle_cold_start_user(self, user_id: str) -> Optional[float]:
        """
        Handle cold start for new users.
        
        Args:
            user_id: User ID
            
        Returns:
            None if user should use CF, 0.0 if cold start
        """
        interaction_count = self.get_user_interaction_count(user_id)
        
        if interaction_count < MIN_USER_INTERACTIONS:
            logger.debug(
                "cf_cold_start_user",
                user_id=user_id,
                interaction_count=interaction_count,
            )
            cf_cold_start_total.labels(cold_start_type="new_user").inc()
            return 0.0
        
        return None
    
    def handle_cold_start_product(self, product_id: str) -> Optional[float]:
        """
        Handle cold start for new products.
        
        Args:
            product_id: Product ID
            
        Returns:
            None if product should use CF, 0.0 if cold start
        """
        if product_id not in self.product_id_to_index:
            logger.debug(
                "cf_cold_start_product",
                product_id=product_id,
            )
            cf_cold_start_total.labels(cold_start_type="new_product").inc()
            return 0.0
        
        return None
    
    def get_user_factors(self, user_id: str) -> Optional[np.ndarray]:
        """
        Get user factor vector.
        
        Args:
            user_id: User ID
            
        Returns:
            User factor vector or None if user not found
        """
        if user_id not in self.user_id_to_index:
            return None
        
        # Check cache first
        if user_id in self._user_factor_cache:
            return self._user_factor_cache[user_id]
        
        user_idx = self.user_id_to_index[user_id]
        factors = self.user_factors[user_idx]
        
        # Cache for this request
        self._user_factor_cache[user_id] = factors
        
        return factors
    
    def compute_user_product_affinity(
        self,
        user_id: str,
        product_id: str
    ) -> float:
        """
        Compute CF score for a user-product pair.
        
        Args:
            user_id: User ID
            product_id: Product ID
            
        Returns:
            CF score between 0.0 and 1.0, or 0.0 if unavailable
        """
        start_time = time.time()
        cf_scoring_requests_total.inc()
        
        if not self.is_available():
            cf_scoring_latency_seconds.observe(time.time() - start_time)
            return 0.0
        
        # Check cold start
        cold_start_score = self.handle_cold_start_user(user_id)
        if cold_start_score is not None:
            cf_scoring_latency_seconds.observe(time.time() - start_time)
            return cold_start_score
        
        cold_start_score = self.handle_cold_start_product(product_id)
        if cold_start_score is not None:
            cf_scoring_latency_seconds.observe(time.time() - start_time)
            return cold_start_score
        
        # Get user factors
        user_factors = self.get_user_factors(user_id)
        if user_factors is None:
            cf_scoring_latency_seconds.observe(time.time() - start_time)
            return 0.0
        
        # Get product factors
        if product_id not in self.product_id_to_index:
            cf_scoring_latency_seconds.observe(time.time() - start_time)
            return 0.0
        
        product_idx = self.product_id_to_index[product_id]
        product_factors = self.item_factors[product_idx]
        
        # Compute dot product
        raw_score = np.dot(user_factors, product_factors)
        
        # Normalize to [0, 1] using sigmoid
        # Using sigmoid: 1 / (1 + exp(-x)) scaled appropriately
        # For ALS scores, typical range is roughly [-2, 2], so we scale
        normalized_score = 1.0 / (1.0 + np.exp(-raw_score))
        
        score = float(np.clip(normalized_score, 0.0, 1.0))
        cf_scoring_latency_seconds.observe(time.time() - start_time)
        
        return score
    
    def compute_user_product_affinities(
        self,
        user_id: str,
        product_ids: List[str]
    ) -> Dict[str, float]:
        """
        Batch compute CF scores for multiple products.
        
        Args:
            user_id: User ID
            product_ids: List of product IDs
            
        Returns:
            Dictionary mapping product_id to CF score
        """
        if not self.is_available():
            return {pid: 0.0 for pid in product_ids}
        
        # Check cold start for user
        cold_start_score = self.handle_cold_start_user(user_id)
        if cold_start_score is not None:
            return {pid: cold_start_score for pid in product_ids}
        
        # Get user factors once
        user_factors = self.get_user_factors(user_id)
        if user_factors is None:
            return {pid: 0.0 for pid in product_ids}
        
        scores = {}
        for product_id in product_ids:
            # Check cold start for product
            cold_start_score = self.handle_cold_start_product(product_id)
            if cold_start_score is not None:
                scores[product_id] = cold_start_score
                continue
            
            if product_id not in self.product_id_to_index:
                scores[product_id] = 0.0
                continue
            
            # Compute score
            product_idx = self.product_id_to_index[product_id]
            product_factors = self.item_factors[product_idx]
            raw_score = np.dot(user_factors, product_factors)
            normalized_score = 1.0 / (1.0 + np.exp(-raw_score))
            scores[product_id] = float(np.clip(normalized_score, 0.0, 1.0))
        
        return scores
    
    def clear_cache(self):
        """Clear in-memory cache."""
        self._user_factor_cache.clear()


# Global service instance (singleton)
_cf_service: Optional[CollaborativeFilteringService] = None


def get_collaborative_filtering_service() -> Optional[CollaborativeFilteringService]:
    """Get global CF service instance."""
    return _cf_service


def initialize_collaborative_filtering() -> bool:
    """
    Initialize global CF service.
    
    Returns:
        True if initialized successfully, False otherwise
    """
    global _cf_service
    
    if _cf_service is not None:
        return _cf_service.is_available()
    
    _cf_service = CollaborativeFilteringService()
    return _cf_service.initialize()

