# ARCHITECTURE.md

## High-Level Components

- **FastAPI Gateway**
  - Request validation
  - Orchestration only

- **Search Service**
  - Keyword (Postgres FTS)
  - Semantic (FAISS)
  - Candidate retrieval only

- **Recommendation Service**
  - Popularity-based
  - Collaborative filtering
  - Candidate retrieval only

- **Ranking Service**
  - Deterministic scoring
  - Business rules
  - Final ordering

## Dependency Rules
- FastAPI must not contain business logic
- Training code must never be imported into API runtime
- Ranking must not call external services

## Failure Modes & Graceful Degradation

### Scenario 1: Ranking Service Down
- Fallback: Return candidates sorted by popularity_score
- User Impact: Worse personalization, but search works
- Detection: Health check every 10s
- Recovery: Auto-restart, alert after 3 failures

### Scenario 2: Redis Cache Down
- Fallback: Query Postgres directly (slower)
- User Impact: Higher latency (200ms → 500ms)
- Mitigation: Circuit breaker after 5 failures
- Recovery: Manual intervention, verify data integrity

### Scenario 3: FAISS Index Corrupted
- Fallback: Keyword search only
- User Impact: No semantic search
- Detection: Index load failure on startup
- Recovery: Rebuild from latest model artifacts (30 min)

### Scenario 4: Postgres Read Replica Lag
- Fallback: Read from primary (increased load)
- User Impact: Slightly stale recommendations
- Detection: Replication lag > 60s
- Recovery: Wait for catch-up or promote new replica

## Circuit Breaker Pattern
- Failure threshold: 50% error rate over 1 minute
- Open duration: 30 seconds
- Half-open: Test with 10% traffic

---

## Database Optimization (Phase 3.4)

**Alignment**: See `specs/DATABASE_OPTIMIZATION.md` for detailed database optimization strategies

### Connection Pooling

**Purpose**: Minimize connection overhead and prevent connection exhaustion

**Configuration**:
- Pool size: 20 connections
- Max overflow: 10 connections
- Connection timeout: 5 seconds
- Max lifetime: 1 hour

**Implementation**: Use `asyncpg` (async) or `psycopg2` with SQLAlchemy (sync)

**Monitoring**: Track pool size, wait time, exhaustion events

### Read/Write Splitting

**Purpose**: Distribute read load across replicas, reduce primary database load

**Routing Logic**:
- **Read Queries**: Route to read replicas (search, recommendations, feature fetching)
- **Write Queries**: Route to primary (events, product updates)
- **Transaction Queries**: Route to primary (read-after-write consistency)

**Replication Lag**: Monitor and alert if >60 seconds

**Fallback**: Route reads to primary if replica lag >60s or replica unhealthy

### Query Optimization

**Strategies**:
- Add indexes for common query patterns
- Use EXPLAIN ANALYZE to identify slow queries
- Batch operations to prevent N+1 queries
- Slow query logging (>100ms)

**See**: `specs/DATABASE_OPTIMIZATION.md` for detailed query optimization guidelines

---

## Async/Await Optimization (Phase 3.5)

**Purpose**: Handle more concurrent requests with same resources through asynchronous I/O

### Async Database Client

**Implementation**: Use `asyncpg` for async database operations

**Benefits**:
- Non-blocking I/O (can handle other requests while waiting for database)
- Higher throughput (2x-3x improvement)
- Better resource utilization

**Example**:
```python
# Async database query
async def get_products(category: str):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM products WHERE category = $1",
            category
        )
```

### Concurrent Feature Fetching

**Purpose**: Fetch multiple features in parallel to reduce latency

**Implementation**: Use `asyncio.gather()` to fetch features concurrently

**Example**:
```python
# Fetch multiple features concurrently
popularity, freshness, cf_score = await asyncio.gather(
    get_feature(product_id, "popularity_score"),
    get_feature(product_id, "freshness_score"),
    get_feature(product_id, "cf_score")
)
```

**Performance**: Reduces feature fetching time from 150ms (sequential) to 50ms (concurrent)

### Async Ranking Service

**Purpose**: Make ranking service async to improve throughput

**Implementation**: Convert ranking service to async/await

**Benefits**:
- Can handle more concurrent ranking requests
- Better integration with async database and cache clients
- Improved overall system throughput

### Performance Targets

**Throughput**: 2x improvement with async/await optimization

**Latency**: Maintain or improve p95 latency

**Resource Usage**: Better CPU utilization (less idle time waiting for I/O)

---

## Scalability (Phase 7)

**Alignment**: See `specs/SCALABILITY.md` for detailed scalability strategies

### Horizontal Scaling

**Architecture**: Stateless services enable horizontal scaling

**Configuration**:
- Minimum instances: 2 (for redundancy)
- Maximum instances: 10 (adjust based on load)
- Auto-scaling: Based on CPU, memory, request rate

**Load Balancing**: Round-robin or least connections algorithm

**Health Checks**: Route to `/health` endpoint every 10 seconds

### Auto-Scaling Triggers

**Scale-Up** (any of the following):
- CPU utilization >70% for 5 minutes
- Memory utilization >80% for 5 minutes
- Request rate >80% of capacity for 5 minutes
- p95 latency >300ms for 5 minutes

**Scale-Down** (all of the following):
- CPU utilization <30% for 10 minutes
- Memory utilization <50% for 10 minutes
- Request rate <40% of capacity for 10 minutes
- p95 latency <100ms for 10 minutes

### Multi-Region Deployment (Phase 10)

**Purpose**: Deploy globally for low latency worldwide

**Strategy**:
- Deploy in 2+ regions (US-East, EU-West, etc.)
- Route users to nearest region (GeoDNS)
- Replicate data across regions
- Automatic failover if region unhealthy

**See**: `specs/SCALABILITY.md` for detailed multi-region deployment strategy