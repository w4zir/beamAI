"""
Generic async LLM client for Tier 1 agents.

Design constraints (per specs and .cursorrules):
- Do NOT use cloud-specific SDKs
- Use HTTP client (httpx) against an OpenAI-compatible API
- Treat LLM strictly as control-plane (no retrieval or ranking here)

Environment configuration:
- LLM_API_BASE: Base URL for API (default: https://api.openai.com/v1)
- LLM_API_KEY: API key / bearer token
- LLM_TIER1_MODEL: Model name for Tier 1 (default: gpt-3.5-turbo)
- LLM_TIER1_TIMEOUT_SECONDS: Request timeout in seconds (default: 5.0)
- LLM_TIER1_COST_PER_1K_TOKENS: Optional cost hint for metrics (USD, float)
"""
import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.core.logging import get_logger
from app.core.metrics import (
    record_llm_error,
    record_llm_request,
    record_llm_tokens_and_cost,
)

logger = get_logger(__name__)


class LLMClient:
    """Async HTTP client for Tier 1 LLM calls."""

    def __init__(
        self,
        api_base: str,
        api_key: Optional[str],
        tier1_model: str,
        timeout_seconds: float = 5.0,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.tier1_model = tier1_model
        self.timeout_seconds = timeout_seconds

        # Circuit breaker configuration per ARCHITECTURE.md
        self.circuit_breaker = CircuitBreaker(
            name="llm_tier1",
            failure_threshold=0.5,
            time_window_seconds=60,
            open_duration_seconds=30,
            half_open_test_percentage=0.1,
        )

    async def _post(self, path: str, json_payload: Dict[str, Any]) -> httpx.Response:
        """Low-level POST helper (isolated for circuit breaker)."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.api_base}{path}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            return await client.post(url, headers=headers, json=json_payload)

    async def chat(
        self,
        agent: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
        response_format: Optional[Dict[str, Any]] = None,
        tier: str = "1",
    ) -> Dict[str, Any]:
        """
        Call chat completion endpoint for Tier 1 agents.

        Args:
            agent: Logical agent name (\"intent\", \"rewrite\", etc.)
            messages: OpenAI-style chat messages
            max_tokens: Max tokens for completion
            response_format: Optional response_format for JSON mode
            tier: LLM tier label (\"1\" by default)

        Returns:
            Raw JSON response from the API.
        """
        if not self.api_key:
            # No API key configured → treat as unavailable and let caller fallback.
            record_llm_error(agent, "missing_api_key")
            raise RuntimeError("LLM API key not configured")

        payload: Dict[str, Any] = {
            "model": self.tier1_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
        # Encourage JSON-only responses when a format is provided.
        if response_format:
            payload["response_format"] = response_format

        start = time.time()

        try:
            # Protect underlying HTTP call with circuit breaker.
            response: httpx.Response = await self.circuit_breaker.call_async(
                self._post,
                "/chat/completions",
                json_payload=payload,
            )
        except CircuitBreakerOpenError:
            record_llm_error(agent, "circuit_open")
            logger.warning("llm_circuit_open", agent=agent)
            raise
        except httpx.TimeoutException as exc:
            record_llm_error(agent, "timeout")
            logger.warning(
                "llm_timeout",
                agent=agent,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        except httpx.HTTPError as exc:
            record_llm_error(agent, "http_error")
            logger.warning(
                "llm_http_error",
                agent=agent,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        except Exception as exc:
            record_llm_error(agent, "unexpected_error")
            logger.error(
                "llm_unexpected_error",
                agent=agent,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise
        finally:
            duration_ms = (time.time() - start) * 1000.0
            # Even if request failed, record latency for observability.
            record_llm_request(agent, self.tier1_model, tier, duration_ms)

        response.raise_for_status()
        data = response.json()

        # Token usage & cost metrics (best-effort, assumes OpenAI-style usage field).
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)

        # Cost estimation is configurable; default 0 to avoid guessing.
        # If LLM_TIER1_COST_PER_1K_TOKENS is set, we use it for simple estimation.
        cost_per_1k = float(
            os.getenv("LLM_TIER1_COST_PER_1K_TOKENS", "0.0") or "0.0"
        )
        total_tokens = input_tokens + output_tokens
        cost_usd = 0.0
        if cost_per_1k > 0 and total_tokens > 0:
            cost_usd = (total_tokens / 1000.0) * cost_per_1k

        record_llm_tokens_and_cost(
            agent=agent,
            model=self.tier1_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

        return data


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get global LLM client instance for Tier 1 calls.

    This is intentionally minimal and provider-agnostic. It assumes an
    OpenAI-compatible /chat/completions API but does not rely on any SDKs.
    """
    global _llm_client
    if _llm_client is None:
        api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        api_key = os.getenv("LLM_API_KEY")  # May be None (treated as disabled)
        tier1_model = os.getenv("LLM_TIER1_MODEL", "gpt-3.5-turbo")
        timeout = float(os.getenv("LLM_TIER1_TIMEOUT_SECONDS", "5.0") or "5.0")

        _llm_client = LLMClient(
            api_base=api_base,
            api_key=api_key,
            tier1_model=tier1_model,
            timeout_seconds=timeout,
        )

    return _llm_client


