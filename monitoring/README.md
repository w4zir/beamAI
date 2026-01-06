# Monitoring Setup - Prometheus & Grafana

This directory contains the configuration for Prometheus metrics collection and Grafana dashboards for the BeamAI Search & Recommendation API.

## Architecture

```
Backend API (FastAPI)
    ↓ (exposes /metrics endpoint)
Prometheus (scrapes metrics every 15s, evaluates alert rules)
    ↓ (sends alerts)
Alertmanager (manages alerts, routes notifications)
    ↓ (notifications)
Notification Channels (Slack, PagerDuty, Email)
    ↓ (data source)
Grafana (visualizes metrics in dashboards)
```

## Services

### Prometheus
- **Port**: 9090
- **URL**: http://localhost:9090
- **Configuration**: `prometheus/prometheus.yml`
- **Alert Rules**: `prometheus/alerts.yml`
- **Scrapes**: Backend metrics endpoint at `backend:8000/metrics`
- **Evaluates**: Alert rules every 15 seconds
- **Sends Alerts**: To Alertmanager at `alertmanager:9093`

### Alertmanager
- **Port**: 9093
- **URL**: http://localhost:9093
- **Configuration**: `alertmanager/alertmanager.yml`
- **Features**:
  - Alert routing by severity
  - Alert grouping and deduplication
  - Alert silencing
  - Notification channel management
- **Alert Routing**:
  - Critical alerts → PagerDuty (page on-call)
  - Warning alerts → Slack #alerts channel
  - Info alerts → Default receiver

### Grafana
- **Port**: 3000
- **URL**: http://localhost:3000
- **Default Credentials**: 
  - Username: `admin`
  - Password: `admin`
- **Dashboards**: Automatically provisioned from `grafana/dashboards/`
- **Data Source**: Prometheus (automatically configured)

## Dashboards

Five dashboards are automatically provisioned:

### 1. Service Health Overview
- Request rate per endpoint
- Error rate per endpoint
- Latency percentiles (p50, p95, p99)
- CPU and memory usage

### 2. Search Performance
- Search request rate
- Search latency (p50, p95, p99)
- Search error rate
- Zero-result rate
- Cache hit rate for searches

### 3. Recommendation Performance
- Recommendation request rate
- Recommendation latency (p50, p95, p99)
- Recommendation error rate
- Cache hit rate for recommendations

### 4. Database Health
- Connection pool usage (active, idle, total)
- Connection pool utilization percentage
- Available connections (alerts if < 2)
- Query latency (p95)

### 5. Cache Performance
- Cache hit rate by type (search, recommendation, features)
- Cache hit/miss rates over time

## Starting the Monitoring Stack

The monitoring stack is included in `docker-compose.yml`. To start:

```bash
docker-compose up -d prometheus alertmanager grafana
```

Or start everything:

```bash
docker-compose up -d
```

## Accessing Dashboards

1. **Grafana**: http://localhost:3000
   - Login with `admin`/`admin`
   - Dashboards are automatically available in the dashboard list

2. **Prometheus**: http://localhost:9090
   - Use PromQL queries to explore metrics
   - Check targets at: http://localhost:9090/targets
   - View alert rules at: http://localhost:9090/alerts
   - Check alert status at: http://localhost:9090/alerts

3. **Alertmanager**: http://localhost:9093
   - View active alerts
   - View alert history
   - Silence alerts
   - Test notification channels

## Testing

Run the test script to verify everything is working:

```bash
# From project root
python backend/scripts/test_grafana_dashboards.py
```

The test script verifies:
- Backend metrics endpoint is accessible
- Prometheus can scrape metrics
- Grafana can connect to Prometheus
- All dashboards are loaded
- Dashboard queries return data

## Metrics Available

### RED Metrics (Rate, Errors, Duration)
- `http_requests_total{method, endpoint, status}` - Total HTTP requests
- `http_errors_total{method, endpoint, status_code}` - Total HTTP errors
- `http_request_duration_seconds{method, endpoint}` - Request latency histogram

### Business Metrics
- `search_zero_results_total{query_pattern}` - Zero-result searches
- `cache_hits_total{cache_type}` - Cache hits
- `cache_misses_total{cache_type}` - Cache misses
- `ranking_score_distribution{product_id}` - Ranking score distribution

### Resource Metrics
- `system_cpu_usage_percent` - CPU usage percentage
- `system_memory_usage_bytes` - Memory usage in bytes
- `db_connection_pool_size{state}` - Database connection pool (active/idle/total)

## Troubleshooting

### Prometheus not scraping metrics
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify backend is running: `curl http://localhost:8000/metrics`
3. Check Prometheus logs: `docker logs beamai-prometheus`

### Grafana dashboards show "No data"
1. Verify Prometheus datasource is configured: Grafana → Configuration → Data Sources
2. Test Prometheus connection in Grafana
3. Check that metrics are being generated (run test script)
4. Verify time range in dashboard (try "Last 1 hour")

### Dashboards not appearing
1. Check Grafana logs: `docker logs beamai-grafana`
2. Verify dashboard files are in `monitoring/grafana/dashboards/`
3. Check provisioning configuration: `monitoring/grafana/provisioning/dashboards/dashboards.yml`

## Customization

### Adding New Dashboards
1. Create dashboard JSON file in `monitoring/grafana/dashboards/`
2. Dashboard will be automatically loaded on Grafana startup
3. Use Grafana UI to create/edit dashboards, then export JSON

### Modifying Prometheus Configuration
Edit `monitoring/prometheus/prometheus.yml` and restart Prometheus:

```bash
docker-compose restart prometheus
```

### Changing Grafana Credentials
Update `docker-compose.yml` environment variables:
- `GF_SECURITY_ADMIN_USER`
- `GF_SECURITY_ADMIN_PASSWORD`

## Alerting Rules

The system includes 5 production-grade alert rules (Phase 1.4 - ✅ **COMPLETE**):

### Critical Alerts (Page On-Call)

1. **p99_latency_high**
   - Condition: p99 latency > 500ms for 5 minutes
   - Severity: Critical
   - Action: Page on-call engineer
   - Runbook: `docs/runbooks/p99_latency_high.md`

2. **error_rate_high**
   - Condition: Error rate > 1% for 2 minutes
   - Severity: Critical
   - Action: Page on-call engineer
   - Runbook: `docs/runbooks/error_rate_high.md`

3. **db_pool_exhausted**
   - Condition: Available connections < 2 for 2 minutes
   - Severity: Critical
   - Action: Page on-call engineer
   - Runbook: `docs/runbooks/db_pool_exhausted.md`

### Warning Alerts (Slack Notification)

4. **zero_result_rate_high**
   - Condition: Zero-result rate > 10% for 10 minutes
   - Severity: Warning
   - Action: Slack alert to #alerts channel
   - Runbook: `docs/runbooks/zero_result_rate_high.md`

5. **cache_hit_rate_low**
   - Condition: Cache hit rate < 50% for 10 minutes
   - Severity: Warning
   - Action: Slack alert to #alerts channel
   - Runbook: `docs/runbooks/cache_hit_rate_low.md`

**View Alert Rules:**
- Alert rules are defined in `monitoring/prometheus/alerts.yml`
- View active alerts in Alertmanager: http://localhost:9093
- View alert rules in Prometheus: http://localhost:9090/alerts

**Testing Alerts:**
- Unit tests: `backend/tests/test_alerting_rules.py`
- Integration tests: `backend/tests/test_alerting_integration.py`
- Run tests: `pytest backend/tests/test_alerting*.py -v`

**Configuring Notification Channels:**
Edit `monitoring/alertmanager/alertmanager.yml` to configure:
- Slack webhook URL (uncomment and add your webhook)
- PagerDuty integration key (uncomment and add your key)
- Email SMTP settings (uncomment and configure)

## Production Considerations

For production deployments:
1. Change default Grafana credentials
2. Enable authentication for Prometheus (if exposed)
3. Configure notification channels in Alertmanager (Slack, PagerDuty, Email)
4. Set up persistent storage for Prometheus and Alertmanager data
5. Review and adjust alert thresholds based on production SLOs
6. Set up alert escalation policies
7. Consider using Grafana Cloud or managed Prometheus services
8. Implement proper backup strategies for dashboard and alert configurations

