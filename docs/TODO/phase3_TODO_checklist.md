# Phase 3: Performance & Resilience - TODO Checklist

**Goal**: Improve performance and handle failures gracefully. Critical before scaling.

**Timeline**: Weeks 11-16

**Status**: 
- ✅ **3.1 Semantic Search (FAISS)**: Core implementation COMPLETE
- ✅ **3.2 Collaborative Filtering**: Core implementation COMPLETE
- ⏳ **3.3 Feature Store**: NOT IMPLEMENTED
- ⏳ **3.4 Query Enhancement**: NOT IMPLEMENTED

---

## 3.1 Redis Caching Layer

### Setup & Configuration
- [ ] Install Redis client library (`redis` or `aioredis`)
- [ ] Add Redis client to `requirements.txt`
- [ ] Set up Redis instance (standalone or cluster)
- [ ] Create Redis client wrapper module (`app/core/cache.py`)
- [ ] Configure connection pooling
- [ ] Configure connection timeout and retry logic
- [ ] Add Redis connection health check

### Multi-Level Caching Strategy

#### Layer 1: Query Result Cache
- [ ] Design cache key format: `search:{query_hash}:{user_id}:{k}`
- [ ] Design cache key format: `recommend:{user_id}:{category}:{k}`
- [ ] Implement result serialization (JSON)
- [ ] Implement cache storage (TTL: 5 minutes)
- [ ] Implement cache retrieval
- [ ] Add cache invalidation on product updates
- [ ] Add cache invalidation on ranking weight changes
- [ ] Add manual cache invalidation endpoint (admin)

#### Layer 2: Feature Cache
- [ ] Design cache key format: `feature:{product_id}:{feature_name}`
- [ ] Design cache key format: `feature:{user_id}:{feature_name}`
- [ ] Implement feature value storage (TTL: 1 hour for products, 24 hours for users)
- [ ] Implement feature value retrieval
- [ ] Add cache invalidation on product updates
- [ ] Add cache invalidation on user events (after batch job)

#### Layer 3: Ranking Configuration Cache
- [ ] Design cache key format: `ranking:weights:{category}`
- [ ] Design cache key format: `ranking:config:global`
- [ ] Implement ranking weight storage (TTL: 1 day)
- [ ] Implement ranking weight retrieval
- [ ] Add cache invalidation on weight updates
- [ ] Add manual refresh endpoint

#### Layer 4: Popular Products Cache
- [ ] Design cache key format: `popular:{category}:{k}`
- [ ] Design cache key format: `popular:global:{k}`
- [ ] Implement popular products storage (TTL: 5 minutes)
- [ ] Implement popular products retrieval
- [ ] Add cache invalidation on popularity score updates

### Circuit Breaker Pattern
- [ ] Implement circuit breaker for Redis failures
- [ ] Configure failure threshold (5 consecutive failures)
- [ ] Implement bypass cache on circuit breaker open
- [ ] Add circuit breaker state metrics
- [ ] Log circuit breaker state changes
- [ ] Implement automatic recovery (test connection after 30 seconds)

### Cache Warming
- [ ] Identify popular queries for cache warming
- [ ] Create cache warming script
- [ ] Implement cache warming on application startup
- [ ] Schedule periodic cache warming (every 5 minutes)
- [ ] Add cache warming metrics

### Cache Invalidation
- [ ] Implement product update event handler
- [ ] Invalidate query result cache on product updates
- [ ] Invalidate feature cache on product updates
- [ ] Invalidate popular products cache on popularity updates
- [ ] Add cache invalidation metrics
- [ ] Log cache invalidation events

### Integration
- [ ] Create cache decorator for search endpoint
- [ ] Create cache decorator for recommendation endpoint
- [ ] Integrate cache into search service
- [ ] Integrate cache into recommendation service
- [ ] Integrate cache into ranking service (for weights)
- [ ] Integrate cache into feature service
- [ ] Add feature flag for caching (enable/disable)

### Testing
- [ ] Write unit tests for Redis client wrapper
- [ ] Write unit tests for cache key generation
- [ ] Write unit tests for cache storage/retrieval
- [ ] Write unit tests for cache invalidation
- [ ] Write unit tests for circuit breaker
- [ ] Write integration tests for cached search endpoint
- [ ] Write integration tests for cached recommendation endpoint
- [ ] Test cache hit scenarios
- [ ] Test cache miss scenarios
- [ ] Test cache invalidation scenarios
- [ ] Test circuit breaker (simulate Redis failures)
- [ ] Performance test: Cache hit latency
- [ ] Performance test: Cache miss latency

### Monitoring & Metrics
- [ ] Add metric: `cache_hits_total{cache_type, cache_layer}`
- [ ] Add metric: `cache_misses_total{cache_type, cache_layer}`
- [ ] Add metric: `cache_hit_rate{cache_type, cache_layer}` (calculated)
- [ ] Add metric: `cache_operation_latency_seconds{cache_type, operation}`
- [ ] Add metric: `cache_invalidations_total{cache_type, reason}`
- [ ] Add metric: `cache_circuit_breaker_state{cache_type}` (0=closed, 1=open, 2=half-open)
- [ ] Add Grafana dashboard for cache performance
- [ ] Log cache operations (hit/miss/invalidation)

### Success Criteria
- [ ] Cache hit rate > 70% for popular queries
- [ ] Cache operation latency < 5ms (p95)
- [ ] Circuit breaker prevents cascading failures
- [ ] Cache invalidation works correctly
- [ ] Cache warming improves initial performance

---

## 3.2 Rate Limiting

### Setup & Configuration
- [ ] Install rate limiting library (or implement custom)
- [ ] Create rate limiting middleware (`app/core/rate_limit.py`)
- [ ] Configure Redis for rate limiting counters
- [ ] Set up rate limit configuration per endpoint

### Per-IP Rate Limiting
- [ ] Implement sliding window counter for IP addresses
- [ ] Configure search endpoint: 100 requests/minute (burst: 150)
- [ ] Configure recommendation endpoint: 50 requests/minute (burst: 75)
- [ ] Implement burst handling (allow short spikes)
- [ ] Extract IP address from request headers (X-Forwarded-For)
- [ ] Handle IPv4 and IPv6 addresses

### Per-API-Key Rate Limiting
- [ ] Implement sliding window counter for API keys
- [ ] Configure search endpoint: 1000 requests/minute per key
- [ ] Configure recommendation endpoint: 500 requests/minute per key
- [ ] Extract API key from Authorization header
- [ ] Validate API key before rate limiting check
- [ ] Handle missing API key (fallback to IP rate limiting)

### Abuse Detection
- [ ] Implement same query detection (>20 times/minute)
- [ ] Implement sequential product_id enumeration detection
- [ ] Add abuse flagging mechanism
- [ ] Implement automatic throttling for abusive patterns
- [ ] Log abuse detection events
- [ ] Add metrics for abuse detection

### Response Handling
- [ ] Return `429 Too Many Requests` status code
- [ ] Add `Retry-After` header with seconds until retry
- [ ] Add rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- [ ] Return error message in response body
- [ ] Log rate limit violations

### Admin Endpoints
- [ ] Create admin endpoint: `POST /admin/rate-limit/whitelist` (add IP to whitelist)
- [ ] Create admin endpoint: `POST /admin/rate-limit/blacklist` (add IP to blacklist)
- [ ] Create admin endpoint: `GET /admin/rate-limit/status` (view rate limit status)
- [ ] Add authentication/authorization for admin endpoints
- [ ] Implement IP whitelist/blacklist storage (Redis)

### Testing
- [ ] Write unit tests for rate limiting logic
- [ ] Write unit tests for sliding window counter
- [ ] Write unit tests for abuse detection
- [ ] Write integration tests for rate limiting middleware
- [ ] Test per-IP rate limiting
- [ ] Test per-API-key rate limiting
- [ ] Test abuse detection
- [ ] Test rate limit response headers
- [ ] Test whitelist/blacklist functionality
- [ ] Load test: Verify rate limiting doesn't impact legitimate traffic

### Monitoring & Metrics
- [ ] Add metric: `rate_limit_hits_total{endpoint, type}` (IP or API key)
- [ ] Add metric: `rate_limit_abuse_detected_total{pattern}`
- [ ] Add metric: `rate_limit_whitelist_size`
- [ ] Add metric: `rate_limit_blacklist_size`
- [ ] Add Grafana dashboard for rate limiting
- [ ] Log rate limit violations

### Success Criteria
- [ ] Rate limiting prevents abuse (same query >20 times/minute blocked)
- [ ] Rate limiting doesn't impact legitimate users
- [ ] Admin endpoints allow IP management
- [ ] Rate limit metrics are tracked correctly

---

## 3.3 Circuit Breakers

**Status**: ✅ **Core implementation complete**.

**Implemented**:
- Implicit ALS model training and serving
- User-product interaction matrix building
- CF score computation and integration with ranking
- Cold start handling (new users/products)
- Prometheus metrics for CF scoring and cold start
- Comprehensive unit and integration tests

### Setup & Configuration
- [x] Install `implicit` library (Implicit ALS)
- [x] Install additional dependencies (numpy, scipy)
- [x] Add implicit and dependencies to `requirements.txt`
- [x] Create collaborative filtering service module (`app/services/recommendation/collaborative.py`)
- [x] Configure model parameters (factors, regularization, iterations)

### Data Preparation
- [x] Create data extraction script for user-product interactions
- [x] Query events table for user-product interaction matrix
- [x] Aggregate interactions by type (view, click, purchase) with weights
- [x] Handle implicit feedback (views, clicks) vs explicit (ratings)
- [x] Create sparse matrix representation (CSR format)
- [x] Add data validation (check for empty matrix, minimum interactions)
- [x] Create data preprocessing pipeline

### Model Training (Offline)
- [x] Create training script (`scripts/train_cf_model.py`)
- [x] Implement Implicit ALS model training
- [x] Configure hyperparameters (factors, regularization, iterations, alpha)
- [ ] Add cross-validation for hyperparameter tuning (optional enhancement)
- [x] Save model artifacts (user factors, item factors)
- [x] Save model metadata (training date, parameters, metrics)
- [ ] Create nightly batch job for model training (manual trigger for Phase 3.2)
- [x] Add model versioning
- [x] Handle training failures gracefully

### Model Artifact Storage
- [x] Set up model artifact storage (S3-compatible or local filesystem)
- [x] Create model registry structure
- [x] Implement model versioning system
- [x] Store model metadata (training metrics, parameters, date)
- [x] Create model loading service
- [x] Add model validation on load
- [ ] Implement model rollback capability (optional enhancement)

### Model Scoring (Online)
- [x] Create CF scoring service
- [x] Load model artifacts (user/item factors) on startup
- [x] Implement `user_product_affinity` score calculation
- [x] Compute scores for candidate products
- [ ] Cache user factors in Redis (TTL: 24 hours) (in-memory cache for Phase 3.2)
- [x] Handle missing users (cold start)
- [x] Handle missing products (cold start)
- [x] Optimize scoring for batch requests

### Cold Start Handling
- [x] Implement new user handling (use popularity-based recommendations)
- [x] Implement new product handling (use content-based/embedding similarity)
- [x] Create transition logic: After 5 interactions, use CF scores
- [x] Track user interaction count
- [ ] Blend CF scores with popularity scores during transition (optional enhancement)
- [x] Add cold start metrics (new user count, new product count)

### Integration with Recommendation Endpoint
- [x] Integrate CF scoring into recommendation endpoint
- [x] Combine CF scores with existing ranking features
- [x] Add CF as optional feature (feature flag)
- [x] Update recommendation response to include CF scores
- [x] Maintain backward compatibility
- [x] Update API documentation

### A/B Testing Setup
- [ ] Create A/B test framework for CF vs popularity baseline (future enhancement)
- [ ] Implement traffic splitting (50/50 or configurable)
- [ ] Track experiment metrics (CTR, CVR, engagement)
- [ ] Create experiment dashboard
- [ ] Add statistical analysis tools
- [ ] Document A/B test results

### Testing
- [x] Write unit tests for data preparation
- [x] Write unit tests for model training
- [x] Write unit tests for CF scoring
- [x] Write unit tests for cold start handling
- [x] Write integration tests for recommendation endpoint with CF
- [x] Test with sparse interaction matrix
- [x] Test with new users (cold start)
- [x] Test with new products (cold start)
- [ ] Verify CF recommendations show personalization (different users get different results) (manual testing)
- [x] Performance test: CF scoring latency

### Monitoring & Metrics
- [x] Add metrics: CF recommendation request count
- [x] Add metrics: CF scoring latency
- [ ] Add metrics: model training duration (logged, not exposed as metric)
- [x] Add metrics: cold start usage count
- [ ] Add metrics: A/B test metrics (CTR, CVR) (future enhancement)
- [ ] Track model performance over time (future enhancement)
- [x] Log CF recommendations and scores
- [x] Monitor model staleness (time since last training)

---

## 3.4 Database Optimization

### Connection Pooling
- [ ] Install async database client (`asyncpg` or `psycopg2`)
- [ ] Create database connection pool module (`app/core/database.py`)
- [ ] Configure connection pool size: 20 connections
- [ ] Configure max overflow: 10 connections
- [ ] Configure connection timeout
- [ ] Configure connection retry logic
- [ ] Add connection pool metrics

### Read Replicas
- [ ] Set up database read replicas (2-3 replicas)
- [ ] Create read/write splitting logic
- [ ] Route read queries (search, recommendations) to replicas
- [ ] Route write queries (events) to primary
- [ ] Implement replica selection (round-robin or least lag)
- [ ] Monitor replication lag
- [ ] Alert if replication lag >60 seconds
- [ ] Add read replica metrics

### Query Optimization
- [ ] Analyze slow queries using EXPLAIN ANALYZE
- [ ] Add database indexes for common queries:
  - [ ] Index on `products.category`
  - [ ] Index on `products.popularity_score`
  - [ ] Index on `events.user_id, events.product_id`
  - [ ] Index on `events.timestamp`
- [ ] Optimize N+1 query patterns
- [ ] Implement batch feature fetching
- [ ] Add query performance metrics
- [ ] Implement slow query logging (>100ms)

### Testing
- [ ] Write unit tests for connection pooling
- [ ] Write unit tests for read/write splitting
- [ ] Write integration tests for database queries
- [ ] Test connection pool exhaustion handling
- [ ] Test read replica failover
- [ ] Test query performance improvements
- [ ] Load test: Verify connection pool handles concurrent requests

### Monitoring & Metrics
- [ ] Add metric: `db_connection_pool_size{state}` (active, idle, waiting)
- [ ] Add metric: `db_query_duration_seconds{query_type}`
- [ ] Add metric: `db_slow_queries_total{query_type}`
- [ ] Add metric: `db_replication_lag_seconds{replica}`
- [ ] Add Grafana dashboard for database health
- [ ] Log slow queries

### Success Criteria
- [ ] Database connection pool never exhausted
- [ ] Read queries routed to replicas
- [ ] Query performance improved (p95 <100ms)
- [ ] Slow queries identified and optimized

---

## 3.5 Async/Await Optimization

### Async Database Client
- [ ] Convert database queries to async (use `asyncpg`)
- [ ] Update database service to async
- [ ] Update all database query functions to async
- [ ] Test async database queries

### Async Ranking Service
- [ ] Convert ranking service to async
- [ ] Update ranking functions to async
- [ ] Test async ranking operations

### Parallel Operations
- [ ] Parallelize feature fetching (fetch multiple features concurrently)
- [ ] Parallelize cache lookups (check multiple cache keys concurrently)
- [ ] Parallelize independent database queries
- [ ] Use `asyncio.gather` for concurrent operations
- [ ] Test parallel operations

### Performance Testing
- [ ] Benchmark synchronous vs asynchronous performance
- [ ] Measure throughput improvement (target: 2x)
- [ ] Measure latency improvement
- [ ] Load test: Verify async handles concurrent requests better

### Testing
- [ ] Write unit tests for async database client
- [ ] Write unit tests for async ranking service
- [ ] Write integration tests for parallel operations
- [ ] Test async error handling
- [ ] Test async timeout handling

### Monitoring & Metrics
- [ ] Add metric: `async_operation_duration_seconds{operation_type}`
- [ ] Add metric: `async_throughput_requests_per_second`
- [ ] Compare async vs sync performance metrics
- [ ] Add Grafana dashboard for async performance

### Success Criteria
- [ ] Throughput improved by 2x (compared to synchronous)
- [ ] Latency improved (p95 <200ms with cache)
- [ ] Async operations handle concurrent requests correctly
- [ ] No performance regressions

---

## Success Criteria Verification

### Cache hit rate > 70% for popular queries
- [ ] Measure cache hit rate for popular queries
- [ ] Verify cache hit rate > 70%
- [ ] Optimize cache warming if needed

### p95 latency < 200ms (with cache)
- [ ] Measure p95 latency with caching enabled
- [ ] Verify p95 latency < 200ms
- [ ] Optimize cache operations if needed

### Circuit breakers prevent cascading failures
- [ ] Simulate database failure → verify circuit breaker opens
- [ ] Simulate Redis failure → verify circuit breaker opens
- [ ] Verify fallback mechanisms work
- [ ] Verify system continues operating with degraded performance

### Rate limiting prevents abuse
- [ ] Test same query >20 times/minute → verify throttling
- [ ] Test sequential product_id enumeration → verify blocking
- [ ] Verify legitimate users not impacted

### Database connection pool never exhausted
- [ ] Load test: Verify connection pool handles concurrent requests
- [ ] Monitor connection pool metrics
- [ ] Verify no connection pool exhaustion errors

---

## Documentation

- [ ] Document Redis caching strategy
- [ ] Document rate limiting configuration
- [ ] Document circuit breaker configuration
- [ ] Document database optimization strategies
- [ ] Document async/await patterns
- [ ] Update architecture documentation
- [ ] Create developer guide for adding new cache layers

---

## Integration & Testing

- [ ] Integration test: End-to-end cached search flow
- [ ] Integration test: End-to-end rate-limited request flow
- [ ] Integration test: Circuit breaker with fallback
- [ ] Integration test: Database read/write splitting
- [ ] Load test: Verify performance improvements
- [ ] Test resilience: Simulate failures and verify graceful degradation

---

## Notes

- Caching is critical for performance - implement early
- Rate limiting prevents abuse and protects system
- Circuit breakers prevent cascading failures
- Database optimization reduces latency
- Async/await improves throughput
- Test each component independently before integration
- Monitor all performance metrics
- Document any deviations from the plan

---

## References

- Phase 3 specification: `/docs/TODO/implementation_plan.md` (Phase 3: Performance & Resilience)
- Caching strategy: `/specs/CACHING_STRATEGY.md`
- Architecture: `/specs/ARCHITECTURE.md`
- API contracts: `/specs/API_CONTRACTS.md`
- Observability: `/specs/OBSERVABILITY.md`

