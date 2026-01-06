# Runbook: error_rate_high

## Alert Information

- **Alert Name**: `error_rate_high`
- **Severity**: Critical
- **Threshold**: Error rate > 1% for 2 minutes
- **Action**: Page on-call engineer

## Symptoms

- Error rate exceeds 1% for a specific endpoint
- Users may experience failed requests
- 4xx or 5xx HTTP status codes increasing
- Service may be returning errors

## Immediate Investigation Steps

1. **Check Alert Details**
   - Identify which endpoint(s) are affected
   - Check the exact error rate percentage
   - Identify error status codes (4xx vs 5xx)
   - Review alert history in Alertmanager UI (http://localhost:9093)

2. **Check Service Logs**
   - Review recent error logs: `docker logs beamai-backend --tail 200 | grep -i error`
   - Check for exception stack traces
   - Review trace IDs for failed requests
   - Look for patterns in error messages

3. **Check Metrics in Grafana**
   - Open Service Health Overview dashboard
   - Review error rate trends
   - Check error breakdown by status code
   - Review request rate (may indicate traffic spikes)

4. **Check Service Health**
   - Verify service is running: `docker ps | grep beamai-backend`
   - Check service health endpoint: `curl http://localhost:8000/health/`
   - Review recent deployments or configuration changes

5. **Check Database Connectivity**
   - Verify database is accessible
   - Check database connection pool status
   - Review database error logs
   - Test database connectivity: `docker exec beamai-backend python -c "from app.core.database import get_db; get_db()"`

6. **Check External Dependencies**
   - Verify Redis is healthy: `docker logs beamai-redis --tail 50`
   - Check Redis connectivity
   - Review external API status (if applicable)

## Common Root Causes

1. **Application Errors (5xx)**
   - Unhandled exceptions
   - Null pointer exceptions
   - Type errors
   - Logic errors in code

2. **Database Issues**
   - Database connection failures
   - Query timeouts
   - Database deadlocks
   - Connection pool exhaustion

3. **Cache Issues**
   - Redis connection failures
   - Cache serialization errors
   - Cache timeout issues

4. **Resource Exhaustion**
   - Out of memory errors
   - CPU exhaustion
   - File descriptor limits
   - Thread pool exhaustion

5. **Configuration Issues**
   - Invalid configuration values
   - Missing environment variables
   - Incorrect service URLs
   - Authentication/authorization failures

6. **Client Errors (4xx)**
   - Invalid request parameters
   - Missing required fields
   - Authentication failures
   - Rate limiting (429 errors)

7. **External Service Failures**
   - Third-party API failures
   - Network connectivity issues
   - Service dependencies down

8. **Recent Deployments**
   - Code bugs introduced in recent deployment
   - Configuration changes
   - Database migration issues
   - Dependency version conflicts

## Resolution Steps

### Step 1: Immediate Mitigation

1. **Check for Recent Deployments**
   - If recent deployment, consider rollback
   - Review deployment logs
   - Check for configuration changes

2. **Restart Service** (if service appears stuck)
   ```bash
   docker restart beamai-backend
   ```

3. **Scale Services** (if load-related)
   - Increase service instances
   - Distribute load across instances

### Step 2: Investigate Error Types

1. **5xx Errors (Server Errors)**
   - Review application logs for stack traces
   - Check for unhandled exceptions
   - Review recent code changes
   - Check for resource exhaustion

2. **4xx Errors (Client Errors)**
   - Review request validation logic
   - Check for authentication issues
   - Verify API contract compliance
   - Review rate limiting configuration

### Step 3: Database Issues

1. **Check Database Connectivity**
   - Verify database is running: `docker ps | grep postgres`
   - Test database connection
   - Check database logs: `docker logs beamai-postgres --tail 100`

2. **Check Connection Pool**
   - Review connection pool metrics
   - Check for connection leaks
   - Increase pool size if needed

3. **Check Database Queries**
   - Review slow query log
   - Check for query timeouts
   - Verify database indexes

### Step 4: Application Fixes

1. **Fix Code Issues**
   - Review error stack traces
   - Identify root cause in code
   - Fix bugs and deploy hotfix

2. **Add Error Handling**
   - Add try-catch blocks where missing
   - Improve error messages
   - Add retry logic for transient failures

3. **Improve Validation**
   - Add input validation
   - Improve error messages for client errors
   - Add request sanitization

### Step 5: External Dependencies

1. **Check Redis**
   - Verify Redis is healthy
   - Test Redis connectivity
   - Check Redis memory usage
   - Restart Redis if needed: `docker restart beamai-redis`

2. **Check External APIs**
   - Verify external services are up
   - Check network connectivity
   - Review API rate limits

## Verification

After implementing fixes:

1. **Monitor Error Rate**
   - Check error rate in Grafana
   - Verify error rate returns below 1% threshold
   - Monitor for 15-30 minutes to ensure stability

2. **Check Alert Status**
   - Verify alert clears in Alertmanager
   - Check alert history for recurrence

3. **Test Endpoints**
   - Manually test affected endpoints
   - Verify responses are successful
   - Check error logs for new errors

4. **User Impact**
   - Monitor user-facing metrics
   - Check for user complaints
   - Verify service is functioning normally

## Escalation

Escalate to senior engineer if:
- Error rate persists >15 minutes after initial investigation
- Multiple endpoints affected simultaneously
- Service is completely down
- Database is unreachable
- Unable to identify root cause after 30 minutes
- Data corruption suspected

## Relevant Metrics and Queries

### Prometheus Queries

**Current Error Rate:**
```promql
sum(rate(http_errors_total[2m])) by (endpoint, status_code)
/
sum(rate(http_requests_total[2m])) by (endpoint)
```

**Error Rate by Status Code:**
```promql
sum(rate(http_errors_total[5m])) by (status_code)
/
sum(rate(http_requests_total[5m]))
```

**4xx vs 5xx Errors:**
```promql
# 4xx Errors
sum(rate(http_errors_total{status_code=~"4.."}[5m])) by (endpoint)

# 5xx Errors
sum(rate(http_errors_total{status_code=~"5.."}[5m])) by (endpoint)
```

**Request Rate:**
```promql
sum(rate(http_requests_total[5m])) by (endpoint, status)
```

**Error Count by Endpoint:**
```promql
sum(rate(http_errors_total[5m])) by (endpoint, status_code)
```

**Database Connection Pool:**
```promql
db_connection_pool_size{state="active"}
db_connection_pool_size{state="idle"}
```

## Prevention

1. **Error Monitoring**
   - Set up proactive error rate monitoring
   - Alert on error rate > 0.5% (warning)
   - Review error trends regularly

2. **Testing**
   - Comprehensive unit tests
   - Integration tests
   - Error scenario testing

3. **Error Handling**
   - Comprehensive error handling
   - Proper exception handling
   - Graceful degradation

4. **Monitoring**
   - Structured logging
   - Error tracking
   - Performance monitoring

5. **Deployment Practices**
   - Staged rollouts
   - Canary deployments
   - Rollback procedures

## Related Alerts

- `p99_latency_high` - High latency may cause timeouts and errors
- `db_pool_exhausted` - Database issues can cause errors
- `cache_hit_rate_low` - Cache issues may cause errors

## References

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana Dashboard: Service Health Overview](http://localhost:3000/d/service-health-overview)
- [Alertmanager UI](http://localhost:9093)
- Application Logs: `docker logs beamai-backend`

