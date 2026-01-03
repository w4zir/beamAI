"""
Compute product_freshness_score based on time decay from created_at.

According to FEATURE_DEFINITIONS.md:
- Type: float
- Description: Recency-based boost
- Computation: Time decay from created_at
- Used by: Ranking service only (computed on-demand, not stored)
"""
from datetime import datetime, timezone
from typing import Optional
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# Half-life in days (products lose half their freshness after this many days)
FRESHNESS_HALF_LIFE_DAYS = 90.0


def compute_freshness_score(created_at: datetime, reference_time: Optional[datetime] = None) -> float:
    """
    Compute freshness score using exponential decay.
    
    Formula: score = exp(-ln(2) * days_old / half_life)
    - New products (0 days old): score = 1.0
    - Products at half-life: score = 0.5
    - Older products: score approaches 0
    
    Args:
        created_at: When the product was created
        reference_time: Reference time for calculation (defaults to now)
        
    Returns:
        Freshness score between 0.0 and 1.0
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    
    # Ensure both datetimes are timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    
    # Calculate days since creation
    delta = reference_time - created_at
    days_old = delta.total_seconds() / (24 * 3600)
    
    # Handle negative days (future dates) or very old products
    if days_old < 0:
        days_old = 0
    elif days_old > FRESHNESS_HALF_LIFE_DAYS * 5:  # Very old products
        return 0.0
    
    # Exponential decay formula
    # Using numpy for numerical stability
    score = np.exp(-np.log(2) * days_old / FRESHNESS_HALF_LIFE_DAYS)
    
    # Clamp to [0, 1]
    return float(np.clip(score, 0.0, 1.0))


def compute_freshness_score_from_string(created_at_str: str, reference_time: Optional[datetime] = None) -> float:
    """
    Compute freshness score from ISO format string.
    
    Args:
        created_at_str: ISO format datetime string
        reference_time: Reference time for calculation (defaults to now)
        
    Returns:
        Freshness score between 0.0 and 1.0
    """
    try:
        # Parse ISO format string
        if created_at_str.endswith('Z'):
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        else:
            created_at = datetime.fromisoformat(created_at_str)
        
        return compute_freshness_score(created_at, reference_time)
    except (ValueError, AttributeError) as e:
        logger.warning(
            "freshness_score_parse_failed",
            created_at_str=created_at_str,
            error=str(e),
            error_type=type(e).__name__,
        )
        return 0.0

