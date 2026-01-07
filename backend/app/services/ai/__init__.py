"""
AI orchestration services package.

Implements Tier 1 LLM-powered agents (intent classification, query rewrite)
strictly as a control-plane layer, per specs/AI_ARCHITECTURE.md:

- LLMs orchestrate, interpret, and explain
- Deterministic systems retrieve, rank, and decide

This package must not contain any retrieval or ranking logic.
"""


