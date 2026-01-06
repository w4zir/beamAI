# FEATURE_STORE.md

## Purpose

This document defines the feature store architecture, which serves as the single source of truth for ML features used in search, recommendations, and ranking. The feature store centralizes feature computation, storage, and serving.

**Alignment**: Implements Phase 6.2 from `docs/TODO/implementation_phases.md`

---

## Design Principles

1. **Single Source of Truth**: Features defined once, used everywhere
2. **Separation of Concerns**: Feature computation (offline) vs feature serving (online)
3. **Versioning**: Track feature versions for reproducibility
4. **Lineage**: Track feature dependencies and computation history
5. **Performance**: Fast feature retrieval for real-time serving

---

## Feature Store Architecture

### Components

**1. Feature Registry**
- Document all features (extend `specs/FEATURE_DEFINITIONS.md`)
- Feature metadata (name, type, description, computation)
- Feature versioning
- Feature lineage (dependencies)

**2. Feature Storage**
- **Online Features**: Redis (low latency, <10ms)
- **Offline Features**: Postgres or Parquet files (for training)
- **Feature Snapshots**: Point-in-time feature values (for model training)

**3. Feature Serving**
- API to fetch features by product_id/user_id
- Batch feature fetching (reduce N+1 queries)
- Feature caching layer
- Feature version selection

---

## Feature Registry

### Feature Metadata

**Required Fields**:
- `feature_name`: Canonical name (matches `FEATURE_DEFINITIONS.md`)
- `feature_type`: Type (float, string, vector, map)
- `description`: Human-readable description
- `computation`: How feature is computed (SQL, Python function, batch job)
- `source`: Data source (products table, events table, model output)
- `version`: Feature version (semantic versioning: 1.0.0, 1.1.0)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Optional Fields**:
- `dependencies`: Other features this depends on
- `staleness_tolerance`: Max acceptable staleness (e.g., 24 hours)
- `computation_frequency`: How often feature is recomputed (5 min, daily, weekly)
- `serving_location`: Where feature is served from (Redis, Postgres)

### Feature Versioning

**Version Format**: Semantic versioning (MAJOR.MINOR.PATCH)

**Version Rules**:
- **MAJOR**: Breaking change (schema change, type change)
- **MINOR**: Non-breaking change (new fields, computation improvement)
- **PATCH**: Bug fix (computation fix, no schema change)

**Version Selection**:
- Serving: Use latest compatible version
- Training: Use specific version (for reproducibility)
- A/B Testing: Use different versions per experiment

### Feature Lineage

**Purpose**: Track feature dependencies and computation history

**Lineage Graph**:
```
events table
    ↓
popularity_score (v1.0.0)
    ↓
user_category_affinity (v1.0.0) [depends on: popularity_score]
    ↓
cf_score (v1.0.0) [depends on: user_category_affinity, events]
```

**Use Cases**:
- Understand feature dependencies
- Impact analysis (if source data changes)
- Debugging feature computation
- Feature deprecation planning

---

## Feature Storage

### Online Features (Redis)

**Purpose**: Fast feature retrieval for real-time serving

**Storage Format**:
- **Key**: `feature:{feature_name}:{entity_id}:v{version}`
- **Value**: Feature value (JSON-serialized)
- **TTL**: Based on feature staleness tolerance

**Example**:
```
Key: feature:popularity_score:prod_123:v1.0.0
Value: 0.87

Key: feature:user_category_affinity:user_456:v1.0.0
Value: {"electronics": 0.9, "books": 0.3}
```

**Features Stored in Redis**:
- `popularity_score` (TTL: 5 minutes)
- `user_category_affinity` (TTL: 24 hours)
- `user_product_affinity` (TTL: 24 hours)
- `product_freshness_score` (TTL: 1 hour)

**Cache Strategy**: See `specs/CACHING_STRATEGY.md`

### Offline Features (Postgres/Parquet)

**Purpose**: Feature storage for training and batch processing

**Storage Format**:
- **Postgres**: Feature table with columns: `entity_id`, `feature_name`, `feature_value`, `version`, `timestamp`
- **Parquet**: Partitioned by date, columns: `entity_id`, `feature_name`, `feature_value`, `version`, `timestamp`

**Features Stored Offline**:
- All features (for training data)
- Historical feature snapshots (point-in-time values)
- Feature backfills (historical recomputation)

**Use Cases**:
- Model training (extract features for training set)
- Feature analysis (distribution, trends)
- Feature backfills (recompute historical features)

### Feature Snapshots

**Purpose**: Point-in-time feature values for model training

**Format**: Parquet files, partitioned by date

**Snapshot Frequency**: Daily (at midnight)

**Retention**: 1 year

**Use Cases**:
- Train models with historical features (avoid data leakage)
- Reproduce model training experiments
- Feature drift analysis

---

## Feature Serving

### API Design

**Single Feature Fetch**:
```python
async def get_feature(
    entity_id: str,
    feature_name: str,
    version: Optional[str] = None
) -> Any:
    """Get single feature value"""
    # 1. Check Redis cache
    # 2. If miss, check Postgres
    # 3. If miss, compute on-demand (if possible)
    # 4. Cache result
    # 5. Return value
```

**Batch Feature Fetch**:
```python
async def batch_get_features(
    entity_ids: List[str],
    feature_names: List[str],
    version: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """Get multiple features for multiple entities"""
    # Returns: {entity_id: {feature_name: value}}
    # Optimized: Single query per feature type
```

**Feature Service Interface**:
```python
class FeatureStore:
    async def get_feature(self, entity_id: str, feature_name: str) -> Any:
        """Get single feature"""
    
    async def batch_get_features(
        self, 
        entity_ids: List[str], 
        feature_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get multiple features"""
    
    async def get_feature_version(self, feature_name: str) -> str:
        """Get latest feature version"""
    
    async def list_features(self) -> List[FeatureMetadata]:
        """List all available features"""
```

### Feature Retrieval Flow

**1. Cache Check** (Redis):
- Check Redis for feature value
- If hit, return value (p95 <10ms)

**2. Database Check** (Postgres):
- If cache miss, query Postgres
- Cache result in Redis
- Return value

**3. On-Demand Computation** (if possible):
- If database miss and feature is computable on-demand
- Compute feature value
- Store in cache and database
- Return value

**4. Fallback**:
- If feature not available, return default value or None
- Log feature miss for monitoring

### Batch Feature Fetching

**Purpose**: Reduce N+1 queries

**Optimization**:
- Group features by source (products table, events table, etc.)
- Execute batch queries per source
- Combine results
- Cache all results

**Example**:
```python
# Fetch popularity_score for 100 products
# Bad: 100 queries
for product_id in product_ids:
    score = await get_feature(product_id, "popularity_score")

# Good: 1 query
scores = await batch_get_features(product_ids, ["popularity_score"])
```

**Performance**: Reduces 100 queries to 1-5 queries (depending on feature sources)

---

## Feature Migration

### Migration from Existing Feature Computation

**Current State**: Features computed inline in services

**Target State**: Features served from feature store

**Migration Steps**:

1. **Phase 1: Register Features**
   - Document all existing features in feature registry
   - Define feature metadata
   - Create feature version 1.0.0

2. **Phase 2: Batch Job Migration**
   - Move feature computation to batch jobs
   - Store features in feature store (Redis + Postgres)
   - Keep inline computation as fallback

3. **Phase 3: Serving Migration**
   - Update services to use feature store API
   - Remove inline feature computation
   - Monitor feature retrieval performance

4. **Phase 4: Cleanup**
   - Remove old feature computation code
   - Update documentation
   - Verify all features served from store

### Backward Compatibility

**Version Compatibility**:
- Support multiple feature versions during migration
- Gradually deprecate old versions
- Alert if old version usage detected

---

## Feature Quality

### Data Quality Checks

**Pre-Computation**:
- Validate input data (schema, completeness)
- Check data freshness
- Detect anomalies

**Post-Computation**:
- Validate feature distributions
- Check feature ranges (min/max)
- Detect feature drift

**Metrics**:
```
feature_quality_checks_total{feature_name="popularity_score", check_type="distribution", status="pass"}
feature_quality_checks_total{feature_name="popularity_score", check_type="distribution", status="fail"}
feature_drift_detected_total{feature_name="popularity_score"}
```

### Feature Monitoring

**Metrics**:
- Feature retrieval latency
- Feature cache hit rate
- Feature availability (feature present/absent)
- Feature staleness (time since last update)

**Alerts**:
- Feature retrieval latency >50ms → Warning
- Feature cache hit rate <60% → Warning
- Feature unavailable >5% of requests → Critical
- Feature staleness >staleness_tolerance → Warning

---

## Integration Points

### Search Service

**Features Used**:
- `search_keyword_score` (computed on-demand)
- `search_semantic_score` (computed on-demand)
- `popularity_score` (from feature store)
- `product_freshness_score` (from feature store)

**Integration**: Fetch features via feature store API before ranking

### Recommendation Service

**Features Used**:
- `user_category_affinity` (from feature store)
- `user_product_affinity` (from feature store, CF model output)
- `popularity_score` (from feature store)

**Integration**: Batch fetch user features for recommendation ranking

### Ranking Service

**Features Used**:
- All features required by ranking formula
- Batch fetch all features for candidate products

**Integration**: Use feature store batch API to fetch all features at once

### Batch Jobs

**Features Computed**:
- `popularity_score` (5-minute batch)
- `user_category_affinity` (daily batch)
- `user_product_affinity` (daily batch, CF model output)

**Integration**: Batch jobs compute features and store in feature store

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 6.2)
- **Feature Definitions**: `specs/FEATURE_DEFINITIONS.md` (Canonical Feature Definitions)
- **Caching Strategy**: `specs/CACHING_STRATEGY.md` (Feature Caching)
- **Batch Infrastructure**: `specs/BATCH_INFRASTRUCTURE.md` (Feature Computation Jobs)
- **Ranking Logic**: `specs/RANKING_LOGIC.md` (Feature Usage in Ranking)

---

End of document

