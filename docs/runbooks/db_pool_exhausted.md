# Runbook: db_pool_exhausted

## Alert Information

- **Alert Name**: `db_pool_exhausted`
- **Severity**: Critical
- **Threshold**: Available connections < 2 for 2 minutes
- **Action**: Page on-call engineer

## Symptoms

- Database connection pool nearly exhausted
- Available connections less than 2
- Requests may fail with connection errors
- Service may become unresponsive
- Database connection timeouts

## Immediate Investigation Steps

1. **Check Alert Details**
   - Check current available connections
   - Review total vs. active connections
   - Check alert history in Alertmanager UI (http://localhost:9093)

2. **Check Database Connection Pool Metrics**
   - Open Database Health dashboard in Grafana
   - Review connection pool usage
   - Check active vs. idle connections
   - Review connection pool trends

3. **Check Service Logs**
   - Review database connection errors: `docker logs beamai-backend --tail 200 | grep -i "connection\|pool\|database"`
   - Check for connection timeout errors
   - Review trace IDs for failed requests

4. **Check Database Status**
   - Verify database is running: `docker ps | grep postgres`
   - Check database health: `docker exec beamai-postgres pg_isready -U postgres`
   - Review database logs: `docker logs beamai-postgres --tail 100`

5. **Check Database Load**
   - Review active database connections
   - Check for long-running queries
   - Review database CPU/memory usage
   - Check for database locks

6. **Check Application Behavior**
   - Review request rate trends
   - Check for traffic spikes
   - Review connection pool configuration
   - Check for connection leaks

## Common Root Causes

1. **Connection Leaks**
   - Connections not properly closed
   - Exception handling not closing connections
   - Async operations not releasing connections
   - Long-running transactions

2. **High Traffic**
   - Sudden traffic spikes
   - Increased request rate
   - More concurrent users
   - Load testing or DDoS

3. **Slow Database Queries**
   - Queries taking too long
   - Missing database indexes
   - Database locks
   - Long-running transactions

4. **Connection Pool Misconfiguration**
   - Pool size too small
   - Max overflow too low
   - Connection timeout too high
   - Pool configuration errors

5. **Database Issues**
   - Database performance degradation
   - Database locks
   - Database replication lag
   - Database connection limits

6. **Application Issues**
   - Synchronous database operations
   - Blocking database calls
   - N+1 query problems
   - Inefficient queries

7. **Resource Exhaustion**
   - Database server resource limits
   - Network issues
   - File descriptor limits
   - System resource constraints

## Resolution Steps

### Step 1: Immediate Mitigation

1. **Increase Connection Pool Size** (temporary fix)
   - Update connection pool configuration
   - Increase max connections
   - Restart service to apply changes

2. **Restart Service** (if connections are stuck)
   ```bash
   docker restart beamai-backend
   ```
   - This will release all connections
   - Monitor if connections are properly released

3. **Kill Long-Running Queries** (if database is locked)
   ```sql
   -- List long-running queries
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';
   
   -- Kill specific query (replace PID)
   SELECT pg_terminate_backend(PID);
   ```

### Step 2: Identify Connection Leaks

1. **Check Connection Pool Metrics**
   - Monitor active connections over time
   - Identify if connections are increasing
   - Check for connections not being released

2. **Review Application Code**
   - Check for connections not closed in finally blocks
   - Review exception handling
   - Check async operations
   - Verify connection context managers

3. **Check for Long-Running Transactions**
   ```sql
   -- Check for long-running transactions
   SELECT pid, now() - xact_start AS duration, query
   FROM pg_stat_activity
   WHERE xact_start IS NOT NULL
   ORDER BY duration DESC;
   ```

### Step 3: Optimize Database Queries

1. **Identify Slow Queries**
   ```sql
   -- Enable slow query log (if not already enabled)
   -- Review pg_stat_statements for slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

2. **Add Missing Indexes**
   - Review query execution plans
   - Add indexes for frequently queried columns
   - Optimize join queries

3. **Optimize Query Performance**
   - Review query logic
   - Add query result caching
   - Batch database operations
   - Use connection pooling effectively

### Step 4: Fix Connection Leaks

1. **Review Code for Leaks**
   - Check all database connection usage
   - Ensure connections are closed in finally blocks
   - Use context managers for connections
   - Review async connection handling

2. **Add Connection Monitoring**
   - Add logging for connection acquisition/release
   - Monitor connection pool metrics
   - Set up alerts for connection leaks

3. **Implement Connection Timeouts**
   - Set connection timeout
   - Implement connection retry logic
   - Add connection health checks

### Step 5: Optimize Connection Pool Configuration

1. **Review Pool Settings**
   - Adjust pool size based on load
   - Configure max overflow
   - Set connection timeout
   - Configure pool recycling

2. **Test Pool Configuration**
   - Load test with new configuration
   - Monitor connection pool usage
   - Verify connections are released

## Verification

After implementing fixes:

1. **Monitor Connection Pool**
   - Check available connections in Grafana
   - Verify connections are properly released
   - Monitor for 30-60 minutes to ensure stability

2. **Check Alert Status**
   - Verify alert clears in Alertmanager
   - Check alert history for recurrence

3. **Test Database Operations**
   - Test database queries
   - Verify connections are working
   - Check for connection errors

4. **Monitor Service Health**
   - Check service response times
   - Verify no connection errors
   - Monitor error rates

## Escalation

Escalate to senior engineer if:
- Connection pool exhaustion persists >15 minutes
- Unable to identify connection leaks
- Database is unresponsive
- Multiple services affected
- Unable to resolve after 30 minutes

## Relevant Metrics and Queries

### Prometheus Queries

**Connection Pool Status:**
```promql
db_connection_pool_size{state="active"}
db_connection_pool_size{state="idle"}
db_connection_pool_size{state="total"}
```

**Available Connections:**
```promql
db_connection_pool_size{state="total"}
-
db_connection_pool_size{state="active"}
```

**Connection Pool Utilization:**
```promql
db_connection_pool_size{state="active"}
/
db_connection_pool_size{state="total"}
```

**Connection Pool Trends:**
```promql
rate(db_connection_pool_size{state="active"}[5m])
```

**Request Rate (may correlate with connection usage):**
```promql
sum(rate(http_requests_total[5m])) by (endpoint)
```

## Prevention

1. **Connection Pool Monitoring**
   - Monitor connection pool usage proactively
   - Set up warning alerts at 80% utilization
   - Review connection pool trends regularly

2. **Code Reviews**
   - Review database connection usage in code reviews
   - Ensure connections are properly closed
   - Use connection context managers

3. **Testing**
   - Test connection pool under load
   - Test connection leak scenarios
   - Load test with realistic traffic

4. **Configuration**
   - Right-size connection pool
   - Configure connection timeouts
   - Set up connection pool recycling

5. **Database Optimization**
   - Regular query optimization
   - Index maintenance
   - Database performance tuning

## Related Alerts

- `p99_latency_high` - Connection pool issues can cause high latency
- `error_rate_high` - Connection pool exhaustion causes errors
- `cache_hit_rate_low` - Cache issues may increase database load

## References

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana Dashboard: Database Health](http://localhost:3000/d/database-health)
- [Alertmanager UI](http://localhost:9093)
- Database Logs: `docker logs beamai-postgres`

