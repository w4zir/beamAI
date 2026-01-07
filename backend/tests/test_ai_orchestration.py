"""
Unit tests for AI Phase 1 components:
- IntentClassificationAgent (Tier 1)
- QueryRewriteAgent (Tier 1)
- AIOrchestrationService

These tests use in-memory stubs/mocks only and do NOT perform real HTTP calls.
"""
import json
from typing import Any, Dict

import pytest

from app.services.ai.schema import (
    IntentOutput,
    QueryRewriteOutput,
)


class DummyLLMClient:
    """Simple stub that emulates an OpenAI-style chat completion response."""

    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    async def chat(self, agent: str, messages, max_tokens: int = 0, response_format=None, tier: str = "1"):
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(self._payload),
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }


@pytest.mark.asyncio
async def test_intent_agent_basic_classification(monkeypatch):
    """IntentClassificationAgent returns structured intent for valid JSON response."""
    from app.services.ai.agents import intent as intent_module

    dummy_payload = {
        "intent": "search",
        "confidence": 0.9,
        "needs_clarification": False,
        "language": "en",
    }

    # Patch LLM client before constructing the agent
    monkeypatch.setattr(
        intent_module,
        "get_llm_client",
        lambda: DummyLLMClient(dummy_payload),
    )

    agent = intent_module.IntentClassificationAgent(confidence_threshold=0.7)
    result = await agent.classify("running shoes")

    assert isinstance(result, IntentOutput)
    assert result.intent == "search"
    assert result.confidence == pytest.approx(0.9)
    assert not result.needs_clarification


@pytest.mark.asyncio
async def test_intent_agent_low_confidence(monkeypatch):
    """IntentClassificationAgent returns None when confidence is below threshold."""
    from app.services.ai.agents import intent as intent_module

    low_conf_payload = {
        "intent": "search",
        "confidence": 0.3,
        "needs_clarification": False,
        "language": "en",
    }

    monkeypatch.setattr(
        intent_module,
        "get_llm_client",
        lambda: DummyLLMClient(low_conf_payload),
    )

    agent = intent_module.IntentClassificationAgent(confidence_threshold=0.7)
    result = await agent.classify("running shoes")

    # Low-confidence results should be ignored so that callers can fall back.
    assert result is None


@pytest.mark.asyncio
async def test_query_rewrite_agent_basic_rewrite(monkeypatch):
    """QueryRewriteAgent returns normalized query and filters from LLM JSON."""
    from app.services.ai.agents import rewrite as rewrite_module

    dummy_payload = {
        "normalized_query": "nike running shoes",
        "filters": {"brand": "nike", "category": "running shoes"},
        "boosts": ["nike", "running"],
    }

    monkeypatch.setattr(
        rewrite_module,
        "get_llm_client",
        lambda: DummyLLMClient(dummy_payload),
    )

    agent = rewrite_module.QueryRewriteAgent()
    result = await agent.rewrite("Nike running shoes", intent=None)

    assert isinstance(result, QueryRewriteOutput)
    assert result.normalized_query == "nike running shoes"
    assert result.filters.get("brand") == "nike"
    assert "nike" in result.boosts


@pytest.mark.asyncio
async def test_ai_orchestration_search_success(monkeypatch):
    """AIOrchestrationService uses both intent and rewrite agents when successful."""
    from app.services.ai import orchestration as orch_module

    class DummyIntentAgent:
        async def classify(self, query: str) -> IntentOutput:
            return IntentOutput(
                intent="search",
                confidence=0.9,
                needs_clarification=False,
                language="en",
            )

    class DummyRewriteAgent:
        async def rewrite(self, query: str, intent: IntentOutput) -> QueryRewriteOutput:
            return QueryRewriteOutput(
                normalized_query="normalized query",
                filters={"brand": "nike"},
                boosts=["nike"],
            )

    monkeypatch.setattr(orch_module, "get_intent_agent", lambda: DummyIntentAgent())
    monkeypatch.setattr(orch_module, "get_query_rewrite_agent", lambda: DummyRewriteAgent())

    service = orch_module.AIOrchestrationService(confidence_threshold=0.7)
    result = await service.orchestrate_search("Nike running shoes")

    assert result.used_ai
    assert result.final_query == "normalized query"
    assert result.filters.get("brand") == "nike"
    assert result.intent == "search"
    assert result.confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_ai_orchestration_search_fallback_on_low_confidence(monkeypatch):
    """AIOrchestrationService falls back when intent is low-confidence."""
    from app.services.ai import orchestration as orch_module

    class DummyLowIntentAgent:
        async def classify(self, query: str) -> IntentOutput:
            return IntentOutput(
                intent="search",
                confidence=0.2,
                needs_clarification=False,
                language="en",
            )

    monkeypatch.setattr(orch_module, "get_intent_agent", lambda: DummyLowIntentAgent())

    # Rewrite agent should never be called in this scenario, but we provide a stub.
    class DummyRewriteAgent:
        async def rewrite(self, query: str, intent: IntentOutput) -> QueryRewriteOutput:  # pragma: no cover - defensive
            return QueryRewriteOutput(
                normalized_query=query,
                filters={},
                boosts=[],
            )

    monkeypatch.setattr(orch_module, "get_query_rewrite_agent", lambda: DummyRewriteAgent())

    service = orch_module.AIOrchestrationService(confidence_threshold=0.7)
    result = await service.orchestrate_search("query")

    assert not result.used_ai
    assert result.final_query is None


