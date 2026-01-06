# AI Phase 4: Clarification & Conversational Interface (Tier 1 + Tier 2) - TODO Checklist

**Goal**: Structured clarification (Tier 1) and optional conversational responses (Tier 2)

**Timeline**: Weeks 17-20

**Status**: ⏳ **NOT IMPLEMENTED**

**Architecture Alignment**: Tier 1 for clarification (structured), Tier 2 for conversational UX (optional, async)

**Dependencies**: 
- AI Phase 1 Query Understanding (extends with clarification)
- Phase 3.1 Redis Caching (for session management)

---

## Setup & Configuration
- [ ] Set up LLM API client for Tier 1 (OpenAI GPT-3.5 Turbo)
- [ ] Set up LLM API client for Tier 2 (OpenAI GPT-4 or Claude Sonnet)
- [ ] Create clarification agent module (`app/services/ai/agents/clarification.py`)
- [ ] Create response composition service module (`app/services/ai/composition.py`)

## Clarification Agent (Tier 1)
- [ ] Create `ClarificationAgent` (Tier 1) in `backend/app/services/ai/agents/clarification.py`
- [ ] Implement clarification question generation (structured JSON):
  ```json
  {
    "needs_clarification": true,
    "clarification_type": "brand|category|attribute|intent",
    "question": "Which brand are you looking for?",
    "options": ["Nike", "Adidas", "Puma"],
    "context": {
      "original_query": "running shoes",
      "ambiguous_entities": ["brand"],
      "confidence": 0.5
    }
  }
  ```
- [ ] Trigger clarification when: Intent confidence < threshold (default: 0.7)
- [ ] Trigger clarification when: Ambiguous or conflicting entities
- [ ] Trigger clarification when: Zero results with low confidence query
- [ ] Ask exactly one clarification question (never multiple)
- [ ] Implement cache-first flow (check cache → LLM → cache result)
- [ ] Configure cache TTL (1h for clarification questions)

## Response Composition Service (Tier 2, Optional)
- [ ] Create `ResponseCompositionService` (Tier 2) in `backend/app/services/ai/composition.py`
- [ ] Implement natural language response generation (async)
- [ ] Implement grounding validation (responses only reference retrieved product IDs)
- [ ] Implement cache-first flow (check cache → LLM → cache result)
- [ ] Configure cache TTL (5-10min for responses)
- [ ] Never block search/recommendation responses (async only)

## Session Management
- [ ] Implement session management in Redis - **Requires Phase 3.1 Redis Caching**
- [ ] Store conversation history (session key: `clarify:{session_id}`)
- [ ] Configure session TTL (1 hour)
- [ ] Include session_id in clarification response
- [ ] Use session_id in follow-up requests

## Clarification Endpoint
- [ ] Add clarification endpoint: `POST /search/clarify` (Tier 1, structured JSON)
- [ ] Accept clarification response from user
- [ ] Process clarified query
- [ ] Return search results with clarified intent

## Conversational Endpoint (Optional)
- [ ] Add optional conversational endpoint: `POST /search/conversation` (Tier 2, async)
- [ ] Accept conversational messages
- [ ] Generate conversational responses (async, best-effort)
- [ ] Return responses with product recommendations

## Frontend Integration
- [ ] Frontend: Build clarification UI component (required)
- [ ] Frontend: Build chat UI component (optional enhancement)
- [ ] Display clarification questions
- [ ] Handle clarification responses
- [ ] Display conversational responses (if available)

## Grounding Validation
- [ ] Implement grounding validation: Responses only reference retrieved product IDs (zero hallucination)
- [ ] Validate all LLM outputs
- [ ] Reject responses with hallucinated content
- [ ] Log validation failures

## Testing
- [ ] Write unit tests for clarification agent
- [ ] Write unit tests for response composition service
- [ ] Write unit tests for session management
- [ ] Write integration tests for clarification endpoint
- [ ] Write integration tests for conversational endpoint
- [ ] Test clarification flow
- [ ] Test conversational flow
- [ ] Test grounding validation

## LLMOps Metrics
- [ ] Add metric: `llm_clarification_triggered_total`
- [ ] Add metric: `llm_clarification_success_total`
- [ ] Add metric: `llm_conversation_requests_total`
- [ ] Add metric: `llm_conversation_responses_generated_total`
- [ ] Track clarification success rate
- [ ] Track conversation engagement

## Success Criteria Verification
- [ ] Verify 30-50% reduction in support tickets (for search-related queries)
- [ ] Verify 20-30% improvement in user satisfaction
- [ ] Verify clarification success rate: >60% (user provides clarification)
- [ ] Verify average conversation length: 2-3 turns (if conversational mode enabled)
- [ ] Verify zero hallucination (grounding validation: 100% pass rate)

## Documentation
- [ ] Document clarification agent architecture
- [ ] Document response composition service
- [ ] Document session management
- [ ] Document clarification endpoint
- [ ] Document conversational endpoint
- [ ] Update API documentation

## References
- AI Phase 4 specification: `/docs/TODO/implementation_plan.md` (AI Phase 4: Clarification & Conversational)
- AI Architecture: `/specs/AI_ARCHITECTURE.md`
- AI Phase 1: `/docs/TODO/ai_phase1_TODO_checklist.md`

