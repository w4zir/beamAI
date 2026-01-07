# AI Phase 1: AI Orchestration Layer & Query Understanding (Tier 1) - TODO Checklist

**Goal**: Implement AI Orchestration Layer with Tier 1 LLM agents for query understanding

**Timeline**: Weeks 5-8

**Status**: ✅ **IMPLEMENTED (CORE CONTROL-PLANE ONLY)**

**Architecture Alignment**: Implements the AI Orchestration Layer pattern from `specs/AI_ARCHITECTURE.md`

**Note**: AI Phase 1 can be implemented in parallel with Phase 1 observability. It enhances query understanding without blocking core observability work.

**Dependencies**: 
- Phase 3.1 Redis Caching Layer (mandatory before LLM calls)
- Phase 2.2 Query Enhancement (enhances with LLM-powered understanding)
- Phase 1.2 Metrics Collection (for LLMOps metrics)

---

## Setup & Configuration
- [x] Set up Redis for caching (mandatory before LLM calls) - **Requires Phase 3.1 Redis Caching**
- [x] Set up LLM API client (OpenAI GPT-3.5 Turbo for Tier 1)
- [x] Add LLM client dependencies to `requirements.txt` *(uses existing `httpx` client, no new SDKs per `.cursorrules`)*
- [x] Create AI services directory structure (`app/services/ai/`)

## AI Orchestration Layer
- [x] Create `AIOrchestrationService` in `backend/app/services/ai/orchestration.py`
- [x] Implement orchestration logic to decide pipeline (search/recommend/clarify)
- [x] Implement confidence threshold enforcement
- [x] Implement fallback to deterministic systems
- [x] Add orchestration middleware before search execution *(implemented directly in `/search` route handler before retrieval and ranking)*

## Intent Classification Agent (Tier 1)
- [x] Create `IntentClassificationAgent` (Tier 1) in `backend/app/services/ai/agents/intent.py`
- [x] Implement intent classification with structured JSON output:
  ```json
  {
    "intent": "search | recommend | question | clarify",
    "confidence": 0.0,
    "needs_clarification": false,
    "language": "en"
  }
  ```
- [x] Implement cache-first flow (check cache → LLM → cache result)
- [x] Configure cache TTL (24h for intent classification)
- [x] Implement schema validation for intent outputs
- [x] Add timeout handling (fallback to keyword search)
- [x] Add error handling (fallback to keyword search)

## Query Rewrite & Entity Extraction Agent (Tier 1)
- [x] Create `QueryRewriteAgent` (Tier 1) in `backend/app/services/ai/agents/rewrite.py`
- [x] Implement query rewriting with structured JSON output:
  ```json
  {
    "normalized_query": "nike running shoes",
    "filters": {
      "brand": "nike",
      "category": "running shoes",
      "price_range": "low"
    },
    "boosts": ["running", "nike"]
  }
  ```
- [ ] Implement entity extraction (brand, category, attributes) *(partial: basic filters only, TODO for richer schema)*
- [x] Implement cache-first flow (check cache → LLM → cache result)
- [x] Configure cache TTL (24h for query rewrite)
- [x] Implement schema validation for rewrite outputs
- [x] Add timeout handling (fallback to original query)
- [x] Add error handling (fallback to original query)

## Voice Interaction Flow
- [ ] Implement voice interaction support:
  - [ ] Speech-to-Text (external or on-device)
  - [ ] Immediate intent extraction (Tier 1 LLM)
  - [ ] Discard raw transcript after intent extraction
  - [ ] Proceed using structured intent only
- [ ] Test voice interaction flow
  - TODO: Voice flow is deferred per current scope; control-plane is ready to consume structured intents.

## Caching Strategy
- [x] Implement Redis caching for intent classification results
- [x] Implement Redis caching for query rewrite results
- [x] Implement cache key generation (hash of query)
- [ ] Implement cache invalidation strategy
- [x] Add cache hit/miss metrics
- [ ] Target: Cache hit rate >80%

## Integration with Search Pipeline
- [x] Update search endpoint to use orchestrated queries (with fallback)
- [x] Integrate intent classification before search
- [x] Integrate query rewrite before search
- [x] Maintain backward compatibility (keyword search still works)
- [x] Add feature flag for AI orchestration (enable/disable)

## LLMOps Metrics
- [x] Add metric: `llm_requests_total{agent, model, tier}`
- [x] Add metric: `llm_latency_ms_bucket{agent, tier}` (histogram)
- [x] Add metric: `llm_cache_hit_total{agent}`
- [x] Add metric: `llm_cache_miss_total{agent}`
- [x] Add metric: `llm_errors_total{agent, reason}`
- [x] Add metric: `llm_schema_validation_failures_total{agent}`
- [x] Add metric: `llm_low_confidence_total{agent}`
- [x] Add metric: `llm_tokens_input_total{agent, model}`
- [x] Add metric: `llm_tokens_output_total{agent, model}`
- [x] Add metric: `llm_cost_usd_total{agent, model}`
- [ ] Calculate cache hit rate: `llm_cache_hit_rate{agent}`
- [ ] Create Grafana dashboard: "LLM Performance"

## Circuit Breakers
- [x] Implement circuit breaker for LLM API calls
- [x] Configure failure threshold (50% error rate over 1 minute)
- [x] Configure open duration (30 seconds)
- [x] Configure half-open test traffic (10%)
- [ ] Add circuit breaker state metrics
- [x] Implement automatic fallback to deterministic systems
- [ ] Alert: LLM error rate >1% for 2m → Critical

## Guardrails & Safety
- [ ] Implement grounding rules: All LLM outputs must reference retrieved product IDs only (zero hallucination)
- [x] Implement confidence handling: Low confidence (< threshold) triggers clarification agent
- [x] Implement failure modes: LLM timeout/error → fallback to keyword search (deterministic, no impact)
- [x] Implement schema validation: 100% pass rate required for all structured outputs

## Testing
- [x] Write unit tests for intent classification agent
- [x] Write unit tests for query rewrite agent
- [x] Write unit tests for AI orchestration service
- [x] Write unit tests for caching logic
- [x] Write unit tests for circuit breakers
- [x] Write integration tests for AI-enhanced search endpoint
- [x] Test fallback mechanisms (LLM timeout, error, circuit breaker open)
- [x] Test cache hit/miss scenarios
- [ ] Performance test: Query understanding latency (target: p95 <80ms with cache)
- [ ] Test voice interaction flow

## A/B Testing Setup
- [ ] Create A/B test framework for enhanced vs. baseline queries - **Requires Phase 8.1 A/B Testing**
- [ ] Implement traffic splitting (50/50 or configurable)
- [ ] Track experiment metrics (zero-result rate, CTR, latency)
- [ ] Create experiment dashboard
- [ ] Document A/B test results

## Success Criteria Verification
- [ ] Verify 15-25% reduction in zero-result searches
- [ ] Verify 10-20% improvement in click-through rates
- [ ] Verify query understanding latency: p95 <80ms (with caching)
- [ ] Verify cache hit rate: >80%
- [x] Verify LLM error rate: <1% *(validated in local testing; monitored via `llm_errors_total`)*
- [x] Verify schema validation pass rate: 100%

## Documentation
- [x] Document AI orchestration layer architecture
- [x] Document intent classification agent usage
- [x] Document query rewrite agent usage
- [x] Document caching strategy
- [x] Document circuit breaker configuration
- [x] Document LLMOps metrics
- [ ] Update API documentation with AI-enhanced endpoints
- [ ] Create developer guide for adding new AI agents

## References
- AI Phase 1 specification: `/docs/TODO/implementation_plan.md` (AI Phase 1: Query Understanding)
- AI Architecture: `/specs/AI_ARCHITECTURE.md`
- Phase 2.2 Query Enhancement: `/docs/TODO/phase2_TODO_checklist.md`

