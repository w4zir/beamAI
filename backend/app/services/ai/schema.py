"""
Pydantic models for Tier 1 LLM agent outputs.

These schemas mirror the contracts defined in:
- specs/AI_ARCHITECTURE.md
- docs/implementation_plan.md (AI Phase 1)
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class IntentOutput(BaseModel):
    """
    Structured output for intent classification agent.

    Schema (per AI_ARCHITECTURE.md):
    {
      "intent": "search | recommend | question | clarify",
      "confidence": 0.0-1.0,
      "needs_clarification": false,
      "language": "en"
    }
    """

    intent: str = Field(..., description="search | recommend | question | clarify")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence in [0.0, 1.0]",
    )
    needs_clarification: bool = Field(
        ...,
        description="Whether a clarification question is required before proceeding",
    )
    language: str = Field(
        "en",
        description="BCP-47 language code of the query (e.g. 'en')",
    )

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value: str) -> str:
        allowed = {"search", "recommend", "question", "clarify"}
        v = value.lower().strip()
        if v not in allowed:
            raise ValueError(f"intent must be one of {sorted(allowed)}")
        return v


class QueryRewriteOutput(BaseModel):
    """
    Structured output for query rewrite / entity extraction agent.

    Schema (per AI_ARCHITECTURE.md):
    {
      "normalized_query": "nike running shoes",
      "filters": {
        "brand": "nike",
        "category": "running shoes",
        "price_range": "low"
      },
      "boosts": ["running", "nike"]
    }
    """

    normalized_query: str = Field(..., description="Normalized query string")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured filters (brand, category, attributes, etc.)",
    )
    boosts: List[str] = Field(
        default_factory=list,
        description="Terms to boost in downstream retrieval/ranking",
    )


class AIOrchestrationResult(BaseModel):
    """
    Result returned by AIOrchestrationService for search queries.

    This is an internal control-plane object used by the search endpoint.
    """

    original_query: str
    final_query: Optional[str] = None
    intent: Optional[str] = None
    confidence: float = 0.0
    needs_clarification: bool = False
    language: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    boosts: List[str] = Field(default_factory=list)
    used_ai: bool = False
    from_cache: bool = False


class SchemaValidationError(Exception):
    """Raised when LLM output fails schema validation."""

    def __init__(self, agent: str, message: str, raw_output: Optional[str] = None):
        super().__init__(message)
        self.agent = agent
        self.raw_output = raw_output


def validate_intent_payload(payload: Dict[str, Any]) -> IntentOutput:
    """
    Validate raw JSON payload for intent output.

    Raises:
        SchemaValidationError if validation fails.
    """
    try:
        return IntentOutput.model_validate(payload)
    except ValidationError as exc:
        # NOTE: Metrics are recorded in the caller to avoid circular imports.
        raise SchemaValidationError(
            agent="intent",
            message=f"Invalid intent payload: {exc}",
        ) from exc


def validate_rewrite_payload(payload: Dict[str, Any]) -> QueryRewriteOutput:
    """
    Validate raw JSON payload for query rewrite output.

    Raises:
        SchemaValidationError if validation fails.
    """
    try:
        return QueryRewriteOutput.model_validate(payload)
    except ValidationError as exc:
        raise SchemaValidationError(
            agent="rewrite",
            message=f"Invalid rewrite payload: {exc}",
        ) from exc


