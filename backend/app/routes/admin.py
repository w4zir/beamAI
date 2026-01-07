"""
Admin endpoints for rate limiting management.

POST /admin/rate-limit/whitelist
POST /admin/rate-limit/blacklist
GET /admin/rate-limit/status
"""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.rate_limit import get_rate_limit_middleware

logger = get_logger(__name__)

router = APIRouter()


class WhitelistRequest(BaseModel):
    """Request to add/remove from whitelist."""
    identifier: str  # IP address or API key


class BlacklistRequest(BaseModel):
    """Request to add/remove from blacklist."""
    identifier: str  # IP address or API key


@router.post("/rate-limit/whitelist")
async def add_to_whitelist(request: WhitelistRequest):
    """
    Add IP address or API key to whitelist (bypasses rate limiting).
    
    Security: Should require admin authentication in production.
    """
    middleware = get_rate_limit_middleware()
    if not middleware:
        raise HTTPException(status_code=503, detail="Rate limiting not available")
    
    middleware.add_to_whitelist(request.identifier)
    return {"status": "added", "identifier": request.identifier[:10] + "..."}


@router.delete("/rate-limit/whitelist")
async def remove_from_whitelist(request: WhitelistRequest):
    """Remove IP address or API key from whitelist."""
    middleware = get_rate_limit_middleware()
    if not middleware:
        raise HTTPException(status_code=503, detail="Rate limiting not available")
    
    middleware.remove_from_whitelist(request.identifier)
    return {"status": "removed", "identifier": request.identifier[:10] + "..."}


@router.post("/rate-limit/blacklist")
async def add_to_blacklist(request: BlacklistRequest):
    """
    Add IP address or API key to blacklist (blocks all requests).
    
    Security: Should require admin authentication in production.
    """
    middleware = get_rate_limit_middleware()
    if not middleware:
        raise HTTPException(status_code=503, detail="Rate limiting not available")
    
    middleware.add_to_blacklist(request.identifier)
    return {"status": "added", "identifier": request.identifier[:10] + "..."}


@router.delete("/rate-limit/blacklist")
async def remove_from_blacklist(request: BlacklistRequest):
    """Remove IP address or API key from blacklist."""
    middleware = get_rate_limit_middleware()
    if not middleware:
        raise HTTPException(status_code=503, detail="Rate limiting not available")
    
    middleware.remove_from_blacklist(request.identifier)
    return {"status": "removed", "identifier": request.identifier[:10] + "..."}


@router.get("/rate-limit/status")
async def get_rate_limit_status():
    """Get rate limiting status (whitelist/blacklist sizes)."""
    middleware = get_rate_limit_middleware()
    if not middleware:
        raise HTTPException(status_code=503, detail="Rate limiting not available")
    
    return {
        "whitelist_size": len(middleware.whitelist),
        "blacklist_size": len(middleware.blacklist),
        "whitelist": list(middleware.whitelist)[:10],  # Show first 10
        "blacklist": list(middleware.blacklist)[:10],  # Show first 10
    }

