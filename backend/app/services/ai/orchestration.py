"""
AI Orchestration Layer (AI Phase 1).

Responsibilities (per specs/AI_ARCHITECTURE.md and docs/implementation_plan.md):
- Decide which deterministic pipeline to invoke (search/recommend/clarify)
- Normalize messy user input into structured instructions
- Enforce confidence thresholds and fallbacks

NON-responsibilities:
- Does NOT fetch products
- Does NOT rank catalogs
- Does NOT apply business logic
"""
from typing import Optional

from app.core.logging import get_logger
from app.core.metrics import record_llm_low_confidence
from app.services.ai.agents.intent import get_intent_agent
from app.services.ai.agents.rewrite import get_query_rewrite_agent
from app.services.ai.schema import (
    AIOrchestrationResult,
    IntentOutput,
    QueryRewriteOutput,
)

logger = get_logger(__name__)


class AIOrchestrationService:
    """
    Control-plane orchestration for AI Phase 1.

    Currently focuses on the search pipeline:
    - Intent classification (Tier 1)
    - Query rewrite & entity extraction (Tier 1)
    - Safe fallbacks to deterministic query enhancement / keyword search
    """

    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self._intent_agent = get_intent_agent()
        self._rewrite_agent = get_query_rewrite_agent()

    async def orchestrate_search(self, query: str) -> AIOrchestrationResult:
        """
        Orchestrate AI understanding for a search query.

        This method is deliberately conservative:
        - If anything fails (LLM errors, schema issues, low confidence),
          it returns a result that signals the caller to fall back to
          deterministic query enhancement.
        """
        result = AIOrchestrationResult(original_query=query)

        if not query or not query.strip():
            return result

        intent: Optional[IntentOutput] = None
        rewrite: Optional[QueryRewriteOutput] = None

        # Step 1: Intent classification (Tier 1)
        try:
            intent = await self._intent_agent.classify(query)
        except Exception as exc:
            logger.warning(
                "ai_orchestration_intent_failed",
                query=query,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            # Fallback handled below.

        if intent is None:
            # No usable intent (low confidence or error) → fallback path.
            record_llm_low_confidence("intent")
            return result

        result.intent = intent.intent
        result.confidence = intent.confidence
        result.needs_clarification = intent.needs_clarification
        result.language = intent.language

        # Enforce confidence threshold again at orchestration layer to ensure
        # end-to-end behavior matches specs even if the agent is misconfigured.
        if intent.confidence < self.confidence_threshold:
            record_llm_low_confidence("intent")
            return result

        # NOTE: Clarification agent is AI Phase 4.
        # For now, if needs_clarification is True, we log and fall back.
        if intent.needs_clarification or intent.intent not in {"search", "recommend"}:
            logger.info(
                "ai_orchestration_intent_requires_clarification",
                query=query,
                intent=intent.intent,
                confidence=intent.confidence,
                needs_clarification=intent.needs_clarification,
            )
            # TODO: Integrate ClarificationAgent in AI Phase 4.
            return result

        # Step 2: Query rewrite & entity extraction (Tier 1)
        try:
            rewrite = await self._rewrite_agent.rewrite(query=query, intent=intent)
        except Exception as exc:
            logger.warning(
                "ai_orchestration_rewrite_failed",
                query=query,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            # Fallback handled below.

        if rewrite is None:
            # No usable rewrite → keep intent metadata but let caller fall back.
            return result

        result.final_query = rewrite.normalized_query or query
        result.filters = rewrite.filters
        result.boosts = rewrite.boosts
        result.used_ai = True

        logger.info(
            "ai_orchestration_search_completed",
            original_query=query,
            final_query=result.final_query,
            intent=result.intent,
            confidence=result.confidence,
            needs_clarification=result.needs_clarification,
        )

        return result


_ai_orchestration_service: Optional[AIOrchestrationService] = None


def get_ai_orchestration_service() -> AIOrchestrationService:
    """Global singleton accessor for AI orchestration service."""
    global _ai_orchestration_service
    if _ai_orchestration_service is None:
        _ai_orchestration_service = AIOrchestrationService()
    return _ai_orchestration_service


