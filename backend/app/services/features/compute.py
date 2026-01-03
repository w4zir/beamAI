"""
Feature computation orchestrator.

Runs batch jobs to compute and update features in the database.
"""
from app.core.logging import configure_logging, get_logger
from app.services.features.popularity import compute_and_update_popularity_scores

logger = get_logger(__name__)


def run_all_feature_computations():
    """
    Run all offline feature computations.
    
    This should be called periodically (e.g., via cron job or scheduled task).
    """
    logger.info("feature_computation_batch_started")
    
    # Compute and update popularity scores
    try:
        updated_count = compute_and_update_popularity_scores()
        logger.info(
            "feature_computation_popularity_completed",
            updated_count=updated_count,
        )
    except Exception as e:
        logger.error(
            "feature_computation_popularity_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
    
    # Note: freshness_score is computed on-demand in ranking service,
    # so no batch job needed for it.
    
    logger.info("feature_computation_batch_completed")


if __name__ == "__main__":
    # Allow running as a script
    import sys
    from pathlib import Path
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    
    # Configure structured logging
    configure_logging(log_level="INFO", json_output=False)
    
    run_all_feature_computations()

