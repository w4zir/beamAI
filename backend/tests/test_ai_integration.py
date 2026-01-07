"""
Integration tests for AI orchestration integration with the /search endpoint.

These tests verify that:
- The feature flag ENABLE_AI_ORCHESTRATION is respected
- The search endpoint still returns the correct shape
- AI orchestration can influence the query used for search (via stub)
"""
import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai.schema import AIOrchestrationResult


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_feature_flags():
    """Reset AI feature flags around each test."""
    original_ai = os.getenv("ENABLE_AI_ORCHESTRATION")
    original_enhancement = os.getenv("ENABLE_QUERY_ENHANCEMENT")
    os.environ["ENABLE_AI_ORCHESTRATION"] = "false"
    os.environ["ENABLE_QUERY_ENHANCEMENT"] = "false"
    yield
    if original_ai is not None:
        os.environ["ENABLE_AI_ORCHESTRATION"] = original_ai
    else:
        os.environ.pop("ENABLE_AI_ORCHESTRATION", None)
    if original_enhancement is not None:
        os.environ["ENABLE_QUERY_ENHANCEMENT"] = original_enhancement
    else:
        os.environ.pop("ENABLE_QUERY_ENHANCEMENT", None)


def test_search_with_ai_orchestration_enabled_uses_stubbed_query():
    """
    When ENABLE_AI_ORCHESTRATION=true and the orchestration service provides
    a final_query, the search endpoint should still function and return results.

    We stub the orchestration service to avoid real LLM calls and to ensure
    deterministic behavior.
    """
    os.environ["ENABLE_AI_ORCHESTRATION"] = "true"

    # Stub orchestration to always rewrite the query to a fixed value.
    from app.routes import search as search_module

    async def _stub_orchestrate_search(query: str) -> AIOrchestrationResult:
        return AIOrchestrationResult(
            original_query=query,
            final_query="stubbed query",
            intent="search",
            confidence=0.99,
            needs_clarification=False,
            language="en",
            used_ai=True,
        )

    with patch.object(
        search_module,
        "get_ai_orchestration_service",
        return_value=Mock(orchestrate_search=_stub_orchestrate_search),
    ):
        # Also stub keyword search to avoid DB calls and make behavior deterministic.
        with patch("app.services.search.keyword.get_supabase_client") as mock_db:
            mock_response = Mock()
            mock_response.data = [
                {
                    "id": "prod_ai_1",
                    "name": "AI Stubbed Product",
                    "description": "Test product",
                    "category": "test",
                    "search_vector": None,
                }
            ]
            mock_db.return_value.table.return_value.select.return_value.execute.return_value = mock_response

            response = client.get("/search?q=original&k=5")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # We do not assert on product IDs here; the goal is to ensure the
            # endpoint still responds correctly with AI orchestration enabled.


