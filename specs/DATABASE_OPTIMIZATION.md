# DATABASE_OPTIMIZATION.md

## Purpose

This document defines database optimization strategies including connection pooling, read replicas, query optimization, and partitioning. These optimizations are critical for handling high traffic and ensuring low latency.

**Alignment**: Implements Phase 3.4 and Phase 7.2 from `docs/TODO/implementation_phases.md`

---

## Design Principles

1. **Connection Efficiency**: Minimize connection overhead through pooling
2. **Read/Write Splitting**: Route reads to replicas, writes to primary
3. **Query Performance**: Optimize queries through indexing and batching
4. **Observability**: Monitor connection pool, replication lag, and query performance
5. **Graceful Degradation**: Fallback to primary if replicas unavailable

---

## Connection Pooling

### Configuration

**Pool Size**: 20 connections (adjust based on load)

**Max Overflow**: 10 connections (total: 30 under load)

**Connection Timeout**: 5 seconds

**Max Lifetime**: 1 hour (prevent stale connections)

**Idle Timeout**: 10 minutes

### Implementation

**Async (Recommended)**: Use `asyncpg` with connection pool

```python
import asyncpg

pool = await asyncpg.create_pool(
    database_url,
    min_size=10,
    max_size=20,
    max_queries=50000,  # Recycle connections after N queries
    max_inactive_connection_lifetime=3600,
    command_timeout=30
)
```

**Sync (Fallback)**: Use `psycopg2` with `SQLAlchemy` connection pool

### Pool Monitoring

**Metrics**:
```
db_connection_pool_size{state="active"}  # Active connections
db_connection_pool_size{state="idle"}   # Idle connections
db_connection_pool_size{state="waiting"} # Waiting for connection
db_connection_pool_wait_time_seconds    # Time waiting for connection
db_connection_pool_errors_total{reason="timeout"}  # Pool exhaustion errors
```

**Alerts**:
- Pool size >90% capacity for 5 minutes → Warning
- Connection wait time >1 second → Warning
- Pool exhaustion → Critical

---

## Read Replica Routing

### Architecture

**Primary Database**: Handles all writes (events, product updates)

**Read Replicas**: 2-3 replicas for read queries (search, recommendations)

**Replication Lag**: Monitor and alert if >60 seconds

### Routing Logic

**Read Queries** (route to replica):
- `SELECT` statements
- Search queries (FTS)
- Recommendation queries
- Feature fetching

**Write Queries** (route to primary):
- `INSERT` statements (events)
- `UPDATE` statements (products, features)
- `DELETE` statements (admin operations)

**Transaction Queries** (route to primary):
- Queries within transactions
- Read-after-write consistency required

### Implementation

**Database Client Wrapper**:
```python
class DatabaseClient:
    async def execute_read(self, query: str, *args) -> List[Dict]:
        """Route to read replica"""
        replica = self._select_replica()  # Round-robin or health-based
        return await replica.fetch(query, *args)
    
    async def execute_write(self, query: str, *args) -> None:
        """Route to primary"""
        return await self.primary.execute(query, *args)
```

**Replica Selection**:
- **Round-Robin**: Distribute load evenly
- **Health-Based**: Prefer replicas with low lag
- **Geo-Based**: Route to nearest replica (multi-region)

### Replication Lag Monitoring

**Metrics**:
```
db_replication_lag_seconds{replica="replica_1"}  # Lag in seconds
db_replica_health{replica="replica_1"}  # 1=healthy, 0=unhealthy
```

**Alerts**:
- Replication lag >60 seconds → Warning
- Replication lag >120 seconds → Critical
- Replica unhealthy → Critical

**Fallback**: If replica lag >60s, route reads to primary (with alert)

---

## Query Optimization

### Indexing Strategy

**Required Indexes**:

1. **Products Table**:
   - `PRIMARY KEY (id)`
   - `INDEX idx_products_category (category)`
   - `INDEX idx_products_popularity (popularity_score DESC)`
   - `GIN INDEX idx_products_search_vector (search_vector)` (FTS)

2. **Events Table**:
   - `INDEX idx_events_user_product (user_id, product_id)`
   - `INDEX idx_events_timestamp (timestamp DESC)`
   - `INDEX idx_events_user_timestamp (user_id, timestamp DESC)`
   - `INDEX idx_events_product_timestamp (product_id, timestamp DESC)`

3. **Composite Indexes**:
   - `INDEX idx_events_user_type_timestamp (user_id, event_type, timestamp DESC)`

### Query Patterns

**Efficient Queries**:
```sql
-- Use indexes
SELECT * FROM products WHERE category = 'electronics' ORDER BY popularity_score DESC LIMIT 20;

-- Use covering indexes
SELECT product_id, popularity_score FROM products WHERE category = 'electronics' ORDER BY popularity_score DESC LIMIT 20;
```

**Inefficient Queries** (avoid):
```sql
-- Full table scan
SELECT * FROM products WHERE LOWER(name) LIKE '%shoes%';

-- Missing index
SELECT * FROM events WHERE user_id = 'user_123' ORDER BY timestamp DESC;  -- If no index on timestamp
```

### EXPLAIN ANALYZE

**Process**:
1. Run `EXPLAIN ANALYZE` on slow queries (>100ms)
2. Identify full table scans, missing indexes
3. Add indexes or rewrite queries
4. Re-test performance

**Example**:
```sql
EXPLAIN ANALYZE
SELECT * FROM products 
WHERE category = 'electronics' 
ORDER BY popularity_score DESC 
LIMIT 20;
```

**Key Metrics**:
- **Seq Scan**: Full table scan (bad, add index)
- **Index Scan**: Using index (good)
- **Execution Time**: Target <50ms for common queries

---

## Batch Operations

### N+1 Query Prevention

**Problem**: Fetching features for N products results in N+1 queries

**Solution**: Batch fetch all features in single query

**Example**:
```python
# Bad: N+1 queries
for product_id in product_ids:
    popularity = await db.fetch_one("SELECT popularity_score FROM products WHERE id = $1", product_id)

# Good: Single query
popularity_scores = await db.fetch(
    "SELECT id, popularity_score FROM products WHERE id = ANY($1)",
    product_ids
)
```

### Batch Feature Fetching

**Service**: `FeatureService.batch_fetch(product_ids: List[str], feature_names: List[str])`

**Implementation**:
1. Group features by source (products table, events table, etc.)
2. Execute batch queries per source
3. Combine results
4. Return feature map: `{product_id: {feature_name: value}}`

**Performance**: Reduces 100 queries to 5-10 queries

---

## Slow Query Logging

### Threshold

**Log Queries**: Execution time >100ms

**Log Details**:
- Query text (parameterized)
- Execution time
- Rows returned
- Index usage
- Trace ID (for correlation)

### Implementation

**PostgreSQL Configuration**:
```sql
-- Enable slow query log
SET log_min_duration_statement = 100;  -- Log queries >100ms
SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';
```

**Application Logging**:
- Log slow queries to structured logs
- Include query plan (EXPLAIN ANALYZE)
- Alert if >10 slow queries per minute

---

## Partitioning Strategy (Future)

### Events Table Partitioning

**Strategy**: Partition by date (monthly partitions)

**Benefits**:
- Faster queries on recent data
- Easier data archival
- Reduced index size per partition

**Implementation** (PostgreSQL 10+):
```sql
-- Create partitioned table
CREATE TABLE events (
    user_id TEXT,
    product_id TEXT,
    event_type TEXT,
    timestamp TIMESTAMP,
    source TEXT
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE events_2024_01 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE events_2024_02 PARTITION OF events
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

**Query Routing**: PostgreSQL automatically routes queries to correct partition

**Maintenance**:
- Create partitions 1 month ahead
- Archive old partitions to cold storage
- Drop partitions after retention period

---

## Performance Targets

### Query Latency

- **Simple Lookups**: p95 <10ms
- **Search Queries**: p95 <50ms
- **Recommendation Queries**: p95 <100ms
- **Feature Batch Fetch**: p95 <50ms (for 100 products)

### Connection Pool

- **Pool Utilization**: <80% under normal load
- **Connection Wait Time**: p95 <10ms
- **Pool Exhaustion**: 0 occurrences

### Replication

- **Replication Lag**: p95 <5 seconds
- **Replica Availability**: >99.9%

---

## Monitoring and Alerting

### Key Metrics

**Connection Pool**:
```
db_connection_pool_size{state="active"}
db_connection_pool_wait_time_seconds
db_connection_pool_errors_total
```

**Replication**:
```
db_replication_lag_seconds{replica="replica_1"}
db_replica_health{replica="replica_1"}
```

**Query Performance**:
```
db_query_duration_seconds{query_type="search"}
db_query_duration_seconds{query_type="recommendation"}
db_slow_queries_total{threshold="100ms"}
```

### Grafana Dashboards

**Database Health Dashboard**:
- Connection pool utilization
- Replication lag per replica
- Query latency percentiles
- Slow query count
- Error rate

### Alerts

- **Pool Exhaustion**: Pool size >95% for 2 minutes → Critical
- **High Replication Lag**: Lag >60 seconds for 5 minutes → Warning
- **Slow Query Spike**: >20 slow queries/minute → Warning
- **Replica Down**: Replica health = 0 → Critical

---

## Migration Path

### Phase 1: Connection Pooling

1. Implement connection pool
2. Monitor pool metrics
3. Adjust pool size based on load

### Phase 2: Read Replicas

1. Set up read replicas
2. Implement read/write splitting
3. Monitor replication lag
4. Gradually route more reads to replicas

### Phase 3: Query Optimization

1. Analyze slow queries
2. Add indexes
3. Rewrite inefficient queries
4. Monitor performance improvements

### Phase 4: Partitioning (Future)

1. Plan partition strategy
2. Create partitioned table
3. Migrate data
4. Update queries if needed

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 3.4, 7.2)
- **Architecture**: `specs/ARCHITECTURE.md` (Failure Modes)
- **Observability**: `specs/OBSERVABILITY.md` (Metrics)
- **Caching Strategy**: `specs/CACHING_STRATEGY.md` (Cache Integration)

---

End of document

