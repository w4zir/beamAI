# RECOMMENDATION_DESIGN.md

## Purpose

This document defines the recommendation system design, including baseline models, collaborative filtering, and cold start strategies.

**Alignment**: Implements Phase 6.1 from `docs/TODO/implementation_phases.md`

---

## Baseline Models

### Global Popularity

**Purpose**: Recommend globally popular products (no personalization)

**Computation**: Weighted count of events (purchase > add_to_cart > view)

**Update Frequency**: 5-minute batch job

**Use Case**: 
- Cold start (new users, no interaction history)
- Fallback when personalized recommendations unavailable

**See**: `specs/FEATURE_DEFINITIONS.md` for `popularity_score` feature definition

### Category-Level Popularity

**Purpose**: Recommend popular products within user's preferred categories

**Computation**: Popularity score per category, weighted by user category affinity

**Update Frequency**: 5-minute batch job (popularity), daily (category affinity)

**Use Case**: 
- Light personalization (some user history)
- Category-specific recommendations

**See**: `specs/FEATURE_DEFINITIONS.md` for `user_category_affinity` feature definition

---

## Collaborative Filtering (Phase 6.1)

### Overview

**Purpose**: Provide personalized recommendations based on user-product interaction patterns

**Model**: Implicit ALS (Alternating Least Squares)

**Input**: User-product interaction matrix from events table

**Output**: User factors and item factors (embeddings)

**Training Frequency**: Daily (overnight batch job)

### Model Architecture

**Implicit ALS**:
- **Library**: `implicit` (Python)
- **Algorithm**: Alternating Least Squares for implicit feedback
- **Factors**: 50-100 dimensions (configurable)
- **Regularization**: L2 regularization (alpha parameter)

**Input Matrix**:
- **Rows**: Users (user_id)
- **Columns**: Products (product_id)
- **Values**: Interaction strength (weighted: purchase=3, add_to_cart=2, view=1)
- **Sparsity**: Filter users/products with <5 interactions

**Output**:
- **User Factors**: Matrix of user embeddings (N_users × factors)
- **Item Factors**: Matrix of item embeddings (N_products × factors)

### Training Pipeline

**Batch Job**: Daily (overnight, see `specs/BATCH_INFRASTRUCTURE.md`)

**Process**:
1. **Extract Interactions**: Query events table (last 90 days)
2. **Build Matrix**: Create user-product interaction matrix
3. **Filter Sparse**: Remove users/products with <5 interactions
4. **Train Model**: Run Implicit ALS training
5. **Extract Factors**: Save user factors and item factors
6. **Validate Model**: Test on holdout set (NDCG, precision@k)
7. **Deploy Model**: Store model artifacts (shadow mode first)

**Model Artifacts**:
- User factors (Parquet file or database table)
- Item factors (Parquet file or database table)
- Model metadata (factors, regularization, training date)

**Storage**: S3-compatible storage or local filesystem

**See**: `specs/BATCH_INFRASTRUCTURE.md` for detailed training pipeline

### Online Scoring

**Purpose**: Compute user-product affinity scores for real-time recommendations

**Scoring Formula**:
```python
user_product_affinity = dot(user_factors[user_id], item_factors[product_id])
```

**Process**:
1. Load user factors and item factors (in memory or cached)
2. For candidate products, compute dot product with user factors
3. Return affinity scores
4. Cache user factors in Redis (TTL: 24 hours)

**Performance**:
- Scoring latency: <10ms per product (with cached user factors)
- Batch scoring: Score 1000 products in <50ms

**Caching**:
- **User Factors**: Cache in Redis (key: `cf:user_factors:{user_id}`, TTL: 24 hours)
- **Item Factors**: Load in memory (or cache in Redis if memory constrained)

**See**: `specs/CACHING_STRATEGY.md` for caching details

### Feature Store Integration (Phase 6.2)

**Feature**: `user_product_affinity` (see `specs/FEATURE_DEFINITIONS.md`)

**Storage**:
- **Online**: Redis (for fast retrieval)
- **Offline**: Postgres or Parquet (for training data)

**Computation**:
- **Offline**: Batch job computes and stores affinity scores
- **Online**: Compute on-demand from user/item factors (faster, more flexible)

**Integration**:
- CF scores served via feature store API
- Batch fetch user affinities for multiple products
- Cache affinity scores in feature cache

**See**: `specs/FEATURE_STORE.md` for feature store architecture

---

## Cold Start Strategy

### New User (No Interaction History)

**Problem**: No user-product interactions → cannot compute CF scores

**Solution**: Multi-tier fallback strategy

**Tier 1: Category Affinity** (if available):
- Use user's category preferences (if provided during signup)
- Recommend popular products in preferred categories

**Tier 2: Global Popularity**:
- Recommend globally popular products
- No personalization, but high-quality recommendations

**Tier 3: Category Diversity**:
- Recommend diverse categories (electronics, fashion, books, etc.)
- Ensure variety in recommendations

**Transition**: After 5 interactions, switch to personalized CF recommendations

### New Product (No Interaction History)

**Problem**: No product interactions → cannot compute CF scores

**Solution**: Content-based recommendations

**Tier 1: Embedding Similarity**:
- Use product embeddings (semantic search)
- Recommend products similar to user's interacted products
- Compute similarity: `cosine_similarity(product_embedding, user_interacted_embeddings)`

**Tier 2: Category Match**:
- Recommend products in user's preferred categories
- Use category-level popularity

**Tier 3: Global Popularity**:
- Recommend globally popular products

**Transition**: After 10 views, product included in CF training

### Hybrid Approach

**Strategy**: Combine CF and content-based for cold start

**Formula**:
```python
if user_interactions < 5:
    score = 0.3 * cf_score + 0.7 * content_score
else:
    score = 0.7 * cf_score + 0.3 * content_score
```

**Benefits**:
- Smooth transition from cold start to personalized
- Better recommendations during cold start period
- Gradual increase in CF weight as user history grows

---

## Recommendation Pipeline

### Candidate Generation

**Step 1: Retrieve Candidates**:
- **CF Candidates**: Top-K products by user-product affinity (CF scores)
- **Popularity Candidates**: Top-K popular products
- **Category Candidates**: Top-K products in user's preferred categories

**Step 2: Merge Candidates**:
- Combine candidates from all sources
- Deduplicate products
- Limit to top 100-200 candidates

### Ranking

**Purpose**: Rank candidates using ranking formula

**Formula**: See `specs/RANKING_LOGIC.md`

**Features Used**:
- `user_product_affinity` (CF score)
- `popularity_score`
- `product_freshness_score`
- `user_category_affinity` (for category boost)

**Process**:
1. Fetch all features for candidates (batch fetch)
2. Compute ranking scores
3. Sort by final score
4. Return top-K results

**See**: `specs/RANKING_LOGIC.md` for detailed ranking formula

---

## Model Deployment

### Shadow Mode

**Purpose**: Test new CF model without user impact

**Process**:
1. Deploy new model alongside production model
2. Both models process requests (new model doesn't serve users)
3. Compare outputs: scores, rankings, metrics (NDCG, CTR)
4. If new model performs better, gradually roll out

**See**: `specs/TESTING_STRATEGY.md` for shadow mode details

### Gradual Rollout

**Strategy**: 
- Phase 1: Shadow mode (0% traffic)
- Phase 2: 10% traffic (experiment)
- Phase 3: 50% traffic (experiment)
- Phase 4: 100% traffic (full rollout)

**See**: `specs/EXPERIMENTATION.md` for A/B testing framework

---

## Performance Targets

### Recommendation Quality

- **NDCG@10**: >0.65 (minimum quality threshold)
- **Precision@10**: >0.3
- **Recall@10**: >0.2

### Latency

- **p50**: <50ms
- **p95**: <100ms
- **p99**: <200ms

### Coverage

- **Cold Start Coverage**: >80% of new users get recommendations
- **CF Coverage**: >90% of users with >5 interactions get CF recommendations

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 6.1)
- **Feature Definitions**: `specs/FEATURE_DEFINITIONS.md` (CF Features)
- **Feature Store**: `specs/FEATURE_STORE.md` (Feature Storage)
- **Batch Infrastructure**: `specs/BATCH_INFRASTRUCTURE.md` (CF Training)
- **Ranking Logic**: `specs/RANKING_LOGIC.md` (CF in Ranking)
- **Caching Strategy**: `specs/CACHING_STRATEGY.md` (CF Caching)

---

End of document

