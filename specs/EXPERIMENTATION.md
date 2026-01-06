# EXPERIMENTATION.md

## Purpose

This document defines the A/B testing and experimentation framework for testing ranking algorithms, features, and UI changes. Experiments enable data-driven decisions and gradual rollouts.

**Alignment**: Implements Phase 8.1 from `docs/TODO/implementation_phases.md`

---

## Design Principles

1. **Statistical Rigor**: Proper sample sizes, statistical significance
2. **Traffic Splitting**: Fair, random assignment to variants
3. **Metrics Tracking**: Track experiment metrics (CTR, CVR, revenue)
4. **Gradual Rollout**: Start small, increase traffic gradually
5. **Safety First**: Automatic rollback on negative impact

---

## Experiment Framework Architecture

### Components

**1. Experiment Configuration**
- Define experiments (A/B tests)
- Specify variants (control, treatment)
- Set traffic split (50/50, 90/10, etc.)
- Define success metrics

**2. Traffic Splitting**
- Random assignment to variants
- Consistent assignment (same user → same variant)
- Per-user or per-request assignment

**3. Metrics Collection**
- Track experiment metrics (CTR, CVR, revenue)
- Track experiment exposures (who saw which variant)
- Aggregate metrics per variant

**4. Statistical Analysis**
- Calculate p-values, confidence intervals
- Determine statistical significance
- Identify winner (if significant)

---

## Experiment Types

### 1. Ranking Algorithm Experiments

**Purpose**: Test different ranking formulas or weights

**Example**: Test new ranking weights vs. current weights

**Variants**:
- **Control**: Current ranking weights [0.4, 0.3, 0.2, 0.1]
- **Treatment**: New ranking weights [0.3, 0.4, 0.2, 0.1]

**Metrics**: CTR, CVR, revenue, NDCG

### 2. Feature Experiments

**Purpose**: Test new features (semantic search, CF, etc.)

**Example**: Test semantic search vs. keyword-only search

**Variants**:
- **Control**: Keyword search only
- **Treatment**: Hybrid search (keyword + semantic)

**Metrics**: CTR, zero-result rate, search latency

### 3. UI Experiments

**Purpose**: Test UI changes (layout, colors, etc.)

**Example**: Test new product card layout

**Variants**:
- **Control**: Current UI
- **Treatment**: New UI

**Metrics**: CTR, engagement time, bounce rate

### 4. Parameter Tuning Experiments

**Purpose**: Test different parameter values

**Example**: Test different cache TTL values

**Variants**:
- **Control**: Cache TTL = 5 minutes
- **Treatment**: Cache TTL = 10 minutes

**Metrics**: Cache hit rate, latency, freshness

---

## Experiment Configuration

### Configuration Schema

```json
{
  "experiment_id": "ranking_weights_v2",
  "name": "Test New Ranking Weights",
  "description": "Test new ranking weights that emphasize CF scores",
  "status": "running",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-01-15T00:00:00Z",
  "traffic_split": {
    "control": 0.5,
    "treatment": 0.5
  },
  "variants": {
    "control": {
      "name": "Current Weights",
      "config": {
        "ranking_weights": [0.4, 0.3, 0.2, 0.1]
      }
    },
    "treatment": {
      "name": "New Weights",
      "config": {
        "ranking_weights": [0.3, 0.4, 0.2, 0.1]
      }
    }
  },
  "metrics": ["ctr", "cvr", "revenue", "ndcg"],
  "target_sample_size": 10000,
  "min_sample_size": 1000,
  "significance_level": 0.05
}
```

### Experiment States

**Draft**: Experiment defined but not running

**Running**: Experiment active, collecting data

**Paused**: Experiment temporarily paused (maintenance, issues)

**Completed**: Experiment finished, analyzing results

**Won**: Treatment variant significantly better

**Lost**: Treatment variant significantly worse or no difference

**Rolled Out**: Treatment variant rolled out to 100% traffic

---

## Traffic Splitting

### Assignment Strategy

**Per-User Assignment** (Recommended):
- Assign user to variant based on user_id hash
- Consistent assignment (same user → same variant)
- Benefits: Better user experience, cleaner analysis

**Per-Request Assignment** (Alternative):
- Assign request to variant randomly
- Benefits: Faster experiment completion
- Drawbacks: User sees different variants (confusing)

### Assignment Algorithm

**Hash-Based Assignment**:
```python
def assign_variant(user_id: str, experiment_id: str, traffic_split: Dict) -> str:
    """Assign user to variant based on hash"""
    hash_value = hash(f"{user_id}:{experiment_id}")
    hash_mod = hash_value % 100
    
    if hash_mod < traffic_split["control"] * 100:
        return "control"
    else:
        return "treatment"
```

**Benefits**:
- Deterministic (same user → same variant)
- Fair distribution (50/50 split)
- Easy to implement

### Traffic Splitting Strategies

**50/50 Split**: Equal traffic to control and treatment (standard)

**90/10 Split**: 90% control, 10% treatment (initial testing)

**10/90 Split**: 10% control, 90% treatment (gradual rollout)

**Custom Split**: Any ratio (e.g., 25/25/25/25 for 4 variants)

---

## Metrics Collection

### Experiment Exposure Tracking

**Table**: `experiment_exposures` (see `specs/DATA_MODEL.md`)

**Fields**:
- `experiment_id`: Experiment identifier
- `user_id`: User identifier (nullable for product-level experiments)
- `product_id`: Product identifier (nullable for user-level experiments)
- `variant`: Variant assigned (control, treatment)
- `exposed_at`: Timestamp of exposure

**Purpose**: Track who saw which variant for analysis

### Experiment Metrics

**Primary Metrics**:
- **CTR** (Click-Through Rate): Clicks / Impressions
- **CVR** (Conversion Rate): Purchases / Clicks
- **Revenue**: Total revenue per variant
- **NDCG** (Normalized Discounted Cumulative Gain): Ranking quality

**Secondary Metrics**:
- **Zero-Result Rate**: Zero-result searches / Total searches
- **Latency**: p95 latency per variant
- **Error Rate**: Errors / Total requests

### Metrics Aggregation

**Per Variant**:
- Aggregate metrics by variant (control vs. treatment)
- Calculate means, standard deviations
- Calculate confidence intervals

**Time Series**:
- Track metrics over time (daily, hourly)
- Detect trends and anomalies
- Identify when experiment reached significance

---

## Statistical Analysis

### Hypothesis Testing

**Null Hypothesis (H0)**: No difference between control and treatment

**Alternative Hypothesis (H1)**: Treatment is different from control

**Significance Level**: α = 0.05 (5% chance of false positive)

**Test Type**: Two-sample t-test or chi-square test (depending on metric type)

### Sample Size Calculation

**Formula**: Based on desired power (80%), effect size, significance level

**Minimum Sample Size**: 1000 per variant (for 80% power, medium effect size)

**Target Sample Size**: 10,000 per variant (for high confidence)

**Duration**: Run experiment until target sample size reached

### Statistical Significance

**P-Value**: Probability of observing results if null hypothesis true

**Significance Threshold**: p < 0.05 (statistically significant)

**Interpretation**:
- **p < 0.05**: Statistically significant (reject null hypothesis)
- **p >= 0.05**: Not statistically significant (fail to reject null hypothesis)

### Confidence Intervals

**Purpose**: Estimate range of true effect size

**Confidence Level**: 95% (standard)

**Interpretation**: 95% confident true effect size is within interval

**Example**: CTR difference: 2.5% ± 0.5% (95% CI: 2.0% to 3.0%)

---

## Experiment Endpoints

### Create Experiment

**Endpoint**: `POST /experiments`

**Request Body**:
```json
{
  "name": "Test New Ranking Weights",
  "description": "Test new ranking weights",
  "traffic_split": {"control": 0.5, "treatment": 0.5},
  "variants": {
    "control": {"config": {"ranking_weights": [0.4, 0.3, 0.2, 0.1]}},
    "treatment": {"config": {"ranking_weights": [0.3, 0.4, 0.2, 0.1]}}
  },
  "metrics": ["ctr", "cvr", "revenue"]
}
```

**Response**: Experiment configuration with `experiment_id`

### Get Experiment

**Endpoint**: `GET /experiments/{experiment_id}`

**Response**: Experiment configuration and current status

### Assign Variant

**Endpoint**: `POST /experiments/{experiment_id}/assign`

**Request Body**:
```json
{
  "user_id": "user_123",
  "context": {"query": "running shoes", "source": "search"}
}
```

**Response**:
```json
{
  "variant": "treatment",
  "config": {"ranking_weights": [0.3, 0.4, 0.2, 0.1]}
}
```

**Usage**: Called by search/recommendation services to get experiment variant

### Get Experiment Results

**Endpoint**: `GET /experiments/{experiment_id}/results`

**Response**:
```json
{
  "experiment_id": "ranking_weights_v2",
  "status": "completed",
  "sample_size": {
    "control": 10000,
    "treatment": 10000
  },
  "metrics": {
    "ctr": {
      "control": 0.15,
      "treatment": 0.17,
      "difference": 0.02,
      "p_value": 0.03,
      "significant": true,
      "confidence_interval": [0.01, 0.03]
    },
    "cvr": {
      "control": 0.05,
      "treatment": 0.06,
      "difference": 0.01,
      "p_value": 0.08,
      "significant": false
    }
  },
  "winner": "treatment",
  "recommendation": "rollout"
}
```

### Update Experiment

**Endpoint**: `PUT /experiments/{experiment_id}`

**Purpose**: Update experiment configuration (traffic split, status, etc.)

**Security**: Admin-only

---

## Shadow Mode Integration

### Shadow Mode Testing

**Purpose**: Test new models/algorithms without user impact

**Process**:
1. Deploy new model alongside production model
2. Both models process requests (new model doesn't serve users)
3. Compare outputs: scores, rankings, metrics
4. If new model performs better, gradually roll out

**Integration with Experiments**:
- Use shadow mode for initial testing
- If shadow mode shows improvement, create experiment
- Gradually roll out via experiment traffic split

**See**: `specs/TESTING_STRATEGY.md` for shadow mode details

---

## Gradual Rollout

### Rollout Strategy

**Phase 1: Shadow Mode** (0% traffic):
- Test new variant in shadow mode
- Compare metrics with production
- Verify no errors or issues

**Phase 2: Small Experiment** (10% traffic):
- Run experiment with 10% traffic
- Monitor metrics closely
- Verify statistical significance

**Phase 3: Medium Experiment** (50% traffic):
- Increase to 50% traffic
- Continue monitoring
- Verify metrics hold at scale

**Phase 4: Full Rollout** (100% traffic):
- Roll out to 100% traffic
- Monitor for 24-48 hours
- Keep experiment active for rollback safety

**Phase 5: Complete**:
- Mark experiment as "rolled out"
- Remove experiment code
- Update production configuration

### Automatic Rollback

**Conditions** (any of the following):
- Error rate >1% for 2 minutes
- CTR drop >10% (statistically significant)
- Revenue drop >5% (statistically significant)
- Critical bug detected

**Action**: Automatically rollback to control variant

**Notification**: Alert on-call engineer

---

## Multi-Armed Bandit (Future)

### Adaptive Experimentation

**Purpose**: Automatically adjust traffic split based on performance

**Algorithm**: Multi-armed bandit (Thompson Sampling or UCB)

**Benefits**:
- Faster experiment completion
- Automatically favor better variant
- Reduce exposure to worse variant

**Use Case**: Testing multiple variants simultaneously

**Implementation**: Future enhancement (Phase 8.2)

---

## Experiment Best Practices

### Do's

- **Run experiments long enough**: Minimum 1 week, target 2 weeks
- **Use proper sample sizes**: Minimum 1000 per variant
- **Track multiple metrics**: Primary and secondary metrics
- **Monitor closely**: Check metrics daily during experiment
- **Document decisions**: Document why experiment was created, what was tested

### Don'ts

- **Don't peek early**: Don't stop experiment early based on preliminary results
- **Don't test too many things**: Focus on one change per experiment
- **Don't ignore statistical significance**: Don't roll out without significance
- **Don't skip shadow mode**: Always test in shadow mode first
- **Don't forget rollback plan**: Always have rollback strategy

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 8.1)
- **Data Model**: `specs/DATA_MODEL.md` (experiment_exposures table)
- **Testing Strategy**: `specs/TESTING_STRATEGY.md` (Shadow Mode)
- **Ranking Logic**: `specs/RANKING_LOGIC.md` (Ranking Experiments)

---

End of document

