# Quick Start Guide - Grafana Dashboards

## Prerequisites

- Docker and Docker Compose installed
- Backend service running and exposing metrics at `/metrics`

## Start Monitoring Stack

```bash
# Start Prometheus and Grafana
docker-compose up -d prometheus grafana

# Or start everything including backend
docker-compose up -d
```

## Access Dashboards

1. **Open Grafana**: http://localhost:3000
   - Username: `admin`
   - Password: `admin`

2. **View Dashboards**: Click "Dashboards" → "Browse" in the left menu

3. **Available Dashboards**:
   - Service Health Overview
   - Search Performance
   - Recommendation Performance
   - Database Health
   - Cache Performance

## Verify Setup

Run the test script:

```bash
python backend/scripts/test_grafana_dashboards.py
```

Expected output:
```
✓ Backend metrics endpoint accessible
✓ Prometheus is accessible and responding to queries
✓ Prometheus has healthy backend target(s)
✓ Grafana has Prometheus datasource configured
✓ All 5 expected dashboards found
✓ All dashboard queries successful
```

## Generate Test Data

To see data in dashboards, make some API calls:

```bash
# Search requests
curl "http://localhost:8000/search?q=running+shoes"

# Recommendation requests
curl "http://localhost:8000/recommend/user123"

# Health check
curl "http://localhost:8000/health"
```

Wait 15-30 seconds for Prometheus to scrape metrics, then refresh Grafana dashboards.

## Troubleshooting

**No data in dashboards?**
1. Check Prometheus targets: http://localhost:9090/targets
2. Verify backend metrics: `curl http://localhost:8000/metrics`
3. Check time range in dashboard (try "Last 1 hour")

**Dashboards not showing?**
1. Check Grafana logs: `docker logs beamai-grafana`
2. Verify dashboard files exist: `ls monitoring/grafana/dashboards/`

**Prometheus not scraping?**
1. Check Prometheus logs: `docker logs beamai-prometheus`
2. Verify backend is accessible from Prometheus container
3. Check Prometheus config: `cat monitoring/prometheus/prometheus.yml`

