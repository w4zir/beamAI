"""
Prometheus metrics endpoint.

GET /metrics
Returns Prometheus-formatted metrics for scraping.
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.core.metrics import get_metrics, get_metrics_content_type
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    No authentication required (standard Prometheus practice).
    """
    try:
        metrics_data = get_metrics()
        return Response(
            content=metrics_data,
            media_type=get_metrics_content_type(),
        )
    except Exception as e:
        logger.error(
            "metrics_endpoint_error",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        # Return empty metrics on error (better than failing completely)
        return Response(
            content=b"# Error collecting metrics\n",
            media_type=get_metrics_content_type(),
        )

