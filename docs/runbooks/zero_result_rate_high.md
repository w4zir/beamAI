# Runbook: zero_result_rate_high

## Alert Information

- **Alert Name**: `zero_result_rate_high`
- **Severity**: Warning
- **Threshold**: Zero-result rate > 10% for 10 minutes
- **Action**: Slack alert to #alerts channel

## Symptoms

- High percentage of search queries returning zero results
- Users unable to find products they're searching for
- Search quality degradation
- User frustration and potential churn

## Immediate Investigation Steps

1. **Check Alert Details**
   - Identify query patterns with high zero-result rate
   - Check the exact zero-result rate percentage
   - Review alert history in Alertmanager UI (http://localhost:9093)

2. **Check Search Metrics in Grafana**
   - Open Search Performance dashboard
   - Review zero-result rate trends
   - Check search request rate
   - Review search latency (may be correlated)

3. **Analyze Query Patterns**
   - Review query patterns in logs: `docker logs beamai-backend --tail 500 | grep "search_zero_results"`
   - Identify common query patterns
   - Check for unusual query patterns
   - Review query normalization

4. **Check Search Index**
   - Verify search index is healthy
   - Check FAISS index availability: `semantic_index_available` metric
   - Review index size: `semantic_index_total_products` metric
   - Check for index corruption

5. **Check Database**
   - Verify products table has data
   - Check database connectivity
   - Review database query performance
   - Verify search indexes exist

6. **Review Recent Changes**
   - Check for recent code deployments
   - Review search algorithm changes
   - Check for configuration changes
   - Review query enhancement changes

## Common Root Causes

1. **Search Index Issues**
   - FAISS index not loaded or corrupted
   - Index out of date (products added but not indexed)
   - Index rebuild failures
   - Index memory issues

2. **Query Understanding Issues**
   - Query normalization problems
   - Query enhancement failures
   - Synonym expansion issues
   - Spell correction problems

3. **Data Quality Issues**
   - Products missing from database
   - Product descriptions incomplete
   - Data synchronization issues
   - Product deletion without index update

4. **Search Algorithm Issues**
   - Search threshold too high
   - Ranking algorithm too strict
   - Hybrid search merge issues
   - Semantic search failures

5. **Configuration Issues**
   - Search configuration changes
   - Index path misconfiguration
   - Search service misconfiguration

6. **Recent Deployments**
   - Search algorithm changes
   - Query processing changes
   - Index format changes
   - Breaking changes in search logic

7. **Unusual Query Patterns**
   - New product categories
   - Seasonal queries
   - Trending products not yet indexed
   - Typos or unusual spellings

## Resolution Steps

### Step 1: Immediate Investigation

1. **Check Search Index Status**
   ```bash
   # Check FAISS index availability
   curl http://localhost:8000/metrics | grep semantic_index_available
   
   # Check index size
   curl http://localhost:8000/metrics | grep semantic_index_total_products
   ```

2. **Review Query Patterns**
   - Check logs for common zero-result queries
   - Identify patterns (e.g., specific categories, brands)
   - Review query normalization

3. **Test Search Manually**
   ```bash
   # Test a known query that should return results
   curl "http://localhost:8000/search?q=running+shoes&k=10"
   ```

### Step 2: Search Index Issues

1. **Rebuild FAISS Index** (if index is corrupted or missing)
   ```bash
   docker exec beamai-backend python scripts/build_faiss_index.py
   ```

2. **Verify Index Loaded**
   - Check `semantic_index_available` metric
   - Verify index file exists
   - Check index memory usage

3. **Update Index** (if products added but not indexed)
   - Run index rebuild script
   - Verify new products are indexed
   - Check index size matches product count

### Step 3: Query Enhancement

1. **Review Query Normalization**
   - Check query normalization logic
   - Verify query preprocessing
   - Review query cleaning

2. **Improve Query Understanding**
   - Review query enhancement rules
   - Add synonyms for common queries
   - Improve spell correction

3. **Test Query Enhancement**
   - Test query normalization
   - Verify query expansion
   - Check query classification

### Step 4: Data Quality

1. **Verify Product Data**
   - Check products table has data
   - Verify product descriptions are complete
   - Check for data synchronization issues

2. **Review Product Indexing**
   - Verify products are indexed
   - Check for missing products
   - Review product deletion process

3. **Data Synchronization**
   - Check for data sync delays
   - Verify product updates are reflected
   - Review data pipeline

### Step 5: Search Algorithm Tuning

1. **Adjust Search Thresholds**
   - Review search score thresholds
   - Lower thresholds if too strict
   - Balance relevance vs. recall

2. **Improve Hybrid Search**
   - Review keyword vs. semantic search balance
   - Adjust merge logic
   - Improve result combination

3. **Optimize Ranking**
   - Review ranking algorithm
   - Adjust ranking weights
   - Improve relevance scoring

## Verification

After implementing fixes:

1. **Monitor Zero-Result Rate**
   - Check zero-result rate in Grafana
   - Verify rate returns below 10% threshold
   - Monitor for 30-60 minutes to ensure stability

2. **Test Search Queries**
   - Test previously failing queries
   - Verify results are returned
   - Check result relevance

3. **Check Alert Status**
   - Verify alert clears in Alertmanager
   - Check alert history for recurrence

4. **User Impact**
   - Monitor user search behavior
   - Check for user complaints
   - Review search analytics

## Escalation

Escalate to senior engineer if:
- Zero-result rate persists >30 minutes after initial investigation
- Search index is completely unavailable
- Multiple query patterns affected
- Unable to identify root cause after 1 hour
- Data corruption suspected

## Relevant Metrics and Queries

### Prometheus Queries

**Current Zero-Result Rate:**
```promql
sum(rate(search_zero_results_total[10m])) by (query_pattern)
/
sum(rate(http_requests_total{endpoint="/search"}[10m]))
```

**Zero-Result Count:**
```promql
sum(rate(search_zero_results_total[5m])) by (query_pattern)
```

**Search Request Rate:**
```promql
sum(rate(http_requests_total{endpoint="/search"}[5m]))
```

**Search Latency:**
```promql
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket{endpoint="/search"}[5m])) by (le)
)
```

**FAISS Index Status:**
```promql
semantic_index_available
semantic_index_total_products
semantic_index_memory_bytes
```

**Search Error Rate:**
```promql
sum(rate(http_errors_total{endpoint="/search"}[5m]))
/
sum(rate(http_requests_total{endpoint="/search"}[5m]))
```

## Prevention

1. **Proactive Monitoring**
   - Monitor zero-result rate daily
   - Set up warning alerts at 5% zero-result rate
   - Review search quality metrics regularly

2. **Index Maintenance**
   - Regular index rebuilds
   - Automated index updates
   - Index health checks

3. **Query Enhancement**
   - Regular synonym updates
   - Spell correction improvements
   - Query pattern analysis

4. **Data Quality**
   - Product data validation
   - Data synchronization monitoring
   - Product description quality checks

5. **Testing**
   - Regular search quality testing
   - Query pattern testing
   - Index rebuild testing

## Related Alerts

- `p99_latency_high` - Search latency may indicate search issues
- `error_rate_high` - Search errors may cause zero results
- `cache_hit_rate_low` - Cache issues may affect search

## References

- [Prometheus Alerting Documentation](https://prometheus.io/docs/alerting/latest/overview/)
- [Grafana Dashboard: Search Performance](http://localhost:3000/d/search-performance)
- [Alertmanager UI](http://localhost:9093)
- Search Logs: `docker logs beamai-backend | grep search`

