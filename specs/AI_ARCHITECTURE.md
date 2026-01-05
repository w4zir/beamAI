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

### 3. Clarification Agent

**Triggered when**
- Intent confidence < threshold
- Ambiguous or conflicting entities

**Behavior**
- Ask exactly **one** clarification question
- Never guess user intent

---

### 4. Response Composition Agent (Optional)

**Purpose**
- Explain results to users
- Summarize recommendations

**Strict Rule**
- Can only reference product IDs returned by retrieval pipelines

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
