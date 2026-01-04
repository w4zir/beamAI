"""
Health check endpoint.
"""
from fastapi import APIRouter

from app.core.logging import get_logger

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

