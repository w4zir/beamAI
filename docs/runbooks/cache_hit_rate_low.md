# Runbook: cache_hit_rate_low

## Alert Information

- **Alert Name**: `cache_hit_rate_low`
- **Severity**: Warning
- **Threshold**: Cache hit rate < 50% for 10 minutes
- **Action**: Slack alert to #alerts channel

## Symptoms

- Low cache hit rate for specific cache types
- Increased database load
- Higher response times
- More cache misses than hits

## Immediate Investigation Steps

1. **Check Alert Details**
   - Identify which cache type(s) are affected
   - Check the exact cache hit rate percentage
   - Review cache hit/miss trends
   - Review alert history in Alertmanager UI (http://localhost:9093)

2. **Check Cache Metrics in Grafana**
   - Open Cache Performance dashboard
   - Review cache hit rate trends
   - Check cache hit/miss counts
   - Review cache operation latency

3. **Check Redis Status**
   - Verify Redis is running: `docker ps | grep redis`
   - Check Redis health: `docker exec beamai-redis redis-cli ping`
   - Review Redis logs: `docker logs beamai-redis --tail 100`
   - Check Redis memory usage: `docker exec beamai-redis redis-cli INFO memory`

4. **Check Cache Configuration**
   - Review cache TTL settings
   - Check cache key patterns
   - Verify cache invalidation logic
   - Review cache warming configuration

5. **Analyze Cache Patterns**
   - Review cache hit/miss patterns in logs
   - Check for cache invalidation storms
   - Review cache key distribution
   - Check for unusual query patterns

6. **Check Application Behavior**
   - Review request patterns
   - Check for traffic spikes
   - Review query diversity
   - Check for cache bypass logic

## Common Root Causes

1. **Cache Invalidation Issues**
   - Excessive cache invalidation
   - Cache invalidation storms
   - Incorrect invalidation logic
   - Too frequent cache clearing

2. **Cache Warming Failures**
   - Cache warming not running
   - Cache warming incomplete
   - Popular queries not cached
   - Cache warming script failures

3. **TTL Configuration Issues**
   - TTL too short
   - TTL misconfiguration
   - Inconsistent TTL settings
   - TTL not set for some caches

4. **Redis Issues**
   - Redis memory full
   - Redis eviction policies
   - Redis connection issues
   - Redis performance degradation

5. **Query Pattern Changes**
   - New query patterns
   - Increased query diversity
   - Seasonal query patterns
   - Trending queries not cached

6. **Cache Key Issues**
   - Cache key collisions
   - Cache key too specific
   - Cache key generation issues
   - Cache key not normalized

7. **Application Issues**
   - Cache bypass logic
   - Cache not being used
   - Cache implementation bugs
   - Cache not enabled for some endpoints

8. **Traffic Patterns**
   - Sudden traffic spikes
   - New user patterns
   - Increased unique queries
   - Cache not keeping up with load

## Resolution Steps

### Step 1: Immediate Investigation

1. **Check Redis Health**
   ```bash
   # Check Redis is running
   docker exec beamai-redis redis-cli ping
   
   # Check Redis memory
   docker exec beamai-redis redis-cli INFO memory
   
   # Check Redis keys
   docker exec beamai-redis redis-cli DBSIZE
   ```

2. **Review Cache Metrics**
   - Check cache hit/miss counts
   - Review cache hit rate trends
   - Identify which cache types are affected

3. **Check Cache Configuration**
   - Review TTL settings
   - Check cache key patterns
   - Verify cache is enabled

### Step 2: Fix Cache Invalidation

1. **Review Invalidation Logic**
   - Check for excessive invalidation
   - Review invalidation triggers
   - Optimize invalidation patterns

2. **Reduce Invalidation Frequency**
   - Batch invalidations
   - Use TTL instead of manual invalidation
   - Implement smarter invalidation

3. **Fix Invalidation Storms**
   - Identify invalidation triggers
   - Add rate limiting to invalidations
   - Optimize invalidation logic

### Step 3: Improve Cache Warming

1. **Run Cache Warming**
   ```bash
   # If cache warming script exists
   docker exec beamai-backend python scripts/warm_cache.py
   ```

2. **Improve Cache Warming**
   - Add popular queries to warming
   - Schedule regular cache warming
   - Monitor cache warming effectiveness

3. **Automate Cache Warming**
   - Set up scheduled cache warming
   - Warm cache on service startup
   - Warm cache after deployments

### Step 4: Optimize TTL Configuration

1. **Review TTL Settings**
   - Increase TTL for stable data
   - Set appropriate TTL per cache type
   - Balance freshness vs. hit rate

2. **Test TTL Changes**
   - Monitor cache hit rate after changes
   - Verify data freshness
   - Adjust TTL based on results

### Step 5: Fix Redis Issues

1. **Check Redis Memory**
   - Review Redis memory usage
   - Check eviction policies
   - Increase Redis memory if needed

2. **Optimize Redis Configuration**
   - Review Redis configuration
   - Adjust eviction policy
   - Optimize Redis performance

3. **Restart Redis** (if needed)
   ```bash
   docker restart beamai-redis
   ```

### Step 6: Improve Cache Strategy

1. **Review Cache Implementation**
   - Check cache is being used correctly
   - Verify cache key generation
   - Review cache logic

2. **Optimize Cache Keys**
   - Normalize cache keys
   - Avoid key collisions
   - Optimize key patterns

3. **Add Caching Where Missing**
   - Identify uncached endpoints
   - Add caching for expensive operations
   - Improve cache coverage

## Verification

After implementing fixes:

1. **Monitor Cache Hit Rate**
   - Check cache hit rate in Grafana
   - Verify rate returns above 50% threshold
   - Monitor for 30-60 minutes to ensure stability

2. **Check Cache Metrics**
   - Review cache hit/miss counts
   - Verify cache is working correctly
   - Check cache operation latency

3. **Check Alert Status**
   - Verify alert clears in Alertmanager
   - Check alert history for recurrence

4. **Monitor Database Load**
   - Check if database load decreased
   - Verify fewer database queries
   - Monitor response times

## Escalation

Escalate to senior engineer if:
- Cache hit rate persists <50% for >1 hour
- Redis is unavailable or corrupted
- Unable to identify root cause after 1 hour
- Multiple cache types affected
- Cache issues causing service degradation

## Relevant Metrics and Queries

### Prometheus Queries

**Cache Hit Rate:**
```promql
sum(rate(cache_hits_total[10m])) by (cache_type)
/
(
  sum(rate(cache_hits_total[10m])) by (cache_type)
  +
  sum(rate(cache_misses_total[10m])) by (cache_type)
)
```

**Cache Hit Count:**
```promql
sum(rate(cache_hits_total[5m])) by (cache_type)
```

**Cache Miss Count:**
```promql
sum(rate(cache_misses_total[5m])) by (cache_type)
```

**Cache Hit/Miss Ratio:**
```promql
sum(rate(cache_hits_total[5m])) by (cache_type)
/
sum(rate(cache_misses_total[5m])) by (cache_type)
```

**Total Cache Operations:**
```promql
sum(rate(cache_hits_total[5m])) by (cache_type)
+
sum(rate(cache_misses_total[5m])) by (cache_type)
```

## Prevention

1. **Proactive Monitoring**
   - Monitor cache hit rate daily
   - Set up warning alerts at 60% hit rate
   - Review cache metrics regularly

2. **Cache Strategy**
   - Regular cache strategy reviews
   - Optimize cache TTL settings
   - Improve cache warming

3. **Redis Maintenance**
   - Regular Redis health checks
   - Monitor Redis memory usage
   - Optimize Redis configuration

4. **Testing**
   - Test cache under load
   - Test cache invalidation
   - Test cache warming

5. **Documentation**
   - Document cache strategy
   - Document cache key patterns
   - Document TTL settings

## Related Alerts

- `p99_latency_high` - Low cache hit rate can cause high latency
- `error_rate_high` - Cache issues may cause errors
- `db_pool_exhausted` - Low cache hit rate increases database load

## References

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana Dashboard: Cache Performance](http://localhost:3000/d/cache-performance)
- [Alertmanager UI](http://localhost:9093)
- Redis Logs: `docker logs beamai-redis`

