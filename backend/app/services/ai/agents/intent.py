"""
Intent classification agent (Tier 1).

Responsibilities:
- Classify user intent for a raw query
- Enforce JSON-only schema via pydantic validation
- Use cache-first strategy before calling LLM
- Never perform retrieval or ranking

Fallback behavior is handled by the AIOrchestrationService.
"""
import json
from typing import Optional

from app.core.logging import get_logger
from app.core.metrics import (
    record_llm_low_confidence,
    record_llm_schema_validation_failure,
)
from app.services.ai.cache import get_cached_intent, cache_intent
from app.services.ai.llm_client import get_llm_client
from app.services.ai.schema import (
    IntentOutput,
    SchemaValidationError,
    validate_intent_payload,
)

logger = get_logger(__name__)


class IntentClassificationAgent:
    """Tier 1 intent classification agent."""

    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self._llm_client = get_llm_client()

    async def classify(self, query: str) -> Optional[IntentOutput]:
        """
        Classify user intent for a query.

        Returns:
            IntentOutput on success, or None if classification should be ignored.

        Raises:
            RuntimeError / HTTP errors if LLM is misconfigured or unavailable.
            Callers are expected to catch and fallback to deterministic systems.
        """
        if not query or not query.strip():
            return None

        # 1) Cache-first
        cached = await get_cached_intent(query)
        if cached is not None:
            try:
                intent = validate_intent_payload(cached)
            except SchemaValidationError as exc:
                # Cached payload invalid → treat as miss and do not reuse.
                record_llm_schema_validation_failure("intent")
                logger.warning(
                    "intent_cache_schema_invalid",
                    error=str(exc),
                )
            else:
                # Apply confidence threshold
                if intent.confidence < self.confidence_threshold:
                    record_llm_low_confidence("intent")
                    return None
                return intent

        # 2) LLM call (cache miss)
        system_prompt = (
            "You are a search intent classifier for an e-commerce search engine. "
            "Given a raw user query, classify the intent.\n\n"
            "You MUST respond with a single JSON object only, with keys:\n"
            '{"intent": "search | recommend | question | clarify", '
            '"confidence": 0.0-1.0, '
            '"needs_clarification": true|false, '
            '"language": "en"}\n'
            "Do not include any explanation, comments, or extra fields."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        # Use JSON mode when supported; fallback is handled by caller if schema fails.
        response = await self._llm_client.chat(
            agent="intent",
            messages=messages,
            max_tokens=128,
            response_format={"type": "json_object"},
            tier="1",
        )

        # OpenAI-compatible shape: choices[0].message.content is a JSON string.
        try:
            content = (
                response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            payload = json.loads(content)
        except Exception as exc:
            record_llm_schema_validation_failure("intent")
            logger.warning(
                "intent_llm_invalid_json",
                error=str(exc),
                raw=response,
            )
            return None

        try:
            intent = validate_intent_payload(payload)
        except SchemaValidationError as exc:
            record_llm_schema_validation_failure("intent")
            logger.warning(
                "intent_llm_schema_invalid",
                error=str(exc),
                raw_payload=payload,
            )
            return None

        # Enforce confidence threshold
        if intent.confidence < self.confidence_threshold:
            record_llm_low_confidence("intent")
            return None

        # Best-effort cache store
        await cache_intent(query, payload)
        return intent


_intent_agent: Optional[IntentClassificationAgent] = None


def get_intent_agent() -> IntentClassificationAgent:
    """Global singleton accessor."""
    global _intent_agent
    if _intent_agent is None:
        _intent_agent = IntentClassificationAgent()
    return _intent_agent


