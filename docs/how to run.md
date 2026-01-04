# How to Run and Test

This document provides step-by-step instructions for running and testing the BeamAI search and recommendation system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Running the System](#running-the-system)
4. [Testing the System](#testing-the-system)
5. [Monitoring with Prometheus & Grafana](#monitoring-with-prometheus--grafana)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before running the system, ensure you have the following installed:

### Required Software

- **Node.js 22+** (recommended: use [nvm](https://github.com/nvm-sh/nvm))
- **Python 3.11+** (recommended: use [pyenv](https://github.com/pyenv/pyenv))
- **[uv](https://github.com/astral-sh/uv)** for Python package management
- **Docker and Docker Compose** for running Supabase standalone container
- **Git** for cloning the repository

### Verify Installation

```bash
# Check Node.js version
node --version  # Should be 22.x or higher

# Check Python version
python --version  # Should be 3.11 or higher

# Check uv installation
uv --version

# Check Docker
docker --version
docker-compose --version
```

---

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd beamAI
```

### 2. Install Frontend Dependencies

```bash
npm install
```

This installs all Node.js dependencies for the frontend and build scripts.

### 3. Setup Backend Environment

```bash
npm run setup:backend
```

This command:
- Creates a Python virtual environment in `backend/venv`
- Installs all Python dependencies from `backend/requirements.txt`
- Sets up the backend environment

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Supabase Configuration (external standalone container)
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_KEY=your_service_role_key

# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_JSON=true                     # true for JSON output (production), false for console (development)
```

**Structured Logging:**
- The system uses `structlog` for structured JSON logging
- All logs include: `timestamp`, `level`, `service`, `trace_id`, `request_id`, `user_id` (when available)
- Logs output to stdout (for containerized environments)
- Set `LOG_JSON=false` for development (human-readable console output)
- Set `LOG_JSON=true` for production (JSON format for log aggregation)

Create a `frontend/.env` file:

```bash
# Supabase Configuration (external standalone container)
VITE_SUPABASE_URL=http://localhost:54321
VITE_SUPABASE_ANON_KEY=your_anon_key

# Backend API URL
VITE_API_URL=http://localhost:8000
```

**Note:** Ensure your Supabase standalone container is running and update the URLs/keys accordingly. See `docs/SUPABASE_SETUP.md` for Supabase setup instructions.

### 5. Run Database Migrations

Apply database migrations to your Supabase database:

```bash
# If using Supabase CLI
supabase db push

# Or manually apply migrations from supabase/migrations/
```

### 6. Seed the Database

Populate the database with sample data:

```bash
cd backend
python scripts/seed_data.py
```

This creates sample products, users, and events.

### 7. Compute Initial Features

Compute popularity scores for products:

```bash
cd backend
python -m app.services.features.compute
```

This runs the feature computation batch job to calculate initial popularity scores.

---

## Running the System

### Option 1: Run Both Frontend and Backend Together

```bash
npm run dev:both
```

This starts both the frontend (Vite dev server) and backend (FastAPI) simultaneously.

### Option 2: Run Separately

**Terminal 1 - Backend:**
```bash
npm run backend
```

Backend runs on: http://localhost:8000
API docs: http://localhost:8000/docs

**Terminal 2 - Frontend:**
```bash
npm run frontend
```

Frontend runs on: http://localhost:5173

### Option 3: Run with Docker Compose

```bash
docker-compose up
```

This starts all services (PostgreSQL, Redis, Backend, Frontend, Prometheus, Grafana) in containers.

**Note:** Prometheus and Grafana are included in the Docker Compose setup for monitoring. See [Monitoring with Prometheus & Grafana](#monitoring-with-prometheus--grafana) section for details.

---

## Testing the System

### 1. Health Check

Verify the backend is running:

```bash
curl http://localhost:8000/health/
```

Expected response:
```json
{"status": "healthy"}
```

### 2. Test Search Endpoint

**Basic search:**
```bash
curl "http://localhost:8000/search?q=running%20shoes&k=5"
```

**With user ID (for personalization):**
```bash
curl "http://localhost:8000/search?q=laptop&user_id=user_123&k=10"
```

**Expected response:**
```json
[
  {
    "product_id": "prod_123",
    "score": 0.87,
    "reason": "Ranked score: 0.870 (search: 0.920, popularity: 0.850, freshness: 0.950)"
  },
  ...
]
```

### 3. Test Recommendation Endpoint

```bash
curl "http://localhost:8000/recommend/user_123?k=10"
```

**Expected response:**
```json
[
  {
    "product_id": "prod_456",
    "score": 0.65,
    "reason": "Ranked score: 0.650 (popularity: 0.800, freshness: 0.500)"
  },
  ...
]
```

### 4. Test Event Tracking

```bash
curl -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "product_id": "prod_456",
    "event_type": "view",
    "source": "search"
  }'
```

**Expected response:**
```json
{
  "success": true,
  "event_id": "event_789"
}
```

### 5. Run Backend Tests

```bash
cd backend
pytest tests/
```

This runs all unit and integration tests.

**Run specific test file:**
```bash
pytest tests/test_search.py -v
pytest tests/test_logging.py -v
pytest tests/test_trace_propagation.py -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=app --cov-report=html
```

### 6. Test Structured Logging

The system uses structured JSON logging with trace ID propagation. Test logging functionality:

**Test logging configuration:**
```bash
cd backend
pytest tests/test_logging.py -v
```

**Test trace ID propagation:**
```bash
cd backend
pytest tests/test_trace_propagation.py -v
```

**Verify trace ID in API responses:**
```bash
# Make a request and check response headers
curl -v "http://localhost:8000/search?q=test&k=5"

# Look for X-Trace-ID and X-Request-ID headers in response
```

**Test with custom trace ID:**
```bash
# Pass trace ID in header
curl -H "X-Trace-ID: my-custom-trace-123" \
  "http://localhost:8000/search?q=test&k=5"

# Response will include the same trace ID
```

**View structured logs:**
- When `LOG_JSON=true` (default in production), logs are output as JSON
- When `LOG_JSON=false` (development), logs are formatted for console readability
- All logs include: `timestamp`, `level`, `service`, `trace_id`, `request_id`, `user_id` (when available)

**Example log entry (JSON format):**
```json
{
  "timestamp": "2026-01-02T10:30:45.123456Z",
  "level": "INFO",
  "service": "beamai_search_api",
  "trace_id": "abc123-def456-ghi789",
  "request_id": "req-123-456",
  "event": "search_completed",
  "query": "running shoes",
  "results_count": 42,
  "latency_ms": 87,
  "cache_hit": false
}
```

**Log Events:**
The system logs the following events:
- `request_started` - When a request is received
- `request_completed` - When a request finishes successfully
- `request_failed` - When a request fails with an error
- `search_started` - Search query initiated
- `search_completed` - Search query finished
- `search_zero_results` - Search returned no results
- `search_error` - Search encountered an error
- `recommendation_started` - Recommendation request started
- `recommendation_completed` - Recommendation request finished
- `recommendation_zero_results` - Recommendation returned no results
- `recommendation_error` - Recommendation encountered an error
- `ranking_started` - Ranking process started
- `ranking_completed` - Ranking process finished
- `ranking_product_scored` - Individual product scoring (DEBUG level)

### 7. Test Feature Computation

Compute popularity scores:

```bash
cd backend
python -m app.services.features.compute
```

**Expected output:**
```
==================================================
Starting feature computation batch job
==================================================
✓ Popularity scores: Updated 150 products
==================================================
Feature computation batch job completed
==================================================
```

### 8. Test Frontend

1. Open http://localhost:5173 in your browser
2. Navigate to the Search page
3. Enter a search query (e.g., "shoes")
4. Verify results are displayed with scores
5. Navigate to the Recommendations page
6. Verify recommendations are displayed

---

## Monitoring with Prometheus & Grafana

The system includes comprehensive metrics collection using Prometheus and visualization with Grafana dashboards (Phase 1.2 implementation).

### Architecture

```
Backend API (FastAPI)
    ↓ (exposes /metrics endpoint)
Prometheus (scrapes metrics every 15s)
    ↓ (data source)
Grafana (visualizes metrics in dashboards)
```

### Starting the Monitoring Stack

**Option 1: With Docker Compose (Recommended)**

The monitoring stack is included in `docker-compose.yml`. Start Prometheus and Grafana:

```bash
# Start only monitoring services
docker-compose up -d prometheus grafana

# Or start everything including backend
docker-compose up -d
```

**Option 2: Standalone (Backend Running Locally)**

If running the backend locally (not in Docker), update `monitoring/prometheus/prometheus.yml` to scrape `host.docker.internal:8000` instead of `backend:8000`, then start Prometheus and Grafana:

```bash
docker-compose up -d prometheus grafana
```

### Accessing Prometheus

- **URL**: http://localhost:9090
- **Metrics Endpoint**: http://localhost:8000/metrics (exposed by backend)
- **Targets**: http://localhost:9090/targets (verify backend is being scraped)

**Query Metrics in Prometheus:**

Use PromQL queries to explore metrics:

```promql
# Request rate per endpoint
rate(http_requests_total[5m])

# Error rate
rate(http_errors_total[5m])

# p95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# CPU usage
system_cpu_usage_percent

# Memory usage
system_memory_usage_bytes / 1024 / 1024  # MB

# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

### Accessing Grafana

- **URL**: http://localhost:3000
- **Default Credentials**:
  - Username: `admin`
  - Password: `admin`
- **Change Password**: You'll be prompted to change the password on first login

**View Dashboards:**

1. Login to Grafana at http://localhost:3000
2. Click "Dashboards" → "Browse" in the left menu
3. Five dashboards are automatically provisioned:
   - **Service Health Overview**: Overall system health, request rates, errors, latency
   - **Search Performance**: Search-specific metrics (rate, latency, zero-results, cache hits)
   - **Recommendation Performance**: Recommendation-specific metrics
   - **Database Health**: Connection pool usage and database metrics
   - **Cache Performance**: Cache hit/miss rates by type

### Available Metrics

The system exposes comprehensive metrics following Prometheus conventions:

#### RED Metrics (Rate, Errors, Duration)

- **`http_requests_total{method, endpoint, status}`**: Total HTTP requests
  - Labels: `method` (GET, POST), `endpoint` (normalized path), `status` (200, 404, 500, etc.)
  - Example: `http_requests_total{method="GET", endpoint="/search", status="200"}`

- **`http_errors_total{method, endpoint, status_code}`**: Total HTTP errors (4xx and 5xx)
  - Labels: `method`, `endpoint`, `status_code`
  - Separate counters for client errors (4xx) and server errors (5xx)

- **`http_request_duration_seconds{method, endpoint}`**: Request latency histogram
  - Buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0] seconds
  - Calculate percentiles: p50, p95, p99, p999

#### Business Metrics

- **`search_zero_results_total{query_pattern}`**: Zero-result searches
  - Tracks searches that return no results
  - Label: `query_pattern` (normalized query pattern for grouping)

- **`cache_hits_total{cache_type}`**: Cache hits
  - Labels: `cache_type` (e.g., "search", "recommendation", "features")

- **`cache_misses_total{cache_type}`**: Cache misses
  - Labels: `cache_type`

- **`ranking_score_distribution{product_id}`**: Ranking score distribution
  - Histogram of ranking scores (0.0 to 1.0)
  - Useful for analyzing score distributions

#### Resource Metrics

- **`system_cpu_usage_percent`**: CPU usage percentage (gauge)
  - Updated on each metrics scrape

- **`system_memory_usage_bytes`**: Memory usage in bytes (gauge)
  - Updated on each metrics scrape

- **`db_connection_pool_size{state}`**: Database connection pool metrics
  - Labels: `state` ("active", "idle", "total")
  - Tracks connection pool utilization

### Testing Metrics Collection

**1. Verify Metrics Endpoint:**

```bash
# Check metrics endpoint is accessible
curl http://localhost:8000/metrics

# Should return Prometheus-formatted metrics
```

**2. Generate Test Metrics:**

Make some API calls to generate metrics:

```bash
# Search requests
curl "http://localhost:8000/search?q=running+shoes&k=5"
curl "http://localhost:8000/search?q=laptop&k=10"

# Recommendation requests
curl "http://localhost:8000/recommend/user123?k=10"

# Health check
curl "http://localhost:8000/health/"

# Generate errors (for testing error metrics)
curl "http://localhost:8000/search?q="  # Invalid query
```

Wait 15-30 seconds for Prometheus to scrape metrics, then check Grafana dashboards.

**3. Run Automated Tests:**

```bash
# Test Prometheus and Grafana setup
cd backend
python scripts/test_grafana_dashboards.py
```

This script verifies:
- Backend metrics endpoint is accessible
- Prometheus can scrape metrics
- Grafana can connect to Prometheus
- All dashboards are loaded
- Dashboard queries return data

**Expected output:**
```
✓ Backend metrics endpoint accessible (8 metrics found)
✓ Prometheus is accessible and responding to queries
✓ Prometheus has 1 healthy backend target(s)
✓ Grafana has Prometheus datasource configured
✓ All 5 expected dashboards found
✓ All dashboard queries successful
```

### Viewing Metrics in Grafana

**Service Health Overview Dashboard:**

- Request rate per endpoint (requests/second)
- Error rate per endpoint (errors/second)
- Latency percentiles (p50, p95, p99) per endpoint
- CPU and memory usage over time

**Search Performance Dashboard:**

- Search request rate
- Search latency (p50, p95, p99)
- Search error rate (4xx, 5xx)
- Zero-result rate percentage
- Cache hit rate for searches

**Recommendation Performance Dashboard:**

- Recommendation request rate
- Recommendation latency (p50, p95, p99)
- Recommendation error rate
- Cache hit rate for recommendations

**Database Health Dashboard:**

- Connection pool usage (active, idle, total)
- Connection pool utilization percentage
- Available connections (alerts if < 2)

**Cache Performance Dashboard:**

- Cache hit rate by type (search, recommendation, features)
- Cache hit/miss rates over time
- Total cache operations

### Prometheus Configuration

Configuration file: `monitoring/prometheus/prometheus.yml`

**Key Settings:**
- Scrape interval: 15 seconds
- Scrape timeout: 10 seconds
- Retention: 30 days
- Target: `backend:8000/metrics` (or `host.docker.internal:8000` for local backend)

**Reload Configuration:**

```bash
# Reload Prometheus config without restart
curl -X POST http://localhost:9090/-/reload

# Or restart Prometheus
docker-compose restart prometheus
```

### Grafana Configuration

**Automatic Provisioning:**

- **Data Sources**: `monitoring/grafana/provisioning/datasources/prometheus.yml`
  - Automatically configures Prometheus as data source
  - URL: `http://prometheus:9090`

- **Dashboards**: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
  - Automatically loads dashboards from `monitoring/grafana/dashboards/`
  - Dashboards are read-only by default (can be edited in UI)

**Customizing Dashboards:**

1. Open Grafana UI
2. Edit dashboard panels
3. Export dashboard JSON
4. Save to `monitoring/grafana/dashboards/` for persistence

### Troubleshooting Monitoring

**Prometheus not scraping metrics:**

1. Check Prometheus targets: http://localhost:9090/targets
   - Should show `beamai-backend` target as "UP"
2. Verify backend metrics endpoint: `curl http://localhost:8000/metrics`
3. Check Prometheus logs: `docker logs beamai-prometheus`
4. Verify network connectivity: Ensure Prometheus can reach backend

**Grafana dashboards show "No data":**

1. Verify Prometheus datasource:
   - Grafana → Configuration → Data Sources
   - Test connection to Prometheus
2. Check time range: Try "Last 1 hour" or "Last 5 minutes"
3. Verify metrics are being generated:
   - Make API calls to generate metrics
   - Wait 15-30 seconds for Prometheus to scrape
   - Check Prometheus UI for metrics
4. Check dashboard queries:
   - Open dashboard panel → Edit
   - Verify PromQL query is correct
   - Test query in Prometheus UI first

**Dashboards not appearing:**

1. Check Grafana logs: `docker logs beamai-grafana`
2. Verify dashboard files exist: `ls monitoring/grafana/dashboards/`
3. Check provisioning config: `cat monitoring/grafana/provisioning/dashboards/dashboards.yml`
4. Restart Grafana: `docker-compose restart grafana`

**Metrics endpoint returns empty:**

1. Verify backend is running: `curl http://localhost:8000/health/`
2. Check metrics module is imported: Verify `app/core/metrics.py` exists
3. Make some API calls to generate metrics
4. Check backend logs for errors

### Production Considerations

For production deployments:

1. **Change Grafana Credentials**: Update `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml`
2. **Secure Prometheus**: Add authentication if exposing Prometheus publicly
3. **Configure Alerting**: Set up Prometheus Alertmanager for alerts (see Phase 1.4)
4. **Persistent Storage**: Prometheus data is stored in Docker volume (30-day retention)
5. **Resource Limits**: Set resource limits for Prometheus and Grafana containers
6. **Backup Dashboards**: Export and backup dashboard JSON files

### Metrics Best Practices

1. **Monitor Key Metrics**:
   - Request rate and latency (p95, p99)
   - Error rate (should be < 0.1%)
   - Cache hit rate (target: > 70%)
   - Zero-result rate (target: < 5%)

2. **Set Up Alerts** (Future):
   - p99 latency > 500ms for 5 minutes
   - Error rate > 1% for 2 minutes
   - Zero-result rate > 10% for 10 minutes
   - Database connection pool exhaustion

3. **Regular Review**:
   - Review dashboards weekly
   - Analyze trends and anomalies
   - Optimize based on metrics

For more details, see `monitoring/README.md` and `monitoring/QUICK_START.md`.

---

## Testing Scenarios

### Scenario 1: End-to-End Search Flow

1. **Seed database** with products:
   ```bash
   cd backend
   python scripts/seed_data.py
   ```

2. **Compute features**:
   ```bash
   python -m app.services.features.compute
   ```

3. **Search for products**:
   ```bash
   curl "http://localhost:8000/search?q=electronics&k=5"
   ```

4. **Track a view event**:
   ```bash
   curl -X POST "http://localhost:8000/events" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "user_123",
       "product_id": "prod_456",
       "event_type": "view",
       "source": "search"
     }'
   ```

5. **Recompute features** (to see updated popularity):
   ```bash
   python -m app.services.features.compute
   ```

### Scenario 2: Recommendation Flow

1. **Get recommendations for a user**:
   ```bash
   curl "http://localhost:8000/recommend/user_123?k=10"
   ```

2. **Track multiple events** (simulate user interactions):
   ```bash
   # View event
   curl -X POST "http://localhost:8000/events" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user_123", "product_id": "prod_1", "event_type": "view"}'
   
   # Add to cart
   curl -X POST "http://localhost:8000/events" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user_123", "product_id": "prod_2", "event_type": "add_to_cart"}'
   
   # Purchase
   curl -X POST "http://localhost:8000/events" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user_123", "product_id": "prod_3", "event_type": "purchase"}'
   ```

3. **Recompute features**:
   ```bash
   python -m app.services.features.compute
   ```

4. **Get updated recommendations**:
   ```bash
   curl "http://localhost:8000/recommend/user_123?k=10"
   ```

### Scenario 3: Error Handling

**Test invalid search query:**
```bash
curl "http://localhost:8000/search?q="
```

Expected: 400 Bad Request

**Test invalid event type:**
```bash
curl -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_123", "product_id": "prod_456", "event_type": "invalid"}'
```

Expected: 400 Bad Request with error message

**Test non-existent user recommendations:**
```bash
curl "http://localhost:8000/recommend/non_existent_user?k=10"
```

Expected: Returns empty list or recommendations (system continues gracefully)

---

## Performance Testing

### Load Testing with Apache Bench

**Test search endpoint:**
```bash
ab -n 1000 -c 10 "http://localhost:8000/search?q=shoes&k=10"
```

**Test recommendation endpoint:**
```bash
ab -n 1000 -c 10 "http://localhost:8000/recommend/user_123?k=10"
```

### Monitor Logs

**Backend logs:**
- Check console output for request/response logs
- Logs include timing information for each request
- All logs are structured JSON (when `LOG_JSON=true`) with trace IDs
- Search logs include: `query`, `results_count`, `latency_ms`, `cache_hit`
- Recommendation logs include: `user_id`, `results_count`, `latency_ms`, `cache_hit`
- Ranking logs include: `product_id`, `final_score`, `score_breakdown`

**View logs in JSON format:**
```bash
# Set LOG_JSON=true in .env, then restart backend
# Logs will be output as JSON, one per line
# Example: grep for trace ID
tail -f backend.log | grep "trace_id"
```

**Trace ID correlation:**
- Every request gets a unique `trace_id` (UUID v4)
- Trace ID is extracted from `X-Trace-ID` or `X-Request-ID` headers if present, otherwise generated
- Trace ID is included in response headers (`X-Trace-ID`)
- Every request also gets a unique `request_id` (UUID v4) in `X-Request-ID` header
- All log entries for a request include the same `trace_id` and `request_id`
- Use trace ID to correlate logs across services and debug issues

**Example: Find all logs for a specific request:**
```bash
# If logs are in a file
grep "abc123-def456-ghi789" backend.log

# Or use jq to filter JSON logs
cat backend.log | jq 'select(.trace_id == "abc123-def456-ghi789")'
```

**Trace ID Propagation:**
- Trace IDs are propagated via HTTP headers (`X-Trace-ID` or `X-Request-ID`)
- Middleware automatically extracts or generates trace IDs for every request
- Trace IDs are stored in context variables and automatically included in all log entries
- User IDs are extracted from query parameters (`user_id`) or headers (`X-User-ID`) and included in logs when available

**Database logs:**
- Check Supabase logs for query performance
- Monitor connection pool usage

---

## Troubleshooting

### Backend Issues

**Problem: Virtual environment not found**
```bash
# Solution: Re-run setup
npm run setup:backend
```

**Problem: Import errors**
```bash
# Solution: Ensure you're using the venv Python
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m app.main
```

**Problem: Supabase connection fails**
- Check `.env` file has correct `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Ensure Supabase standalone container is running
- Verify network connectivity to Supabase container
- Test connection:
  ```bash
  cd backend
  python scripts/test_supabase_connection.py
  ```

**Problem: Database migrations fail**
- Ensure migrations are applied to your Supabase database
- Check migration files in `supabase/migrations/`
- Verify database schema matches expected structure

### Frontend Issues

**Problem: Supabase auth not working**
- Verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env`
- Check browser console for errors
- Ensure Supabase container is accessible

**Problem: API calls fail**
- Check `VITE_API_URL` is set to `http://localhost:8000` in `frontend/.env`
- Verify backend is running on port 8000
- Check CORS configuration in backend

**Problem: Build errors**
```bash
# Solution: Clear node_modules and reinstall
rm -rf node_modules
npm install
```

**Problem: Port already in use**
- Change port in `frontend/vite.config.ts` or `backend/app/main.py`
- Or kill the process using the port:
  ```bash
  # Windows
  netstat -ano | findstr :8000
  taskkill /PID <PID> /F
  
  # Linux/Mac
  lsof -ti:8000 | xargs kill
  ```

### Database Issues

**Problem: Tables not found**
- Ensure migrations are applied
- Check database connection
- Verify Supabase container is running

**Problem: No data**
```bash
# Solution: Run seed script
cd backend
python scripts/seed_data.py
```

**Problem: Popularity scores are zero**
```bash
# Solution: Run feature computation
cd backend
python -m app.services.features.compute
```

**Problem: Freshness scores seem incorrect**
- Check `created_at` timestamps in products table
- Verify timezone handling (should be UTC)
- Check freshness computation logic in `app/services/features/freshness.py`

### Feature Computation Issues

**Problem: Popularity scores not updating**
- Verify events exist in database
- Check event types match expected values (`view`, `add_to_cart`, `purchase`)
- Run feature computation manually:
  ```bash
  cd backend
  python -m app.services.features.compute
  ```

**Problem: Feature computation fails**
- Check database connection
- Verify events table exists and has data
- Check logs for specific error messages

### Logging Issues

**Problem: Logs not in JSON format**
- Check `LOG_JSON` environment variable is set to `true`
- Restart backend after changing environment variables
- Verify structlog is installed: `pip list | grep structlog`
- Check that `configure_logging()` is called with `json_output=True` in `app/main.py`

**Problem: Trace ID not appearing in logs**
- Verify trace ID middleware (`TraceIDMiddleware`) is enabled in `app/main.py`
- Check response headers include `X-Trace-ID` and `X-Request-ID`
- Ensure logging is configured before making requests
- Verify middleware is added after CORS middleware but before routes

**Problem: Logs missing context fields**
- Verify structured logging is configured in `app/core/logging.py`
- Check that context variables (`trace_id_var`, `request_id_var`, `user_id_var`) are set correctly
- Ensure `configure_logging()` is called at application startup in `app/main.py`
- Verify `add_trace_context` processor is included in the processor chain

**Problem: Cannot find logs by trace ID**
- Verify logs are being written to stdout (for containerized environments)
- Check log aggregation tool configuration
- Ensure JSON format is enabled for log parsing (`LOG_JSON=true`)
- Test trace ID extraction: `curl -H "X-Trace-ID: test-123" http://localhost:8000/health/`

**Problem: User ID not appearing in logs**
- User ID is only included when provided via query parameter (`?user_id=...`) or header (`X-User-ID`)
- Check that `set_user_id()` is called in route handlers when user_id is available
- Verify middleware extracts user_id from query params or headers

### Monitoring Issues

**Problem: Prometheus not scraping metrics**
- Check Prometheus targets: http://localhost:9090/targets
- Verify backend metrics endpoint: `curl http://localhost:8000/metrics`
- Check Prometheus logs: `docker logs beamai-prometheus`
- Verify network connectivity between Prometheus and backend containers
- If running backend locally, update `prometheus.yml` to use `host.docker.internal:8000`

**Problem: Grafana dashboards show "No data"**
- Verify Prometheus datasource is configured: Grafana → Configuration → Data Sources
- Test Prometheus connection in Grafana
- Check time range in dashboard (try "Last 1 hour")
- Make API calls to generate metrics, wait 15-30 seconds for Prometheus to scrape
- Verify metrics exist in Prometheus UI: http://localhost:9090

**Problem: Metrics endpoint returns empty**
- Verify backend is running: `curl http://localhost:8000/health/`
- Check that metrics module is imported in `app/main.py`
- Make some API calls to generate metrics
- Check backend logs for errors related to metrics collection

**Problem: Dashboards not appearing in Grafana**
- Check Grafana logs: `docker logs beamai-grafana`
- Verify dashboard files exist: `ls monitoring/grafana/dashboards/`
- Check provisioning configuration: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- Restart Grafana: `docker-compose restart grafana`

---

## Development Workflow

### 1. Make Code Changes

Edit files in `backend/app/` or `frontend/src/`

### 2. Hot Reload

Both frontend and backend support hot reload:
- **Backend**: Uses `uvicorn --reload` (restarts on file changes)
- **Frontend**: Vite HMR (Hot Module Replacement)

### 3. Test Changes

```bash
# Run tests
cd backend
pytest tests/

# Test API endpoints
curl "http://localhost:8000/search?q=test&k=5"
```

### 4. Check Logs

Monitor console output for:
- Request/response logs with trace IDs
- Error messages with full context
- Performance metrics (latency_ms)
- Structured JSON logs (when `LOG_JSON=true`)

**View logs with trace ID:**
```bash
# Filter logs by trace ID
tail -f backend.log | grep "trace_id"

# Or use jq for JSON logs
tail -f backend.log | jq 'select(.trace_id == "your-trace-id")'
```

**Common log events:**
- `request_started` - Request received (includes method, path, query_params, client_host)
- `request_completed` - Request finished successfully (includes status_code, latency_ms)
- `request_failed` - Request failed with error (includes error, error_type, latency_ms)
- `search_started` - Search query initiated (includes query, user_id, k)
- `search_completed` - Search query finished (includes query, user_id, results_count, latency_ms, cache_hit)
- `search_zero_results` - Search returned no results (includes query, user_id, latency_ms, cache_hit)
- `search_error` - Search encountered an error (includes query, user_id, error, error_type, latency_ms)
- `recommendation_started` - Recommendation request started (includes user_id, k)
- `recommendation_completed` - Recommendation request finished (includes user_id, results_count, latency_ms, cache_hit)
- `recommendation_zero_results` - Recommendation returned no results (includes user_id, latency_ms, cache_hit)
- `recommendation_error` - Recommendation encountered an error (includes user_id, error, error_type, latency_ms)
- `ranking_started` - Ranking process started (includes is_search, user_id, candidates_count, weights)
- `ranking_completed` - Ranking process finished (includes is_search, user_id, ranked_count, candidates_count)
- `ranking_product_scored` - Individual product scoring (DEBUG level, includes product_id, final_score, score_breakdown)

---

## Production Deployment

### Backend Deployment

1. **Build Docker image:**
   ```bash
   cd backend
   docker build -t beamai-backend .
   ```

2. **Set environment variables:**
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `DATABASE_URL` (if using direct Postgres connection)
   - `REDIS_URL` (if using Redis)
   - `LOG_LEVEL` (default: INFO)
   - `LOG_JSON` (default: true for production)

3. **Run container:**
   ```bash
   docker run -p 8000:8000 \
     -e SUPABASE_URL=$SUPABASE_URL \
     -e SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY \
     beamai-backend
   ```

### Frontend Deployment

1. **Build for production:**
   ```bash
   cd frontend
   npm run build
   ```

2. **Deploy `dist/` directory** to:
   - Vercel
   - Netlify
   - AWS S3 + CloudFront
   - Any static hosting service

3. **Set environment variables** in hosting platform:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_URL`

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Architecture**: See `specs/ARCHITECTURE.md`
- **Feature Definitions**: See `specs/FEATURE_DEFINITIONS.md`
- **Ranking Logic**: See `specs/RANKING_LOGIC.md`
- **Testing Strategy**: See `specs/TESTING_STRATEGY.md`
- **Observability**: See `specs/OBSERVABILITY.md`

---

## Quick Reference

### Common Commands

```bash
# Setup
npm install
npm run setup:backend

# Run
npm run dev:both          # Both frontend and backend
npm run backend           # Backend only
npm run frontend          # Frontend only

# Testing
cd backend && pytest tests/
cd backend && pytest tests/test_logging.py -v
cd backend && pytest tests/test_trace_propagation.py -v
curl "http://localhost:8000/search?q=test&k=5"
curl -H "X-Trace-ID: test-123" "http://localhost:8000/search?q=test&k=5"

# Feature Computation
cd backend && python -m app.services.features.compute

# Database
cd backend && python scripts/seed_data.py
```

### URLs

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health/
- Metrics Endpoint: http://localhost:8000/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

---

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Test search**: Try different queries and verify results
3. **Track events**: Simulate user interactions
4. **Monitor features**: Recompute features and see how scores change
5. **Test structured logging**: Verify trace IDs appear in logs and response headers
6. **Read architecture docs**: Understand system design in `specs/`

### Observability Features

The system includes comprehensive structured logging:

- **Trace ID Propagation**: Every request gets a unique trace ID for correlation
- **Structured Logs**: JSON-formatted logs with consistent fields
- **Request Context**: trace_id, request_id, and user_id automatically included
- **Performance Tracking**: Latency metrics in all endpoint logs
- **Error Context**: Full error context with trace IDs for debugging

**Verify observability:**
```bash
# Check trace ID in response headers
curl -v "http://localhost:8000/search?q=test&k=5" 2>&1 | grep -i trace

# View structured logs (if LOG_JSON=true)
# Logs will be JSON format, one per line
# Use jq to parse: cat logs.txt | jq '.trace_id'
```

For more details, see the main [README.md](../README.md) file.

