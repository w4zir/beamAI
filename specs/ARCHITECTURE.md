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