"""
Response models for API endpoints.

These models define the structure of API responses.
"""
from typing import Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Search result model."""
    product_id: str
    score: float
    reason: Optional[str] = None


class RecommendResult(BaseModel):
    """Recommendation result model."""
    product_id: str
    score: float
    reason: Optional[str] = None

