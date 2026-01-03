# How to Run and Test

This document provides step-by-step instructions for running and testing the BeamAI search and recommendation system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Running the System](#running-the-system)
4. [Testing the System](#testing-the-system)
5. [Troubleshooting](#troubleshooting)

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
```

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

This starts all services (PostgreSQL, Redis, Backend, Frontend) in containers.

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
```

**Run with coverage:**
```bash
pytest tests/ --cov=app --cov-report=html
```

### 6. Test Feature Computation

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

### 7. Test Frontend

1. Open http://localhost:5173 in your browser
2. Navigate to the Search page
3. Enter a search query (e.g., "shoes")
4. Verify results are displayed with scores
5. Navigate to the Recommendations page
6. Verify recommendations are displayed

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
- Request/response logs
- Error messages
- Performance metrics

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
curl "http://localhost:8000/search?q=test&k=5"

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

---

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Test search**: Try different queries and verify results
3. **Track events**: Simulate user interactions
4. **Monitor features**: Recompute features and see how scores change
5. **Read architecture docs**: Understand system design in `specs/`

For more details, see the main [README.md](../README.md) file.

