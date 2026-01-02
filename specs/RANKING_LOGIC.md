## Feature Name Mapping

This document uses shortened feature names for readability. The following mapping references the canonical feature names defined in `/specs/FEATURE_DEFINITIONS.md`:

| Ranking Formula Name | Canonical Feature Name | Source Document |
|---------------------|----------------------|-----------------|
| `search_score` | Combined from `search_keyword_score` and `search_semantic_score` | See Search Score Combination below |
| `cf_score` | `user_product_affinity` | FEATURE_DEFINITIONS.md line 107 |
| `popularity_score` | `popularity_score` | FEATURE_DEFINITIONS.md line 69, DATA_MODEL.md line 22 |
| `freshness_score` | `product_freshness_score` | FEATURE_DEFINITIONS.md line 81 |

### Search Score Combination

The `search_score` used in the ranking formula is computed as follows:

- **For search queries:** `search_score = max(search_keyword_score, search_semantic_score)`
  - If both keyword and semantic search are performed, use the higher score
  - This ensures the best match (whether exact keyword or semantic similarity) is emphasized
- **For recommendations:** `search_score = 0` (not applicable)

This approach prioritizes the strongest signal between keyword matching (exact/partial text matches) and semantic matching (meaning-based similarity).

### Collaborative Filtering Score

The `cf_score` in the ranking formula maps directly to the `user_product_affinity` feature defined in FEATURE_DEFINITIONS.md. This feature represents the strength of a user's interaction with a product, computed from collaborative filtering model output (Implicit ALS as specified in RECOMMENDATION_DESIGN.md).

---

## Ranking Formula Evolution

### Phase 1: Global Weights (Current)
```python
final_score = (
    0.4 * search_score +
    0.3 * cf_score +
    0.2 * popularity_score +
    0.1 * freshness_score
)
```

### Phase 2: Category-Specific Weights (6 months)
```python
# Electronics: Emphasize freshness (new models matter)
if category == 'electronics':
    weights = [0.3, 0.3, 0.1, 0.3]
# Fashion: Emphasize trends
elif category == 'fashion':
    weights = [0.3, 0.2, 0.4, 0.1]
# Books: Emphasize CF (taste-based)
elif category == 'books':
    weights = [0.3, 0.5, 0.1, 0.1]
```

### Phase 3: Learned Weights (12 months)
```python
# Train a meta-model to predict optimal weights
# Input: user features, query features, context
# Output: weight vector [w1, w2, w3, w4]
weights = meta_model.predict(user, query, context)
final_score = weights @ feature_vector
```

### Configuration Management
- Store weights in Redis (fast lookup)
- Override via experiment flags
- Default fallback to global 

## Ranking Explainability

For debugging and user trust, log ranking decisions:
```json
{
  "product_id": "prod_123",
  "final_score": 0.87,
  "breakdown": {
    "search_score": 0.92,
    "cf_score": 0.78,
    "popularity_score": 0.85,
    "freshness_score": 0.95
  },
  "weights": [0.4, 0.3, 0.2, 0.1],
  "reason": "Strong keyword match + high collaborative filtering affinity"
}
```