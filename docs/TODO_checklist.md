# TODO Checklist: Basic End-to-End Search & Recommendation System

This checklist implements a minimal working version of the search and recommendation system locally, following the specifications in the `/specs` directory and using features defined in [FEATURE_DEFINITIONS.md](../specs/FEATURE_DEFINITIONS.md).

## Database: Supabase Local (Docker Compose)

We're using **Supabase Local** for local development, which runs Postgres in Docker via Supabase CLI.

---

## Phase 1: Database Setup & Schema ✅

**Goal**: Set up Supabase Local and create canonical tables

- [ ] Install Supabase CLI (if not installed)
- [ ] Initialize Supabase project: `supabase init`
- [ ] Start Supabase Local: `supabase start`
- [ ] Create migration `supabase/migrations/001_create_tables.sql`:
  - [ ] `products` table (id TEXT PRIMARY KEY, name TEXT, description TEXT, category TEXT, price NUMERIC, popularity_score FLOAT DEFAULT 0, created_at TIMESTAMP)
  - [ ] `users` table (id TEXT PRIMARY KEY, created_at TIMESTAMP)
  - [ ] `events` table (user_id TEXT, product_id TEXT, event_type TEXT, timestamp TIMESTAMP, source TEXT)
- [ ] Create migration `supabase/migrations/002_create_fts_index.sql`:
  - [ ] Add `search_vector` column (tsvector) to products
  - [ ] Create GIN index on `search_vector`
  - [ ] Create trigger function to auto-update search_vector
  - [ ] Create trigger on products table
- [ ] Create seed script `backend/scripts/seed_data.py`:
  - [ ] Generate synthetic products (10-20 products across categories)
  - [ ] Create sample users (5-10 users)
  - [ ] Generate sample events (views, add_to_cart, purchases)
- [ ] Update `.env` with local Supabase connection details
- [ ] Run migrations: `supabase db reset` or `supabase migration up`
- [ ] Run seed script to populate initial data

**Files Created**:
- `supabase/config.toml`
- `supabase/migrations/001_create_tables.sql`
- `supabase/migrations/002_create_fts_index.sql`
- `backend/scripts/seed_data.py`

---

## Phase 2: Feature Computation (Offline) ✅

**Goal**: Implement offline feature computation per [FEATURE_DEFINITIONS.md](../specs/FEATURE_DEFINITIONS.md)

- [ ] Create `backend/app/services/features/__init__.py`
- [ ] Implement `popularity_score` computation (`backend/app/services/features/popularity.py`):
  - [ ] Weighted count: purchase=3, add_to_cart=2, view=1
  - [ ] Query events table, aggregate by product_id
  - [ ] Update products.popularity_score
- [ ] Implement `product_freshness_score` (`backend/app/services/features/freshness.py`):
  - [ ] Time decay formula from created_at
  - [ ] Computed on-demand (no storage needed)
- [ ] Create feature orchestrator (`backend/app/services/features/compute.py`):
  - [ ] Function to run popularity_score batch job
  - [ ] CLI command or script to trigger computation
- [ ] Test: Run popularity computation on seeded data
- [ ] Verify: Check products table has updated popularity_score values

**Files Created**:
- `backend/app/services/features/__init__.py`
- `backend/app/services/features/popularity.py`
- `backend/app/services/features/freshness.py`
- `backend/app/services/features/compute.py`

---

## Phase 3: Search Service ✅

**Goal**: Implement keyword search using Postgres FTS

- [ ] Create `backend/app/services/search/__init__.py`
- [ ] Implement keyword search (`backend/app/services/search/keyword.py`):
  - [ ] Query normalization function (lowercase, trim whitespace)
  - [ ] Postgres FTS query using `search_vector` column
  - [ ] Return list of (product_id, search_keyword_score) tuples
  - [ ] Handle empty queries gracefully
- [ ] Create search endpoint (`backend/app/routes/search.py`):
  - [ ] GET `/search?q={query}&user_id={optional}&k={int}`
  - [ ] Validate query parameter
  - [ ] Call keyword search service
  - [ ] Return candidates with scores (no ranking yet)
- [ ] Test: Search for products by name/category
- [ ] Verify: Results include search_keyword_score

**Files Created**:
- `backend/app/services/search/__init__.py`
- `backend/app/services/search/keyword.py`
- `backend/app/routes/search.py`

---

## Phase 4: Recommendation Service ✅

**Goal**: Implement popularity-based recommendations

- [ ] Create `backend/app/services/recommendation/__init__.py`
- [ ] Implement popularity recommendations (`backend/app/services/recommendation/popularity.py`):
  - [ ] Global popularity: Query top K products by popularity_score
  - [ ] Return list of product_ids
  - [ ] Handle cold start (new products with 0 popularity)
- [ ] Create recommendation endpoint (`backend/app/routes/recommend.py`):
  - [ ] GET `/recommend/{user_id}?k={int}`
  - [ ] Validate user_id exists
  - [ ] Call popularity recommendation service
  - [ ] Return candidates (no ranking yet)
- [ ] Test: Get recommendations for existing user
- [ ] Verify: Results are ordered by popularity_score

**Files Created**:
- `backend/app/services/recommendation/__init__.py`
- `backend/app/services/recommendation/popularity.py`
- `backend/app/routes/recommend.py`

---

## Phase 5: Ranking Service ✅

**Goal**: Implement deterministic ranking using Phase 1 formula from [RANKING_LOGIC.md](../specs/RANKING_LOGIC.md)

- [ ] Create `backend/app/services/ranking/__init__.py`
- [ ] Implement feature retrieval (`backend/app/services/ranking/features.py`):
  - [ ] Fetch `popularity_score` from products table
  - [ ] Compute `freshness_score` on-demand using freshness service
  - [ ] Return feature dict for a product
- [ ] Implement ranking (`backend/app/services/ranking/score.py`):
  - [ ] Phase 1 formula:
    ```python
    final_score = (
        0.4 * search_score +      # search_keyword_score for search, 0 for recs
        0.3 * cf_score +          # 0 for now (no CF)
        0.2 * popularity_score +
        0.1 * freshness_score
    )
    ```
  - [ ] Function to rank list of candidates
  - [ ] Return sorted list with final_score
- [ ] Integrate ranking into search endpoint:
  - [ ] After getting candidates, fetch features
  - [ ] Rank candidates
  - [ ] Return ranked results
- [ ] Integrate ranking into recommend endpoint:
  - [ ] After getting candidates, fetch features
  - [ ] Rank candidates (search_score = 0)
  - [ ] Return ranked results
- [ ] Test: Verify ranking changes order of results
- [ ] Verify: Final scores are computed correctly

**Files Created**:
- `backend/app/services/ranking/__init__.py`
- `backend/app/services/ranking/features.py`
- `backend/app/services/ranking/score.py`

**Files Modified**:
- `backend/app/routes/search.py`
- `backend/app/routes/recommend.py`

---

## Phase 6: API Integration & Error Handling ✅

**Goal**: Wire up all services in FastAPI with proper error handling

- [ ] Update `backend/app/main.py`:
  - [ ] Include search router: `app.include_router(search.router, prefix="/search", tags=["Search"])`
  - [ ] Include recommend router: `app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])`
  - [ ] Add request logging middleware
- [ ] Create response models (`backend/app/models/responses.py`):
  - [ ] `SearchResult` model (product_id, score, reason?)
  - [ ] `RecommendResult` model (product_id, score, reason?)
- [ ] Implement graceful degradation:
  - [ ] If ranking fails, return candidates sorted by popularity_score
  - [ ] If search fails, return empty results with error message
  - [ ] Add try/except blocks in endpoints
- [ ] Add error handlers in `main.py`:
  - [ ] Handle database connection errors
  - [ ] Handle validation errors
- [ ] Test: Verify error handling works (disconnect DB, invalid queries)

**Files Created**:
- `backend/app/models/__init__.py`
- `backend/app/models/responses.py`

**Files Modified**:
- `backend/app/main.py`
- `backend/app/routes/search.py`
- `backend/app/routes/recommend.py`

---

## Phase 7: Frontend UI - Search Page ✅

**Goal**: Create basic search interface

- [ ] Create API client (`frontend/src/api/search.ts`):
  - [ ] Function `searchProducts(query: string, userId?: string, k?: number)`
  - [ ] Call `/search` endpoint
  - [ ] Return typed results
- [ ] Create Search page (`frontend/src/pages/Search.tsx`):
  - [ ] Search input field with debounce
  - [ ] Loading state while searching
  - [ ] Results display (product cards):
    - [ ] Product name
    - [ ] Category
    - [ ] Price
    - [ ] Score (for debugging)
  - [ ] Empty state (no results)
  - [ ] Error state (search failed)
- [ ] Add route in `frontend/src/App.tsx`:
  - [ ] `/search` route pointing to Search component
- [ ] Update Navbar (`frontend/src/components/Navbar.tsx`):
  - [ ] Add "Search" link
- [ ] Test: Search for products, verify results display

**Files Created**:
- `frontend/src/pages/Search.tsx`
- `frontend/src/api/search.ts`

**Files Modified**:
- `frontend/src/App.tsx`
- `frontend/src/components/Navbar.tsx`

---

## Phase 8: Frontend UI - Recommendations Page ✅

**Goal**: Create basic recommendations interface

- [ ] Create API client (`frontend/src/api/recommend.ts`):
  - [ ] Function `getRecommendations(userId: string, k?: number)`
  - [ ] Call `/recommend/{user_id}` endpoint
  - [ ] Return typed results
- [ ] Create Recommendations page (`frontend/src/pages/Recommendations.tsx`):
  - [ ] Get current user ID from Supabase auth
  - [ ] Loading state while fetching
  - [ ] Product cards display:
    - [ ] Product name
    - [ ] Category
    - [ ] Price
    - [ ] Score (for debugging)
  - [ ] Empty state (no recommendations)
  - [ ] Error state (fetch failed)
- [ ] Add route in `frontend/src/App.tsx`:
  - [ ] `/recommendations` route pointing to Recommendations component
- [ ] Update Navbar (`frontend/src/components/Navbar.tsx`):
  - [ ] Add "Recommendations" link
- [ ] Test: View recommendations for logged-in user

**Files Created**:
- `frontend/src/pages/Recommendations.tsx`
- `frontend/src/api/recommend.ts`

**Files Modified**:
- `frontend/src/App.tsx`
- `frontend/src/components/Navbar.tsx`

---

## Phase 9: Event Tracking ✅

**Goal**: Track user interactions for future feature computation

- [ ] Create event tracking endpoint (`backend/app/routes/events.py`):
  - [ ] POST `/events`
  - [ ] Accept: user_id, product_id, event_type, source
  - [ ] Validate event_type (view, add_to_cart, purchase)
  - [ ] Insert into events table
  - [ ] Return success/error response
- [ ] Create API client (`frontend/src/api/events.ts`):
  - [ ] Function `trackEvent(userId, productId, eventType, source)`
  - [ ] Call POST `/events` endpoint
- [ ] Integrate into Search page:
  - [ ] Track "view" event when results are displayed
  - [ ] Track "view" event when product card is clicked
  - [ ] Source = "search"
- [ ] Integrate into Recommendations page:
  - [ ] Track "view" event when recommendations are displayed
  - [ ] Track "view" event when product card is clicked
  - [ ] Source = "recommendation"
- [ ] Test: Verify events are inserted into database
- [ ] Verify: Check events table has new rows

**Files Created**:
- `backend/app/routes/events.py`
- `frontend/src/api/events.ts`

**Files Modified**:
- `backend/app/main.py` (include events router)
- `frontend/src/pages/Search.tsx`
- `frontend/src/pages/Recommendations.tsx`

---

## Phase 10: Testing & Validation ✅

**Goal**: Ensure basic end-to-end flow works

- [ ] Manual testing checklist:
  - [ ] Start Supabase Local: `supabase start`
  - [ ] Start backend: `npm run backend`
  - [ ] Start frontend: `npm run frontend`
  - [ ] Search returns results
  - [ ] Results are ranked correctly (check scores)
  - [ ] Recommendations show products
  - [ ] Events are tracked (check database)
  - [ ] Error handling works (invalid queries, missing data)
- [ ] Create basic integration test (`backend/tests/test_search.py`):
  - [ ] Test search endpoint returns expected structure
  - [ ] Test search with valid query
  - [ ] Test search with empty query
- [ ] Update README (`README.md`):
  - [ ] Document Supabase Local setup steps
  - [ ] Document how to run migrations
  - [ ] Document how to seed data
  - [ ] Document API endpoints
  - [ ] Document how to run the system end-to-end
- [ ] Verify: Full end-to-end flow works locally

**Files Created**:
- `backend/tests/__init__.py`
- `backend/tests/test_search.py`

**Files Modified**:
- `README.md`

---

## Dependencies to Add

**Backend** (`backend/requirements.txt`):
- `numpy` (for freshness score computation)
- `python-dateutil` (for date handling)

**Infrastructure**:
- Supabase CLI (install via npm: `npm install -g supabase` or via package manager)
- Docker & Docker Compose (for Supabase Local)

---

## Success Criteria

- [ ] Database schema created and seeded with sample data
- [ ] Search endpoint returns ranked results
- [ ] Recommendation endpoint returns ranked results
- [ ] Frontend displays search results
- [ ] Frontend displays recommendations
- [ ] Events are tracked when users interact
- [ ] System runs locally end-to-end
- [ ] All features from FEATURE_DEFINITIONS.md are referenced correctly

---

## Notes

- **Database**: Using Supabase Local (Postgres in Docker)
- **Features**: Following [FEATURE_DEFINITIONS.md](../specs/FEATURE_DEFINITIONS.md) strictly
- **Architecture**: Separation of concerns - retrieval separate from ranking
- **Phase 1 Scope**: No collaborative filtering, no semantic search (keyword only)
- **Ranking**: Phase 1 formula with fixed weights (0.4, 0.3, 0.2, 0.1)

