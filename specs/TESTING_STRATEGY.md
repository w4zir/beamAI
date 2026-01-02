## Testing Pyramid

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

## Ranking Test Cases

### Golden Dataset
- 1000 hand-labeled query-product pairs
- Rating scale: 0 (irrelevant) to 4 (perfect)
- Updated quarterly

### Regression Tests
```python
def test_ranking_regression():
    for query, expected_products in golden_dataset:
        results = search(query, k=10)
        assert expected_products[0] in results[:3]  # Top product in top 3
        ndcg = compute_ndcg(results, expected_products)
        assert ndcg > 0.65  # Minimum quality threshold
```

### Shadow Mode Testing
- New model runs in parallel with production
- Compare outputs, but don't serve to users
- Measure metric differences without risk