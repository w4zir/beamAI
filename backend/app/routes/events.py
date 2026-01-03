"""
Event tracking endpoint for user interactions.

POST /events
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.core.logging import get_logger, set_user_id
from app.core.database import get_supabase_client

logger = get_logger(__name__)

router = APIRouter()


class EventRequest(BaseModel):
    """Event tracking request model."""
    user_id: str = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID")
    event_type: str = Field(..., description="Event type: view, add_to_cart, or purchase")
    source: Optional[str] = Field(None, description="Source: search, recommendation, or direct")


@router.post("")
async def track_event(request: Request, event: EventRequest):
    """
    Track a user interaction event.
    
    Events are append-only and used for:
    - Computing popularity scores
    - Training collaborative filtering models
    - Analytics
    """
    # Set user_id in context
    set_user_id(event.user_id)
    
    # Validate event_type
    valid_event_types = ["view", "add_to_cart", "purchase"]
    if event.event_type not in valid_event_types:
        logger.warning(
            "event_invalid_type",
            event_type=event.event_type,
            valid_types=valid_event_types,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    # Validate source if provided
    if event.source:
        valid_sources = ["search", "recommendation", "direct"]
        if event.source not in valid_sources:
            logger.warning(
                "event_invalid_source",
                source=event.source,
                valid_sources=valid_sources,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
            )
    
    client = get_supabase_client()
    if not client:
        logger.error("event_tracking_db_connection_failed")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        logger.info(
            "event_tracking_started",
            user_id=event.user_id,
            product_id=event.product_id,
            event_type=event.event_type,
            source=event.source,
        )
        
        # Insert event
        event_data = {
            "user_id": event.user_id,
            "product_id": event.product_id,
            "event_type": event.event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "source": event.source
        }
        
        response = client.table("events").insert(event_data).execute()
        
        if not response.data:
            logger.error(
                "event_tracking_insert_failed",
                user_id=event.user_id,
                product_id=event.product_id,
                event_type=event.event_type,
            )
            raise HTTPException(status_code=500, detail="Failed to insert event")
        
        event_id = response.data[0].get("id") if response.data else None
        logger.info(
            "event_tracked",
            user_id=event.user_id,
            product_id=event.product_id,
            event_type=event.event_type,
            source=event.source,
            event_id=event_id,
        )
        
        return {
            "success": True,
            "event_id": event_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "event_tracking_error",
            user_id=event.user_id,
            product_id=event.product_id,
            event_type=event.event_type,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error during event tracking")

