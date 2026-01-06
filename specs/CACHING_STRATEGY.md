# CACHING_STRATEGY.md

## Purpose

This document defines the multi-level caching strategy for the search and recommendation system. Caching is critical for performance, reducing database load, and enabling low-latency responses.

**Alignment**: Implements Phase 3.1 from `docs/TODO/implementation_phases.md`

---

## Design Principles

1. **Cache-First Strategy**: Always check cache before expensive operations
2. **Graceful Degradation**: System must function if cache is unavailable
3. **Cache Invalidation**: Explicit invalidation on data changes
4. **Circuit Breaker**: Automatic fallback on cache failures
5. **Observability**: All cache operations are monitored and logged

---

## Multi-Level Caching Architecture

### Layer 1: Query Result Cache

**Purpose**: Cache complete search/recommendation results to avoid recomputation

**Key Format**: `search:{query_hash}:{user_id}:{k}` or `recommend:{user_id}:{category}:{k}`

**Value**: Serialized list of ranked product results (JSON)

**TTL**: 5 minutes

**Invalidation**:
- Product updates (price, availability, description)
- Ranking weight changes
- Manual invalidation via admin API

**Example**:
```
Key: search:abc123def456:user_789:10
Value: [{"product_id": "prod_1", "score": 0.95}, ...]
```

### Layer 2: Feature Cache

**Purpose**: Cache computed features to avoid repeated database queries

**Key Format**: `feature:{product_id}:{feature_name}` or `feature:{user_id}:{feature_name}`

**Value**: Feature value (float, string, or JSON)

**TTL**: 
- Product features: 1 hour
- User features: 24 hours
- Popularity scores: 5 minutes

**Invalidation**:
- Product updates → invalidate all product features
- User events → invalidate user features after batch job
- Feature recomputation → invalidate specific feature

**Example**:
```
Key: feature:prod_123:popularity_score
Value: 0.87

Key: feature:user_456:category_affinity
Value: {"electronics": 0.9, "books": 0.3}
```

### Layer 3: Ranking Configuration Cache

**Purpose**: Cache ranking weights and configuration to avoid database lookups

**Key Format**: `ranking:weights:{category}` or `ranking:config:global`

**Value**: Ranking weight vector or configuration JSON

**TTL**: 1 day (or until manual refresh)

**Invalidation**:
- Ranking weight updates (admin API)
- Experiment configuration changes
- Manual refresh endpoint

**Example**:
```
Key: ranking:weights:electronics
Value: {"search_score": 0.3, "cf_score": 0.3, "popularity_score": 0.1, "freshness_score": 0.3}
```

### Layer 4: Popular Products Cache

**Purpose**: Cache top-K popular products per category for fast recommendations

**Key Format**: `popular:{category}:{k}` or `popular:global:{k}`

**Value**: List of product IDs with scores

**TTL**: 5 minutes

**Invalidation**:
- Popularity score batch job completion
- Product availability changes
- Manual refresh

**Example**:
```
Key: popular:electronics:20
Value: [{"product_id": "prod_1", "score": 0.99}, ...]
```

### Layer 5: LLM Cache (AI Integration)

**Purpose**: Cache LLM outputs to minimize API calls and costs

**Key Format**: 
- Intent: `llm:intent:{query_hash}`
- Rewrite: `llm:rewrite:{query_hash}`
- Clarification: `llm:clarify:{intent_hash}`
- Explanation: `llm:explain:{product_id}:{breakdown_hash}`

**Value**: LLM response (JSON)

**TTL**:
- Intent/Rewrite: 24 hours
- Clarification: 1 hour
- Explanation: 5 minutes
- Content generation: 24 hours (invalidated on product update)

**Invalidation**:
- Manual refresh (admin API)
- Product updates (for content cache)
- Cache warming scripts

**Alignment**: See `specs/AI_ARCHITECTURE.md` for LLM caching details

---

## Redis Integration

### Connection Pooling

**Configuration**:
- Pool size: 20 connections
- Max overflow: 10 connections
- Connection timeout: 5 seconds
- Retry attempts: 3

**Implementation**: Use `redis-py` with connection pool or `aioredis` for async

### Key Naming Conventions

**Format**: `{layer}:{identifier}:{optional_params}`

**Rules**:
- Use colons (`:`) as separators
- Lowercase only
- No spaces or special characters
- Include version in key if schema changes (e.g., `v1:feature:...`)

**Examples**:
- ✅ `search:abc123:user_789:10`
- ✅ `feature:prod_123:popularity_score`
- ❌ `Search:ABC123:User_789` (uppercase, wrong format)

### Serialization

**Format**: JSON (human-readable, debuggable)

**Alternative**: MessagePack (for large values, 30% size reduction)

**Compression**: Consider gzip for values >10KB

---

## Cache Invalidation Strategies

### 1. Time-Based Expiration (TTL)

**Use Case**: Default strategy for all caches

**Implementation**: Set TTL on write, Redis auto-expires

**Pros**: Simple, automatic cleanup

**Cons**: Stale data until expiration

### 2. Event-Based Invalidation

**Use Case**: Product updates, feature recomputation

**Events**:
- `product.updated` → Invalidate product features, query results containing product
- `ranking.weights.updated` → Invalidate ranking config cache
- `popularity.recomputed` → Invalidate popular products cache
- `user.events.created` → Invalidate user features (after batch job)

**Implementation**: Publish events to message queue, cache service subscribes

### 3. Manual Invalidation

**Use Case**: Admin operations, debugging

**Endpoints**:
- `POST /admin/cache/invalidate?pattern={key_pattern}`
- `POST /admin/cache/invalidate/product/{product_id}`
- `POST /admin/cache/invalidate/user/{user_id}`
- `POST /admin/cache/invalidate/all`

**Security**: Admin-only, requires authentication

### 4. Cache Warming

**Purpose**: Pre-populate cache with popular queries/products

**Strategies**:
- **On Startup**: Load top 100 popular queries, top 50 products per category
- **Scheduled**: Run every 5 minutes for trending queries
- **On-Demand**: Admin-triggered warming for specific queries

**Implementation**: Background job that queries database and populates cache

---

## Circuit Breaker Pattern

### Configuration

**Failure Threshold**: 5 consecutive failures or 50% error rate over 1 minute

**Open Duration**: 30 seconds

**Half-Open**: Test with 10% of requests

**Recovery**: Automatic after successful test requests

### Behavior

**Closed (Normal)**:
- All requests go through cache
- Monitor error rate

**Open (Cache Down)**:
- All requests bypass cache
- Direct database queries
- Log cache failures
- Alert on-call

**Half-Open (Testing)**:
- 10% of requests test cache
- If successful, close circuit
- If failed, reopen circuit

### Fallback Strategy

**Cache Miss/Failure**:
1. Try cache (with timeout: 50ms)
2. If failure, log and continue
3. Query database directly
4. Return results (no caching on failure)

**Impact**: Higher latency (200ms → 500ms) but system remains functional

---

## Metrics and Monitoring

### Cache Performance Metrics

**Prometheus Metrics**:
```
cache_hits_total{cache_layer="query_result", cache_type="search"}
cache_misses_total{cache_layer="query_result", cache_type="search"}
cache_hit_rate{cache_layer="query_result"}  # Calculated: hits / (hits + misses)
cache_latency_seconds{cache_layer="query_result"}  # Histogram
cache_errors_total{cache_layer="query_result", reason="timeout"}
cache_circuit_breaker_state{cache_layer="query_result"}  # 0=closed, 1=open, 2=half-open
```

### Target Metrics

- **Cache Hit Rate**: >70% for query results, >80% for features
- **Cache Latency**: p95 <10ms
- **Cache Error Rate**: <0.1%

### Grafana Dashboards

**Cache Performance Dashboard**:
- Hit rate by layer
- Latency percentiles
- Error rate
- Circuit breaker state
- Cache size (memory usage)

**Alerts**:
- Cache hit rate <60% for 10 minutes → Warning
- Cache error rate >1% for 2 minutes → Critical
- Circuit breaker open for 5 minutes → Critical

---

## Implementation Guidelines

### Redis Client Wrapper

**Requirements**:
- Connection pooling
- Automatic retries
- Circuit breaker integration
- Metrics collection
- Error handling and logging

**Example Interface**:
```python
class CacheClient:
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache, return None if miss or error"""
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in cache with TTL, return success"""
    
    async def delete(self, pattern: str) -> int:
        """Delete keys matching pattern, return count"""
    
    async def invalidate_product(self, product_id: str) -> None:
        """Invalidate all cache entries for product"""
```

### Cache Decorators

**Usage**: Decorate search/recommendation endpoints

**Example**:
```python
@cache_result(ttl=300, key_fn=lambda q, u, k: f"search:{hash(q)}:{u}:{k}")
async def search(query: str, user_id: str, k: int):
    # Implementation
    pass
```

**Features**:
- Automatic key generation
- TTL configuration
- Cache hit/miss logging
- Metrics collection

---

## Cache Warming Scripts

### Startup Warming

**Script**: `scripts/warm_cache.py`

**Actions**:
1. Load top 100 popular queries from analytics
2. Load top 50 products per category
3. Pre-compute and cache results
4. Log warming progress

**Run**: On application startup (background task)

### Scheduled Warming

**Script**: `scripts/warm_trending_cache.py`

**Actions**:
1. Query trending queries (last 1 hour)
2. Pre-compute and cache results
3. Run every 5 minutes

**Schedule**: Cron job or Airflow DAG

---

## Security Considerations

### Cache Key Isolation

**Tenant Isolation**: Include tenant_id in cache keys for multi-tenant deployments

**User Isolation**: Include user_id in cache keys for personalized results

### Sensitive Data

**Rule**: Never cache PII or sensitive user data

**Allowed**: Product IDs, scores, feature values (non-PII)

**Prohibited**: User emails, addresses, payment info

---

## Migration Strategy

### Phase 1: Cache-Aside Pattern

1. Check cache
2. If miss, query database
3. Store in cache
4. Return result

### Phase 2: Write-Through (Future)

1. Write to database
2. Update cache immediately
3. Return success

**Use Case**: High consistency requirements

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 3.1)
- **Architecture**: `specs/ARCHITECTURE.md` (Failure Modes)
- **AI Architecture**: `specs/AI_ARCHITECTURE.md` (LLM Caching)
- **Observability**: `specs/OBSERVABILITY.md` (Metrics)

---

End of document

