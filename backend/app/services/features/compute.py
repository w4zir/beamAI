"""
Feature computation orchestrator.

Runs batch jobs to compute and update features in the database.
"""
import logging
from app.services.features.popularity import compute_and_update_popularity_scores

logger = logging.getLogger(__name__)


def run_all_feature_computations():
    """
    Run all offline feature computations.
    
    This should be called periodically (e.g., via cron job or scheduled task).
    """
    logger.info("=" * 50)
    logger.info("Starting feature computation batch job")
    logger.info("=" * 50)
    
    # Compute and update popularity scores
    try:
        updated_count = compute_and_update_popularity_scores()
        logger.info(f"✓ Popularity scores: Updated {updated_count} products")
    except Exception as e:
        logger.error(f"✗ Error computing popularity scores: {e}", exc_info=True)
    
    # Note: freshness_score is computed on-demand in ranking service,
    # so no batch job needed for it.
    
    logger.info("=" * 50)
    logger.info("Feature computation batch job completed")
    logger.info("=" * 50)


if __name__ == "__main__":
    # Allow running as a script
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_all_feature_computations()

