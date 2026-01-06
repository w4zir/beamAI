# AI Phase 1: AI Orchestration Layer & Query Understanding (Tier 1) - TODO Checklist

**Goal**: Implement AI Orchestration Layer with Tier 1 LLM agents for query understanding

**Timeline**: Weeks 5-8

**Status**: ⏳ **NOT IMPLEMENTED**

**Architecture Alignment**: Implements the AI Orchestration Layer pattern from `specs/AI_ARCHITECTURE.md`

**Note**: AI Phase 1 can be implemented in parallel with Phase 1 observability. It enhances query understanding without blocking core observability work.

**Dependencies**: 
- Phase 3.1 Redis Caching Layer (mandatory before LLM calls)
- Phase 2.2 Query Enhancement (enhances with LLM-powered understanding)
- Phase 1.2 Metrics Collection (for LLMOps metrics)

---

## Setup & Configuration
- [ ] Set up Redis for caching (mandatory before LLM calls) - **Requires Phase 3.1 Redis Caching**
- [ ] Set up LLM API client (OpenAI GPT-3.5 Turbo for Tier 1)
- [ ] Add LLM client dependencies to `requirements.txt`
- [ ] Create AI services directory structure (`app/services/ai/`)

## AI Orchestration Layer
- [ ] Create `AIOrchestrationService` in `backend/app/services/ai/orchestration.py`
- [ ] Implement orchestration logic to decide pipeline (search/recommend/clarify)
- [ ] Implement confidence threshold enforcement
- [ ] Implement fallback to deterministic systems
- [ ] Add orchestration middleware before search execution

## Intent Classification Agent (Tier 1)
- [ ] Create `IntentClassificationAgent` (Tier 1) in `backend/app/services/ai/agents/intent.py`
- [ ] Implement intent classification with structured JSON output:
  ```json
  {
    "intent": "search | recommend | question | clarify",
    "confidence": 0.0,
    "needs_clarification": false,
    "language": "en"
  }
  ```
- [ ] Implement cache-first flow (check cache → LLM → cache result)
- [ ] Configure cache TTL (24h for intent classification)
- [ ] Implement schema validation for intent outputs
- [ ] Add timeout handling (fallback to keyword search)
- [ ] Add error handling (fallback to keyword search)

## Query Rewrite & Entity Extraction Agent (Tier 1)
- [ ] Create `QueryRewriteAgent` (Tier 1) in `backend/app/services/ai/agents/rewrite.py`
- [ ] Implement query rewriting with structured JSON output:
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
- [ ] Implement entity extraction (brand, category, attributes)
- [ ] Implement cache-first flow (check cache → LLM → cache result)
- [ ] Configure cache TTL (24h for query rewrite)
- [ ] Implement schema validation for rewrite outputs
- [ ] Add timeout handling (fallback to original query)
- [ ] Add error handling (fallback to original query)

## Voice Interaction Flow
- [ ] Implement voice interaction support:
  - [ ] Speech-to-Text (external or on-device)
  - [ ] Immediate intent extraction (Tier 1 LLM)
  - [ ] Discard raw transcript after intent extraction
  - [ ] Proceed using structured intent only
- [ ] Test voice interaction flow

## Caching Strategy
- [ ] Implement Redis caching for intent classification results
- [ ] Implement Redis caching for query rewrite results
- [ ] Implement cache key generation (hash of query)
- [ ] Implement cache invalidation strategy
- [ ] Add cache hit/miss metrics
- [ ] Target: Cache hit rate >80%

## Integration with Search Pipeline
- [ ] Update search endpoint to use orchestrated queries (with fallback)
- [ ] Integrate intent classification before search
- [ ] Integrate query rewrite before search
- [ ] Maintain backward compatibility (keyword search still works)
- [ ] Add feature flag for AI orchestration (enable/disable)

## LLMOps Metrics
- [ ] Add metric: `llm_requests_total{agent, model, tier}`
- [ ] Add metric: `llm_latency_ms_bucket{agent, tier}` (histogram)
- [ ] Add metric: `llm_cache_hit_total{agent}`
- [ ] Add metric: `llm_cache_miss_total{agent}`
- [ ] Add metric: `llm_errors_total{agent, reason}`
- [ ] Add metric: `llm_schema_validation_failures_total{agent}`
- [ ] Add metric: `llm_low_confidence_total{agent}`
- [ ] Add metric: `llm_tokens_input_total{agent, model}`
- [ ] Add metric: `llm_tokens_output_total{agent, model}`
- [ ] Add metric: `llm_cost_usd_total{agent, model}`
- [ ] Calculate cache hit rate: `llm_cache_hit_rate{agent}`
- [ ] Create Grafana dashboard: "LLM Performance"

## Circuit Breakers
- [ ] Implement circuit breaker for LLM API calls
- [ ] Configure failure threshold (50% error rate over 1 minute)
- [ ] Configure open duration (30 seconds)
- [ ] Configure half-open test traffic (10%)
- [ ] Add circuit breaker state metrics
- [ ] Implement automatic fallback to deterministic systems
- [ ] Alert: LLM error rate >1% for 2m → Critical

## Guardrails & Safety
- [ ] Implement grounding rules: All LLM outputs must reference retrieved product IDs only (zero hallucination)
- [ ] Implement confidence handling: Low confidence (< threshold) triggers clarification agent
- [ ] Implement failure modes: LLM timeout/error → fallback to keyword search (deterministic, no impact)
- [ ] Implement schema validation: 100% pass rate required for all structured outputs

## Testing
- [ ] Write unit tests for intent classification agent
- [ ] Write unit tests for query rewrite agent
- [ ] Write unit tests for AI orchestration service
- [ ] Write unit tests for caching logic
- [ ] Write unit tests for circuit breakers
- [ ] Write integration tests for AI-enhanced search endpoint
- [ ] Test fallback mechanisms (LLM timeout, error, circuit breaker open)
- [ ] Test cache hit/miss scenarios
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
- [ ] Verify LLM error rate: <1%
- [ ] Verify schema validation pass rate: 100%

## Documentation
- [ ] Document AI orchestration layer architecture
- [ ] Document intent classification agent usage
- [ ] Document query rewrite agent usage
- [ ] Document caching strategy
- [ ] Document circuit breaker configuration
- [ ] Document LLMOps metrics
- [ ] Update API documentation with AI-enhanced endpoints
- [ ] Create developer guide for adding new AI agents

## References
- AI Phase 1 specification: `/docs/TODO/implementation_plan.md` (AI Phase 1: Query Understanding)
- AI Architecture: `/specs/AI_ARCHITECTURE.md`
- Phase 2.2 Query Enhancement: `/docs/TODO/phase2_TODO_checklist.md`

