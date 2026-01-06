# Runbook: p99_latency_high

## Alert Information

- **Alert Name**: `p99_latency_high`
- **Severity**: Critical
- **Threshold**: p99 latency > 500ms (0.5s) for 5 minutes
- **Action**: Page on-call engineer

## Symptoms

- p99 latency exceeds 500ms for a specific endpoint
- Users may experience slow response times
- Request timeouts may increase
- Service may appear unresponsive

## Immediate Investigation Steps

1. **Check Alert Details**
   - Identify which endpoint(s) are affected
   - Check the exact latency value
   - Review alert history in Alertmanager UI (http://localhost:9093)

2. **Check Service Health**
   - Verify service is running: `docker ps | grep beamai-backend`
   - Check service logs: `docker logs beamai-backend --tail 100`
   - Review recent deployments or configuration changes

3. **Check Metrics in Grafana**
   - Open Service Health Overview dashboard
   - Review latency percentiles (p50, p95, p99) for affected endpoints
   - Check request rate trends
   - Review error rate (may be correlated)

4. **Check Resource Utilization**
   - CPU usage: Check `system_cpu_usage_percent` metric
   - Memory usage: Check `system_memory_usage_bytes` metric
   - Database connection pool: Check `db_connection_pool_size` metrics

5. **Check Database Performance**
   - Review database query latency
   - Check for slow queries in database logs
   - Verify database connection pool is not exhausted
   - Check database replication lag (if applicable)

6. **Check Cache Performance**
   - Review cache hit rate: `cache_hit_rate` metric
   - Verify Redis is healthy: `docker logs beamai-redis --tail 50`
   - Check cache connection issues

## Common Root Causes

1. **Database Issues**
   - Slow database queries
   - Database connection pool exhaustion
   - Database replication lag
   - Missing database indexes

2. **Resource Constraints**
   - High CPU usage (>80%)
   - High memory usage (>85%)
   - Network latency
   - Disk I/O bottlenecks

3. **Cache Issues**
   - Low cache hit rate
   - Redis connection issues
   - Cache invalidation storms
   - Cache warming failures

4. **Application Issues**
   - Inefficient algorithms
   - N+1 query problems
   - Large result sets
   - Synchronous blocking operations

5. **External Dependencies**
   - Slow external API calls
   - Network issues
   - Third-party service degradation

6. **Load Issues**
   - Sudden traffic spikes
   - DDoS attacks
   - Resource exhaustion under load

## Resolution Steps

### Step 1: Immediate Mitigation

1. **Scale Services** (if applicable)
   - Increase service instances
   - Scale horizontally if load is high

2. **Restart Service** (if service appears stuck)
   ```bash
   docker restart beamai-backend
   ```

3. **Clear Cache** (if cache issues suspected)
   ```bash
   docker exec beamai-redis redis-cli FLUSHALL
   ```

### Step 2: Database Optimization

1. **Check Slow Queries**
   - Review database slow query log
   - Identify queries taking >100ms
   - Add missing indexes

2. **Optimize Connection Pool**
   - Increase connection pool size if exhausted
   - Check for connection leaks
   - Review connection pool configuration

3. **Check Database Load**
   - Review database CPU/memory usage
   - Check for long-running transactions
   - Verify database replication status

### Step 3: Application Optimization

1. **Review Recent Changes**
   - Check git history for recent code changes
   - Review recent deployments
   - Check for configuration changes

2. **Profile Application**
   - Use profiling tools to identify bottlenecks
   - Review application logs for errors
   - Check for memory leaks

3. **Optimize Hot Paths**
   - Review endpoint-specific code
   - Optimize database queries
   - Add caching where appropriate

### Step 4: Cache Optimization

1. **Improve Cache Hit Rate**
   - Review cache TTL settings
   - Implement cache warming
   - Check cache invalidation strategy

2. **Verify Redis Health**
   - Check Redis memory usage
   - Review Redis connection pool
   - Verify Redis is not a bottleneck

## Verification

After implementing fixes:

1. **Monitor Metrics**
   - Check p99 latency in Grafana
   - Verify latency returns below 500ms threshold
   - Monitor for 15-30 minutes to ensure stability

2. **Check Alert Status**
   - Verify alert clears in Alertmanager
   - Check alert history for recurrence

3. **User Impact**
   - Monitor error rates
   - Check user-facing metrics
   - Verify service is responsive

## Escalation

Escalate to senior engineer if:
- Latency persists >15 minutes after initial investigation
- Multiple endpoints affected simultaneously
- Service is completely unresponsive
- Database is down or unreachable
- Unable to identify root cause after 30 minutes

## Relevant Metrics and Queries

### Prometheus Queries

**Current p99 Latency:**
```promql
histogram_quantile(0.99, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint, method)
)
```

**Latency by Endpoint:**
```promql
histogram_quantile(0.99, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
)
```

**Request Rate:**
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```

**Error Rate:**
```promql
sum(rate(http_errors_total[5m])) by (endpoint)
/
sum(rate(http_requests_total[5m])) by (endpoint)
```

**CPU Usage:**
```promql
system_cpu_usage_percent
```

**Memory Usage:**
```promql
system_memory_usage_bytes
```

**Database Connection Pool:**
```promql
db_connection_pool_size{state="active"}
db_connection_pool_size{state="idle"}
db_connection_pool_size{state="total"}
```

**Cache Hit Rate:**
```promql
sum(rate(cache_hits_total[5m])) by (cache_type)
/
(
  sum(rate(cache_hits_total[5m])) by (cache_type)
  +
  sum(rate(cache_misses_total[5m])) by (cache_type)
)
```

## Prevention

1. **Set Up Monitoring**
   - Monitor p95 latency proactively
   - Set up warning alerts at p95 > 300ms
   - Review latency trends regularly

2. **Performance Testing**
   - Regular load testing
   - Identify bottlenecks before production
   - Set up performance budgets

3. **Database Optimization**
   - Regular query optimization
   - Index maintenance
   - Connection pool tuning

4. **Cache Strategy**
   - Maintain high cache hit rate (>70%)
   - Implement cache warming
   - Monitor cache effectiveness

5. **Capacity Planning**
   - Monitor resource utilization trends
   - Plan for traffic growth
   - Set up auto-scaling if applicable

## Related Alerts

- `error_rate_high` - May be correlated with latency issues
- `db_pool_exhausted` - Database issues can cause latency
- `cache_hit_rate_low` - Cache issues can cause latency

## References

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana Dashboard: Service Health Overview](http://localhost:3000/d/service-health-overview)
- [Alertmanager UI](http://localhost:9093)

