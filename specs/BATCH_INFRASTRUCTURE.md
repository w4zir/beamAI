# BATCH_INFRASTRUCTURE.md

## Purpose

This document defines the batch job infrastructure for offline feature computation, model training, and data processing. Batch jobs are critical for maintaining fresh features and models without impacting real-time serving performance.

**Alignment**: Implements Phase 6.3 from `docs/TODO/implementation_phases.md`

---

## Design Principles

1. **Separation of Concerns**: Batch jobs run independently of serving code
2. **Idempotency**: Jobs can be safely retried without side effects
3. **Observability**: All jobs are monitored and logged
4. **Zero-Downtime**: Jobs don't impact serving performance
5. **Failure Recovery**: Automatic retries with exponential backoff

---

## Orchestration Framework

### Tool Selection

**Primary**: Apache Airflow or Prefect (cloud-agnostic)

**Requirements**:
- Cloud-agnostic (no cloud-specific SDKs)
- DAG/workflow definition
- Scheduling and dependency management
- Retry logic and error handling
- Monitoring and alerting

**Recommendation**: Start with Prefect (simpler, Python-native) or Airflow (more features, industry standard)

### Job Definition

**Format**: Python DAG/workflow files

**Location**: `backend/jobs/` directory

**Structure**:
```python
from prefect import flow, task

@task
def compute_popularity_scores():
    """Compute popularity scores for all products"""
    pass

@flow
def popularity_score_flow():
    compute_popularity_scores()

# Schedule: Every 5 minutes
```

---

## Batch Job Definitions

### 1. Popularity Score Computation

**Purpose**: Compute weighted popularity scores for all products

**Schedule**: Every 5 minutes

**Input**: Events table (last 90 days)

**Process**:
1. Query events table (rolling 90-day window)
2. Aggregate events by product_id and event_type
3. Apply weights: purchase=3, add_to_cart=2, view=1
4. Compute time-decay factor
5. Calculate final popularity_score
6. Update products table

**Output**: Updated `popularity_score` in products table

**Performance**: Target <30 seconds for 100K products

**Dependencies**: None (can run independently)

**Error Handling**:
- Retry 3 times with exponential backoff
- Alert if job fails 3 consecutive times
- Fallback to previous scores if job fails

### 2. User Category Affinity

**Purpose**: Compute user preference strength per category

**Schedule**: Daily (overnight)

**Input**: Events table (last 90 days)

**Process**:
1. Query events table grouped by user_id and category
2. Count interactions per category
3. Apply time-decay (recent interactions weighted higher)
4. Normalize scores (0.0 to 1.0)
5. Store in feature store (Redis or Postgres)

**Output**: `user_category_affinity` feature per user

**Performance**: Target <5 minutes for 1M users

**Dependencies**: None

**Error Handling**:
- Retry 3 times
- Alert if job fails
- Partial updates allowed (update users incrementally)

### 3. FAISS Index Rebuild

**Purpose**: Rebuild FAISS index with latest product embeddings

**Schedule**: Weekly (Sunday 2 AM)

**Input**: Products table (all products with descriptions)

**Process**:
1. Generate embeddings for all products (SentenceTransformers)
2. Build FAISS index (IndexIVFFlat or IndexHNSW)
3. Save index to disk
4. Validate index (test queries)
5. Deploy new index (zero-downtime):
   - Load new index alongside old index
   - Switch traffic to new index
   - Keep old index for 24 hours (rollback safety)

**Output**: New FAISS index file

**Performance**: Target <2 hours for 1M products

**Dependencies**: Product embeddings must be up-to-date

**Error Handling**:
- Retry once (long-running job)
- Alert if index build fails
- Keep old index if new index fails validation
- Rollback to old index if new index causes errors

**Zero-Downtime Deployment**:
1. Build new index in background
2. Load new index in memory (alongside old index)
3. Route 10% of traffic to new index (canary)
4. Monitor metrics (latency, error rate)
5. If metrics good, route 100% traffic to new index
6. If metrics bad, rollback to old index

### 4. Collaborative Filtering Training

**Purpose**: Train Implicit ALS model for user-product affinity

**Schedule**: Daily (overnight)

**Input**: Events table (user-product interaction matrix)

**Process**:
1. Extract user-product interaction matrix from events
2. Filter sparse interactions (users/products with <5 interactions)
3. Train Implicit ALS model
4. Extract user factors and item factors
5. Save model artifacts (user factors, item factors, metadata)
6. Deploy new model (shadow mode first):
   - Load new model alongside old model
   - Run both models on production traffic (shadow mode)
   - Compare metrics (NDCG, CTR)
   - If new model better, gradually roll out (10% → 50% → 100%)

**Output**: Model artifacts (user factors, item factors)

**Performance**: Target <1 hour for 1M users, 100K products

**Dependencies**: Events table must be up-to-date

**Error Handling**:
- Retry once (long-running job)
- Alert if training fails
- Keep old model if new model fails validation
- Rollback to old model if new model performs worse

**Shadow Mode**:
- Run new model alongside old model
- Don't serve new model results to users
- Compare outputs and metrics
- Gradually roll out if new model performs better

### 5. Feature Backfill

**Purpose**: Recompute features for date range (on-demand)

**Schedule**: On-demand (admin-triggered)

**Input**: Date range, feature names, product/user IDs

**Process**:
1. Query events/data for specified date range
2. Recompute features for specified products/users
3. Update feature store
4. Invalidate cache for updated features
5. Generate report (features updated, errors)

**Output**: Updated features, backfill report

**Use Cases**:
- Debugging feature computation
- Model retraining with historical features
- Fixing data quality issues

**Error Handling**:
- Retry failed features individually
- Generate report of successes and failures
- Allow partial backfills

---

## Error Handling & Retries

### Retry Strategy

**Exponential Backoff**:
- First retry: 1 minute
- Second retry: 5 minutes
- Third retry: 15 minutes
- Max retries: 3

**Retry Conditions**:
- Transient errors (database connection, network timeout)
- Rate limits (external APIs)
- Temporary resource unavailability

**No Retry**:
- Permanent errors (invalid data, schema mismatch)
- Authentication failures
- Configuration errors

### Failure Notifications

**Alerts**:
- Job fails 3 consecutive times → Page on-call
- Job takes >2x expected duration → Warning
- Job produces no output → Warning

**Notification Channels**:
- Critical: PagerDuty/OpsGenie
- Warning: Slack #alerts channel

### Dead Letter Queue

**Purpose**: Store failed jobs for manual investigation

**Storage**: Database table or message queue

**Fields**:
- Job ID
- Job name
- Error message
- Stack trace
- Input data
- Timestamp

**Retention**: 30 days

---

## Job Monitoring

### Metrics

**Job Execution Metrics**:
```
batch_job_runs_total{job_name="popularity_scores", status="success"}
batch_job_runs_total{job_name="popularity_scores", status="failure"}
batch_job_duration_seconds{job_name="popularity_scores"}
batch_job_records_processed_total{job_name="popularity_scores"}
```

**Job Health Metrics**:
```
batch_job_last_success_timestamp{job_name="popularity_scores"}
batch_job_last_failure_timestamp{job_name="popularity_scores"}
batch_job_consecutive_failures{job_name="popularity_scores"}
```

### Logging

**Structured Logs**:
- Job start/end timestamps
- Records processed
- Duration
- Errors (if any)
- Output summary

**Example**:
```json
{
  "timestamp": "2026-01-02T10:30:45Z",
  "level": "INFO",
  "event": "batch_job_completed",
  "job_name": "popularity_scores",
  "duration_seconds": 25.3,
  "records_processed": 100000,
  "status": "success"
}
```

### Dashboards

**Batch Job Dashboard** (Grafana):
- Job execution status (success/failure)
- Job duration trends
- Records processed per job
- Error rate
- Last successful run timestamp

**Alerts**:
- Job hasn't run in expected interval → Warning
- Job failed → Critical
- Job duration >2x expected → Warning

---

## Resource Management

### Resource Limits

**CPU**: Allocate based on job requirements
- Popularity scores: 2 CPU cores
- User affinity: 4 CPU cores
- FAISS rebuild: 8 CPU cores
- CF training: 8 CPU cores

**Memory**: Allocate based on data size
- Popularity scores: 4 GB
- User affinity: 8 GB
- FAISS rebuild: 16 GB
- CF training: 16 GB

**Disk**: Temporary storage for intermediate results
- FAISS rebuild: 10 GB (for index files)
- CF training: 5 GB (for model artifacts)

### Resource Isolation

**Separate Workers**: Run batch jobs on separate worker nodes (not serving nodes)

**Resource Quotas**: Set quotas to prevent batch jobs from impacting serving

**Scheduling**: Schedule resource-intensive jobs during low-traffic periods

---

## Data Quality Checks

### Pre-Job Validation

**Input Data Validation**:
- Check data freshness (events ingested within last 5 minutes)
- Check data completeness (required fields not null)
- Check data schema (columns match expected)

**Failure Action**: Skip job run, alert on-call

### Post-Job Validation

**Output Validation**:
- Check feature distributions (detect anomalies)
- Check feature counts (expected number of features)
- Check feature ranges (scores within expected range)

**Failure Action**: Alert on-call, keep previous features

### Data Quality Metrics

```
data_quality_checks_total{check_type="schema_validation", status="pass"}
data_quality_checks_total{check_type="schema_validation", status="fail"}
data_freshness_seconds{data_source="events"}
```

---

## Zero-Downtime Deployment

### Model Deployment

**Process**:
1. Build new model/index in background
2. Load new model/index alongside old model/index
3. Route small percentage of traffic to new model (canary)
4. Monitor metrics (latency, error rate, quality)
5. Gradually increase traffic (10% → 50% → 100%)
6. If issues, rollback to old model

**Rollback Strategy**:
- Keep old model/index for 24 hours
- One-command rollback (switch traffic back)
- Automatic rollback if error rate >1%

### Feature Deployment

**Process**:
1. Compute new features
2. Store in feature store (versioned)
3. Update serving code to use new features
4. Invalidate old feature cache
5. Monitor feature usage

**Rollback Strategy**:
- Keep old feature versions for 7 days
- Rollback by updating feature version in config

---

## Job Dependencies

### Dependency Graph

```
Events Ingested
    ↓
Popularity Scores (every 5 min)
    ↓
User Category Affinity (daily)
    ↓
CF Training (daily)
    ↓
FAISS Rebuild (weekly, depends on product updates)
```

### Dependency Management

**Airflow/Prefect**: Define dependencies in DAG/workflow

**Example**:
```python
@flow
def daily_flow():
    popularity_scores = compute_popularity_scores()
    user_affinity = compute_user_affinity(wait_for=[popularity_scores])
    cf_training = train_cf_model(wait_for=[user_affinity])
```

**Failure Handling**: If dependency fails, skip dependent jobs (with alert)

---

## References

- **Implementation Phases**: `docs/TODO/implementation_phases.md` (Phase 6.3)
- **Feature Definitions**: `specs/FEATURE_DEFINITIONS.md` (Feature Computation)
- **Recommendation Design**: `specs/RECOMMENDATION_DESIGN.md` (CF Training)
- **Search Design**: `specs/SEARCH_DESIGN.md` (FAISS Index)
- **Observability**: `specs/OBSERVABILITY.md` (Monitoring)

---

End of document

