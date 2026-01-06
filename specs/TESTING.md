# TESTING.md

## Purpose

This document expands the testing strategy with chaos engineering, resilience testing, and failure injection patterns. These tests ensure the system handles failures gracefully and maintains availability under adverse conditions.

**Alignment**: Expands `specs/TESTING_STRATEGY.md` with Phase 4.4 from `docs/TODO/implementation_phases.md`

---

## Testing Pyramid (Recap)

### Unit Tests (Fast, Many)
- Pure functions (scoring logic, feature extraction)
- Coverage target: 80%
- Run on every commit

### Integration Tests (Medium Speed, Moderate)
- API endpoints return expected structure
- Database queries return correct data
- Service-to-service communication works
- Run before merge to main

### End-to-End Tests (Slow, Few)
- User searches for "shoes" → gets results → clicks → purchases
- Simulates real user journey
- Run nightly on staging

### Load Tests (Slow, Few)
- Simulate 10,000 QPS
- Measure p99 latency under load
- Identify bottlenecks
- Run weekly

**See**: `specs/TESTING_STRATEGY.md` for detailed testing pyramid

---

## Chaos Engineering

### Purpose

**Goal**: Verify graceful degradation works under real-world failure conditions

**Principle**: "If it can fail, it will fail. Test it before it fails in production."

**Benefits**:
- Discover hidden dependencies
- Verify fallback mechanisms work
- Build confidence in system resilience
- Identify single points of failure

### Chaos Engineering Scenarios

#### 1. Database Connection Failures

**Scenario**: Simulate database connection failures

**Injection Method**:
- Block database port (iptables)
- Stop database container
- Exhaust connection pool

**Expected Behavior**:
- Circuit breaker opens after threshold
- Fallback to cached results
- Return 503 Service Unavailable if no cache
- Log errors with trace_id

**Verification**:
- System continues to function (degraded)
- No cascading failures
- Automatic recovery when database restored

**Runbook**: See Database Failure Runbook below

#### 2. Redis Cache Unavailability

**Scenario**: Simulate Redis cache failures

**Injection Method**:
- Stop Redis container
- Block Redis port
- Exhaust Redis connections

**Expected Behavior**:
- Circuit breaker opens after 5 failures
- Bypass cache, query database directly
- Higher latency (200ms → 500ms) but system functional
- Log cache failures

**Verification**:
- System continues to function (slower)
- No errors returned to users
- Automatic recovery when Redis restored

**Runbook**: See Cache Failure Runbook below

#### 3. High Latency Spikes

**Scenario**: Simulate network latency or slow database queries

**Injection Method**:
- Add artificial delay to database queries (100ms, 500ms, 1s)
- Add artificial delay to Redis operations
- Simulate network congestion

**Expected Behavior**:
- Timeout after threshold (30s for database, 5s for Redis)
- Fallback to cached results or error handling
- Circuit breaker opens if latency persists
- Log slow operations

**Verification**:
- System handles latency gracefully
- Timeouts prevent hanging requests
- Circuit breakers prevent cascading failures

**Runbook**: See Latency Spike Runbook below

#### 4. Service Crashes

**Scenario**: Simulate service crashes or restarts

**Injection Method**:
- Kill service process
- Restart service container
- Simulate OOM (Out of Memory) kills

**Expected Behavior**:
- Load balancer removes unhealthy instance
- Traffic routes to healthy instances
- Auto-scaling replaces crashed instance
- No user-visible errors (if multiple instances)

**Verification**:
- Zero-downtime service restarts
- Automatic instance replacement
- Health checks detect failures quickly

**Runbook**: See Service Crash Runbook below

#### 5. FAISS Index Corruption

**Scenario**: Simulate FAISS index corruption or unavailability

**Injection Method**:
- Corrupt index file
- Remove index file
- Simulate index load failure

**Expected Behavior**:
- Fallback to keyword search only
- Log index unavailability
- Alert on-call engineer
- System continues to function (degraded)

**Verification**:
- System continues to function without semantic search
- Keyword search still works
- Index rebuild process works

**Runbook**: See FAISS Index Failure Runbook below

#### 6. Read Replica Lag

**Scenario**: Simulate high read replica lag

**Injection Method**:
- Add artificial delay to replica queries
- Simulate network issues between primary and replica
- Stop replica replication

**Expected Behavior**:
- Route reads to primary if lag >60 seconds
- Alert on replication lag
- Monitor replica health
- System continues to function

**Verification**:
- Automatic failover to primary
- Replication lag monitoring works
- System continues to function

**Runbook**: See Replica Lag Runbook below

---

## Failure Injection Patterns

### Network Failure Injection

**Tool**: Chaos Monkey, Chaos Mesh, or custom scripts

**Methods**:
- Block ports (iptables, firewall rules)
- Add network latency (tc, netem)
- Simulate packet loss
- Simulate network partitions

**Example** (using iptables):
```bash
# Block database port
iptables -A INPUT -p tcp --dport 5432 -j DROP

# Restore
iptables -D INPUT -p tcp --dport 5432 -j DROP
```

### Resource Exhaustion

**Methods**:
- Exhaust CPU (stress-ng)
- Exhaust memory (allocate large arrays)
- Exhaust disk space (fill disk)
- Exhaust connection pool

**Example** (CPU exhaustion):
```bash
stress-ng --cpu 4 --timeout 60s
```

### Service Failure Injection

**Methods**:
- Kill service process
- Restart service container
- Simulate OOM kills
- Simulate service crashes

**Example** (kill process):
```bash
# Kill service
pkill -9 python

# Or restart container
docker restart backend_service
```

---

## Resilience Testing Procedures

### Test Environment

**Requirements**:
- Staging environment (production-like)
- Multiple instances (test load balancing)
- Monitoring and alerting enabled
- Rollback capability

**Safety**:
- Never run chaos tests in production
- Always have rollback plan
- Monitor closely during tests
- Stop tests if critical issues detected

### Test Execution

**Frequency**: Weekly (automated) or monthly (manual)

**Duration**: 30-60 minutes per scenario

**Process**:
1. **Preparation**: Set up test environment, verify monitoring
2. **Injection**: Inject failure (database, cache, service, etc.)
3. **Observation**: Monitor system behavior, metrics, logs
4. **Verification**: Verify graceful degradation, fallbacks work
5. **Recovery**: Restore service, verify automatic recovery
6. **Analysis**: Document findings, update runbooks

### Test Metrics

**Track During Tests**:
- Error rate
- Latency (p50, p95, p99)
- Request success rate
- Circuit breaker state
- Recovery time

**Success Criteria**:
- System continues to function (degraded but functional)
- No cascading failures
- Automatic recovery when failure resolved
- Error rate <5% during failure
- Recovery time <5 minutes

---

## Runbooks

### Database Failure Runbook

**Symptoms**:
- Database connection errors
- Circuit breaker open
- High error rate
- Fallback to cached results

**Immediate Actions**:
1. Check database health (connectivity, CPU, memory)
2. Check connection pool status
3. Verify circuit breaker state
4. Check replication lag (if applicable)

**Investigation**:
1. Check database logs for errors
2. Check application logs for connection errors
3. Verify database resource usage (CPU, memory, disk)
4. Check network connectivity

**Resolution**:
1. If database down: Restart database, verify health
2. If connection pool exhausted: Increase pool size, check for leaks
3. If replication lag: Check replica health, promote new replica if needed
4. Verify automatic recovery (circuit breaker closes)

**Prevention**:
- Monitor database health proactively
- Set up alerts for connection pool exhaustion
- Regular database maintenance
- Connection pool leak detection

### Cache Failure Runbook

**Symptoms**:
- Redis connection errors
- Circuit breaker open
- Higher latency (cache misses)
- Fallback to database queries

**Immediate Actions**:
1. Check Redis health (connectivity, memory usage)
2. Check circuit breaker state
3. Verify cache hit rate drop
4. Monitor latency increase

**Investigation**:
1. Check Redis logs for errors
2. Check Redis memory usage (OOM?)
3. Verify network connectivity
4. Check Redis connection pool

**Resolution**:
1. If Redis down: Restart Redis, verify health
2. If Redis OOM: Increase memory limit, check for memory leaks
3. If network issue: Check network connectivity, firewall rules
4. Verify automatic recovery (circuit breaker closes, cache hit rate recovers)

**Prevention**:
- Monitor Redis health proactively
- Set up alerts for memory usage
- Regular Redis maintenance
- Cache warming after Redis restart

### Latency Spike Runbook

**Symptoms**:
- High latency (p95 >300ms)
- Timeout errors
- Circuit breaker may open
- Slow database queries

**Immediate Actions**:
1. Check latency metrics (p50, p95, p99)
2. Check database query performance
3. Check cache latency
4. Verify circuit breaker state

**Investigation**:
1. Check slow query log (>100ms queries)
2. Check database resource usage (CPU, memory)
3. Check network latency
4. Check for N+1 queries

**Resolution**:
1. If slow queries: Optimize queries, add indexes
2. If database load: Scale database, add read replicas
3. If network issue: Check network connectivity, routing
4. If N+1 queries: Implement batch fetching

**Prevention**:
- Monitor query performance proactively
- Set up alerts for slow queries
- Regular query optimization
- Database performance tuning

### Service Crash Runbook

**Symptoms**:
- Service unavailable errors
- Health check failures
- Load balancer removes instance
- Auto-scaling triggers

**Immediate Actions**:
1. Check service health (health endpoint)
2. Check service logs for errors
3. Verify load balancer routing
4. Check auto-scaling status

**Investigation**:
1. Check service logs for crash reason (OOM, error, etc.)
2. Check service resource usage (CPU, memory)
3. Check for recent deployments
4. Verify service configuration

**Resolution**:
1. If OOM: Increase memory limit, check for memory leaks
2. If error: Fix error, redeploy service
3. If configuration issue: Fix configuration, redeploy
4. Verify automatic recovery (new instance created, health checks pass)

**Prevention**:
- Monitor service health proactively
- Set up alerts for service crashes
- Regular service maintenance
- Memory leak detection

### FAISS Index Failure Runbook

**Symptoms**:
- FAISS index unavailable
- Fallback to keyword search only
- No semantic search results
- Alert triggered

**Immediate Actions**:
1. Check index file existence and permissions
2. Check index load errors in logs
3. Verify disk space availability
4. Check memory availability

**Investigation**:
1. Check index file integrity
2. Check disk space (index file size)
3. Check memory usage (index loading)
4. Check index build logs

**Resolution**:
1. If index corrupted: Rebuild index from latest embeddings
2. If disk space: Free up disk space, rebuild index
3. If memory issue: Increase memory limit, rebuild index
4. Verify index loads successfully

**Prevention**:
- Monitor index health proactively
- Set up alerts for index unavailability
- Regular index rebuilds
- Index file backup

### Replica Lag Runbook

**Symptoms**:
- High replication lag (>60 seconds)
- Reads routed to primary
- Alert triggered
- Slightly stale data

**Immediate Actions**:
1. Check replication lag metrics
2. Check replica health
3. Verify read routing (primary vs replica)
4. Check primary database load

**Investigation**:
1. Check replica logs for errors
2. Check network connectivity (primary → replica)
3. Check primary database load (high write load?)
4. Check replica resource usage (CPU, memory)

**Resolution**:
1. If replica unhealthy: Restart replica, verify replication
2. If network issue: Check network connectivity, routing
3. If primary load: Optimize writes, add read replicas
4. Verify replication lag decreases

**Prevention**:
- Monitor replication lag proactively
- Set up alerts for high lag
- Regular replica maintenance
- Optimize primary database writes

---

## Automated Chaos Tests

### Test Suite

**Location**: `tests/chaos/`

**Tests**:
- `test_database_failure.py`: Test database connection failures
- `test_cache_failure.py`: Test Redis cache failures
- `test_latency_spike.py`: Test high latency scenarios
- `test_service_crash.py`: Test service crashes
- `test_faiss_failure.py`: Test FAISS index failures
- `test_replica_lag.py`: Test read replica lag

### Test Execution

**Frequency**: Weekly (automated)

**Environment**: Staging environment

**Process**:
1. Run test suite
2. Inject failures
3. Verify graceful degradation
4. Restore services
5. Generate test report

**Report**:
- Test results (pass/fail)
- Metrics during tests
- Issues found
- Recommendations

---

## References

- **Testing Strategy**: `specs/TESTING_STRATEGY.md` (Testing Pyramid)
- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 4.4)
- **Architecture**: `specs/ARCHITECTURE.md` (Failure Modes)
- **Observability**: `specs/OBSERVABILITY.md` (Monitoring)

---

End of document

