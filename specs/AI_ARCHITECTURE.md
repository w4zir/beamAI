# AI_ARCHITECTURE.md

## Purpose
This document defines how **AI Agents and LLMs augment the existing search and recommendation architecture** without compromising latency, cost, reliability, or correctness.

The guiding principle:
> **LLMs orchestrate, interpret, and explain. Deterministic systems retrieve, rank, and decide.**

This mirrors proven production patterns from Stripe, Shopify, DoorDash, Delivery Hero, and similar platforms.

---

## Design Goals

1. **Excellent User Experience**
   - Understand user intent from text and voice
   - Handle ambiguous queries gracefully
   - Provide clear, grounded responses

2. **High Accuracy**
   - Zero hallucinated products or facts
   - Responses always grounded in retrieved data

3. **Low Latency**
   - LLMs never block critical retrieval paths
   - Fast fallbacks when LLMs are unavailable

4. **Low Cost**
   - Minimize token usage
   - Aggressive caching
   - Progressive model distillation

---

## High-Level Architecture

```
Client (Text / Voice)
   |
   v
API Gateway
   |
   v
AI Orchestration Layer
   |
   +--> Intent Classification Agent (LLM - Tier 1)
   +--> Query Rewrite / Entity Extraction Agent (LLM - Tier 1)
   |
   +--> Search Pipeline (Keyword + FAISS + Ranking)
   +--> Recommendation Pipeline (CF + Popularity + Ranking)
   |
   +--> Response Composition Agent (LLM - Tier 2, optional)
   |
   v
Response to Client
```

LLMs operate strictly as **control-plane components**.

---

## AI Orchestration Layer

### Responsibilities
- Decide **which pipeline to invoke** (search, recommend, clarify)
- Normalize messy user input into structured instructions
- Enforce confidence thresholds and fallbacks

### Non-Responsibilities
- Does NOT fetch products
- Does NOT rank entire catalogs
- Does NOT apply business logic

---

## LLM Tiering Strategy

| Tier | Purpose | Characteristics | SLA |
|----|----|----|----|
| Tier 0 | No LLM | Cached / rules | <10ms |
| Tier 1 | Intent, rewrite, entities | Small model, JSON output | p95 <80ms |
| Tier 2 | Explanation, chat UX | Larger model, async | Best-effort |

**Hard Rule:** Tier 2 LLMs must never block search or recommendation responses.

---

## Core AI Agents

### 1. Intent Classification Agent

**Purpose**
- Classify user intent and confidence

**Inputs**
- Raw text or speech transcript

**Outputs (strict schema)**
```json
{
  "intent": "search | recommend | question | clarify",
  "confidence": 0.0,
  "needs_clarification": false,
  "language": "en"
}
```

**Notes**
- Cached by query hash
- Used before any expensive downstream processing

---

### 2. Query Rewrite & Entity Extraction Agent

**Purpose**
- Convert natural language into structured search instructions

**Outputs**
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

**Constraints**
- No free-text answers
- Deterministic schema validation required

---

### 3. Clarification Agent (AI Phase 4)

**Purpose**: Ask structured clarification questions when user intent is ambiguous

**Tier**: Tier 1 (p95 <80ms, structured JSON output)

**Triggered when**:
- Intent confidence < threshold (default: 0.7)
- Ambiguous or conflicting entities (e.g., multiple brands, conflicting filters)
- Zero results with low confidence query
- Ambiguous query classification (navigational vs informational)

**Output Schema** (Structured JSON):
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

**Behavior**:
- Ask exactly **one** clarification question (never multiple questions)
- Never guess user intent (always ask if ambiguous)
- Provide structured options (not free-text)
- Cache clarification requests (TTL: 1 hour)

**Clarification Types**:
1. **Brand Clarification**: "Which brand are you looking for?" (if multiple brands detected)
2. **Category Clarification**: "What type of product?" (if category ambiguous)
3. **Attribute Clarification**: "What size/color?" (if attribute ambiguous)
4. **Intent Clarification**: "Are you looking for a specific product or general recommendations?" (if intent ambiguous)

**Session Management**:
- Store clarification context in Redis (session key: `clarify:{session_id}`)
- TTL: 1 hour (session expires after 1 hour of inactivity)
- Include session_id in clarification response
- Use session_id in follow-up requests

**Integration**:
- Called by AI Orchestration Layer when confidence < threshold
- Returns clarification question (not search results)
- Frontend displays clarification UI
- User responds → new search with clarified intent

**Caching**:
- Cache clarification questions by query hash (key: `llm:clarify:{query_hash}`, TTL: 1 hour)
- Cache hit mandatory before LLM call

**Metrics**: Track clarification rate, clarification success rate, user abandonment after clarification

---

### 4. Response Composition Agent (AI Phase 2, Optional)

**Purpose**: Generate natural language explanations and summaries for search results and recommendations

**Tier**: Tier 2 (async, best-effort, never blocks user responses)

**Use Cases**:
1. **Product Description Generation**: Generate optimized product descriptions for better semantic search
2. **Result Summaries**: Summarize search results or recommendations
3. **Explanation Text**: Natural language explanation of ranking decisions (optional, async)

**Strict Rules**:
- Can only reference product IDs returned by retrieval pipelines (zero hallucination)
- Never create or speculate about products
- All content must be grounded in provided product data
- Async processing (never blocks search/recommendation responses)

#### Product Description Generation (Offline Batch)

**Purpose**: Generate optimized product descriptions for semantic search

**Process**:
1. **Input**: Product attributes (name, category, existing description)
2. **LLM Call**: Generate optimized description (Tier 2, GPT-4 or Claude Sonnet)
3. **Grounding Validation**: Verify description only references provided attributes
4. **Store**: Update product description in database
5. **Update Embeddings**: Trigger embedding regeneration for updated products

**Batch Job**: Run nightly (see `specs/BATCH_INFRASTRUCTURE.md`)

**Admin API**: `POST /admin/products/{id}/generate-description` (async, returns job ID)

**Grounding Validation**:
- Check that generated description only references provided product attributes
- Reject if description contains information not in product data
- Log validation failures for monitoring

**Cache**: Generated descriptions cached (key: `content:product:{product_id}`, TTL: 24 hours, invalidate on product update)

#### Result Summaries (Optional, Async)

**Purpose**: Generate natural language summaries of search results

**Process**:
1. **Input**: Search results (product IDs, scores, breakdowns)
2. **LLM Call**: Generate summary (Tier 2, async, best-effort)
3. **Grounding Validation**: Verify summary only references provided product IDs
4. **Store**: Cache summary (TTL: 5 minutes)
5. **Return**: Include summary in response if available (optional field)

**Response Field**: `summary` (nullable, async-populated)

**Example**:
```json
{
  "results": [...],
  "summary": "Found 42 running shoes, including popular Nike and Adidas models. Top results focus on comfort and durability."  // Optional, async
}
```

**Failure Handling**: If summary generation fails, response still returns results (no impact)

#### Explanation Text (Optional, Async)

**Purpose**: Natural language explanation of ranking decisions

**Process**:
1. **Input**: Ranking breakdown (scores, weights, product attributes)
2. **LLM Call**: Generate explanation (Tier 2, async, best-effort)
3. **Grounding Validation**: Verify explanation only references provided scores
4. **Store**: Cache explanation (key: `llm:explain:{product_id}:{breakdown_hash}`, TTL: 5 minutes)
5. **Return**: Include explanation in response if available (optional field)

**Response Field**: `explanation` (nullable, async-populated)

**Example**:
```json
{
  "product_id": "prod_123",
  "score": 0.87,
  "breakdown": {...},
  "explanation": "This product ranked highly due to strong keyword match and high collaborative filtering affinity."  // Optional, async
}
```

**Integration**: See `specs/API_CONTRACTS.md` for explainability endpoints

**Failure Handling**: If explanation generation fails, response still returns numeric breakdown (no impact)

#### Async Processing Patterns

**Pattern**: Fire-and-forget with best-effort population

**Flow**:
1. Search/recommendation service returns results immediately (with numeric breakdowns)
2. Background task generates explanation/summary (async)
3. If explanation available, include in response (optional field)
4. If explanation not available, response still complete (no blocking)

**Implementation**: Use background task queue (Celery, FastAPI background tasks, or similar)

**Cache**: All generated content cached to minimize LLM calls

**Cost Management**: 
- Target: <10% of requests generate explanations (cache hit rate >90%)
- Rate limit: Max 100 explanation requests per minute per user
- Cost monitoring: Track `llm_cost_usd_total` for Tier 2 agents

#### Grounding Validation

**Purpose**: Ensure zero hallucination (no product creation or speculation)

**Validation Rules**:
1. **Product References**: Only reference product IDs from retrieval results
2. **Attribute References**: Only reference attributes from product data
3. **Score References**: Only reference scores from ranking breakdown
4. **No Speculation**: Never create or guess product information

**Validation Process**:
1. Extract all product IDs mentioned in LLM output
2. Verify all IDs exist in retrieval results
3. Extract all attributes mentioned
4. Verify all attributes exist in product data
5. Reject if validation fails, log violation

**Metrics**: Track `llm_grounding_violations_total` for monitoring

**Alert**: If grounding violations >1% of requests, alert on-call

---

## Voice Interaction Flow

1. Speech-to-Text (external or on-device)
2. Immediate intent extraction
3. Discard raw transcript after intent extraction
4. Proceed using structured intent only

**Benefits**
- Lower cost
- Better privacy
- Faster pipelines

---

## Guardrails & Safety

### Grounding Rules
- All responses must reference retrieved product IDs
- No product creation or speculation

### Confidence Handling
- Low confidence → clarification
- Zero results → suggest reformulation

### Failure Modes

| Failure | Fallback |
|----|----|
| LLM timeout | Keyword + popularity |
| LLM error | Cached rewrite or rules |
| Ambiguous intent | Clarification |

---

## Caching Strategy (Critical)

| Layer | Key | TTL |
|----|----|----|
| Intent cache | hash(query) | 24h |
| Rewrite cache | hash(query) | 24h |
| Response cache | intent+filters | 5–10m |

Cache hit is mandatory before calling any LLM.

---

## Model Strategy

### Initial Phase
- External API or hosted LLM
- Strict token limits

### Evolution
- Distill logs → fine-tune small models
- Replace Tier 1 with local inference

---

## Observability & LLMOps Metrics

LLM behavior must be **first-class observable** via Prometheus.

### Core LLM Metrics

#### 1. Request Metrics
```
llm_requests_total{agent="intent", model="x"}
llm_errors_total{agent="rewrite", reason="timeout"}
```

#### 2. Latency Metrics
```
llm_latency_ms_bucket{agent="intent"}
llm_latency_ms_p95{agent="rewrite"}
```

#### 3. Cost & Token Metrics
```
llm_tokens_input_total{agent="intent"}
llm_tokens_output_total{agent="intent"}
llm_cost_usd_total{agent="intent"}
```

#### 4. Cache Effectiveness
```
llm_cache_hit_total{agent="rewrite"}
llm_cache_miss_total{agent="rewrite"}
```

#### 5. Quality & Confidence
```
llm_low_confidence_total{agent="intent"}
llm_clarification_triggered_total{}
```

---

## Suggested Alerts

| Alert | Condition |
|----|----|
| LLM latency spike | p95 > 150ms for 5m |
| LLM error rate | >1% for 2m |
| Cache hit drop | <60% for 10m |
| Token cost anomaly | 2x baseline |

---

## Alignment with Existing Stack

- Metrics: Prometheus
- Dashboards: Grafana
- Traces: OpenTelemetry spans per agent
- Logs: Structured JSON with `agent_name`, `model`, `confidence`

---

## Non-Goals

- Replacing ranking logic with LLMs
- Using LLMs for hard business decisions
- Chatbot-first UX

---

## Summary

This architecture:
- Preserves your **low-latency retrieval core**
- Adds **LLM intelligence only where it compounds value**
- Keeps **costs predictable and observable**
- Scales from MVP to global production

LLMs are treated as **augmenters, not dependencies**.

---

End of document
