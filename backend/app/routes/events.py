"""
Event tracking endpoint for user interactions.

POST /events
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime

from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


class EventRequest(BaseModel):
    """Event tracking request model."""
    user_id: str = Field(..., description="User ID")
    product_id: str = Field(..., description="Product ID")
    event_type: str = Field(..., description="Event type: view, add_to_cart, or purchase")
    source: Optional[str] = Field(None, description="Source: search, recommendation, or direct")


@router.post("")
async def track_event(event: EventRequest):
    """
    Track a user interaction event.
    
    Events are append-only and used for:
    - Computing popularity scores
    - Training collaborative filtering models
    - Analytics
    """
    # Validate event_type
    valid_event_types = ["view", "add_to_cart", "purchase"]
    if event.event_type not in valid_event_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    # Validate source if provided
    if event.source:
        valid_sources = ["search", "recommendation", "direct"]
        if event.source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
            )
    
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
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
            raise HTTPException(status_code=500, detail="Failed to insert event")
        
        logger.info(f"Tracked event: {event.event_type} for user {event.user_id}, product {event.product_id}")
        
        return {
            "success": True,
            "event_id": response.data[0].get("id") if response.data else None
        }
        
    except Exception as e:
        logger.error(f"Error tracking event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during event tracking")

