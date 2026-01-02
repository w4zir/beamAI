# FEATURE_DEFINITIONS.md

## Purpose

This document defines all **features used by search, recommendation, and ranking**.
It specifies:
- What each feature represents
- How it is computed
- Where it is computed
- Where it may be used

This is the **single source of truth** for features.

---

## Feature Principles

- Features are computed **offline or asynchronously**
- Serving systems only **read features**
- No feature computation inside FastAPI request handlers
- Feature definitions must be stable across environments

---

## Feature Categories

1. User Features
2. Product Features
3. Interaction Features
4. Search Features
5. Contextual Features

---

## 1️⃣ User Features

### user_id
- Type: string
- Source: users.id
- Description: Canonical user identifier

---

### user_category_affinity
- Type: map<string, float>
- Description: User preference strength per category
- Computation:
  - Count of interactions per category
  - Time-decayed
- Computed: Offline batch job
- Used by:
  - Recommendation ranking
  - Personalized search reranking

---

### user_activity_level
- Type: float
- Description: Normalized activity score
- Computation:
  - Number of events in last N days
- Used by:
  - Cold-start detection

---

## 2️⃣ Product Features

### popularity_score
- Type: float
- Description: Global popularity of product
- Computation:
  - Weighted count of events (purchase > add_to_cart > view)
- Computed: Offline batch
- Used by:
  - Recommendations
  - Search ranking fallback

---

### product_freshness_score
- Type: float
- Description: Recency-based boost
- Computation:
  - Time decay from created_at
- Used by:
  - Ranking service only

---

### product_embedding
- Type: vector<float>
- Dimension: 384
- Source:
  - SentenceTransformer embeddings
- Computed: Offline
- Stored:
  - FAISS index
- Used by:
  - Semantic search
  - Content-based recommendation

---

## 3️⃣ Interaction Features

### user_product_affinity
- Type: float
- Description: Strength of user’s interaction with product
- Source:
  - Collaborative filtering model output
- Used by:
  - Recommendation ranking

---

### recent_user_events
- Type: list<event>
- Description: Last N interactions
- Used by:
  - Session-based heuristics (optional)

---

## 4️⃣ Search Features

### search_keyword_score
- Type: float
- Description: Relevance score from Postgres FTS
- Computed: Query time (cheap)
- Used by:
  - Ranking service

---

### search_semantic_score
- Type: float
- Description: Similarity score from FAISS
- Computed: Query time (cheap)
- Used by:
  - Ranking service

---

## 5️⃣ Contextual Features

### request_timestamp
- Type: timestamp
- Description: Time of request
- Used by:
  - Freshness weighting

---

### request_source
- Type: enum
- Values:
  - search
  - recommendation
  - direct
- Used by:
  - Analytics
  - Bias detection

---

## Explicit Non-Goals

- No online feature learning
- No feature joins inside FastAPI routes
- No ad-hoc feature creation without updating this document

---

## Change Management

- Any new feature MUST be added here
- Feature removal requires:
  - Ranking update
  - Model retraining
- Feature renaming is treated as breaking change

---

## Feature Computation Schedule

### Real-Time (sub-second)
- search_keyword_score: Computed on-demand (Postgres FTS is fast)
- search_semantic_score: Computed on-demand (FAISS lookup)

### Near Real-Time (5-minute batch)
- popularity_score: Rolling window aggregation
- trending_products: Spike detection on recent events

### Daily Batch (overnight)
- user_category_affinity: Compute from last 90 days of events
- product_embeddings: Regenerate if product descriptions change
- collaborative_filtering_scores: Retrain model

### Weekly Batch
- FAISS index rebuild: Incorporate new products

## Cold Start Handling

### New User (no events)
- user_category_affinity: NULL → use global category popularity
- CF scores: NULL → use content-based recommendations
- Transition: After 5 interactions, switch to personalized

### New Product (no interactions)
- popularity_score: Default to 0.1 (low but not zero)
- CF scores: Use content-based embedding similarity
- Transition: After 10 views, compute real popularity

## Staleness Tolerance

| Feature | Max Staleness | Impact if Stale |
|---------|---------------|-----------------|
| user_category_affinity | 24 hours | Minor: Slightly worse recs |
| product_popularity | 5 minutes | Medium: Trending items missed |
| search_semantic_score | 7 days | Minor: New products not searchable semantically |
| CF scores | 24 hours | Medium: Personalization degrades |

---

## Mental Model

> Models change often.  
> Features must be boring and stable.
