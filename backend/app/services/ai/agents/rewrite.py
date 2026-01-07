"""
Query rewrite & entity extraction agent (Tier 1).

Responsibilities:
- Normalize natural language query into structured form
- Extract filters (brand, category, attributes, etc.)
- Suggest boost terms for retrieval/ranking

Constraints:
- JSON-only output validated via pydantic
- Cache-first strategy before LLM
- No retrieval or ranking logic here
"""
import json
from typing import Optional

from app.core.logging import get_logger
from app.core.metrics import (
    record_llm_schema_validation_failure,
)
from app.services.ai.cache import get_cached_rewrite, cache_rewrite
from app.services.ai.llm_client import get_llm_client
from app.services.ai.schema import (
    IntentOutput,
    QueryRewriteOutput,
    SchemaValidationError,
    validate_rewrite_payload,
)

logger = get_logger(__name__)


class QueryRewriteAgent:
    """Tier 1 query rewrite and entity extraction agent."""

    def __init__(self):
        self._llm_client = get_llm_client()

    async def rewrite(
        self,
        query: str,
        intent: Optional[IntentOutput] = None,
    ) -> Optional[QueryRewriteOutput]:
        """
        Rewrite query into normalized form with filters and boosts.

        Returns:
            QueryRewriteOutput on success, or None if rewrite should be ignored.

        Raises:
            RuntimeError / HTTP errors if LLM is misconfigured or unavailable.
            Callers are expected to catch and fallback.
        """
        if not query or not query.strip():
            return None

        # 1) Cache-first
        cached = await get_cached_rewrite(query)
        if cached is not None:
            try:
                return validate_rewrite_payload(cached)
            except SchemaValidationError as exc:
                record_llm_schema_validation_failure("rewrite")
                logger.warning(
                    "rewrite_cache_schema_invalid",
                    error=str(exc),
                )

        # 2) LLM call
        system_prompt = (
            "You are a query rewrite and entity extraction service for an "
            "e-commerce search engine. Given a raw user query, you MUST respond "
            "with a single JSON object with the following shape:\n"
            '{\n'
            '  "normalized_query": "nike running shoes",\n'
            '  "filters": {\n'
            '    "brand": "nike",\n'
            '    "category": "running shoes",\n'
            '    "price_range": "low"\n'
            "  },\n"
            '  "boosts": ["running", "nike"]\n'
            "}\n\n"
            "Rules:\n"
            "- Do NOT include any extra top-level keys.\n"
            "- Do NOT include comments or explanations.\n"
            "- If you are unsure about filters, use an empty object {}.\n"
            "- If there are no boosts, use an empty list [].\n"
        )

        # Optional context from intent (if available)
        user_prompt = query
        if intent is not None:
            user_prompt = (
                f"Intent: {intent.intent}, confidence: {intent.confidence}. "
                f"Query: {query}"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self._llm_client.chat(
            agent="rewrite",
            messages=messages,
            max_tokens=256,
            response_format={"type": "json_object"},
            tier="1",
        )

        try:
            content = (
                response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            payload = json.loads(content)
        except Exception as exc:
            record_llm_schema_validation_failure("rewrite")
            logger.warning(
                "rewrite_llm_invalid_json",
                error=str(exc),
                raw=response,
            )
            return None

        try:
            rewrite = validate_rewrite_payload(payload)
        except SchemaValidationError as exc:
            record_llm_schema_validation_failure("rewrite")
            logger.warning(
                "rewrite_llm_schema_invalid",
                error=str(exc),
                raw_payload=payload,
            )
            return None

        await cache_rewrite(query, payload)
        return rewrite


_rewrite_agent: Optional[QueryRewriteAgent] = None


def get_query_rewrite_agent() -> QueryRewriteAgent:
    """Global singleton accessor."""
    global _rewrite_agent
    if _rewrite_agent is None:
        _rewrite_agent = QueryRewriteAgent()
    return _rewrite_agent


