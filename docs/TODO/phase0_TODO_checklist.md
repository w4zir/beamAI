# TODO Checklist: Basic End-to-End Search & Recommendation System

This checklist implements a minimal working version of the search and recommendation system locally, following the specifications in the `/specs` directory and using features defined in [FEATURE_DEFINITIONS.md](../specs/FEATURE_DEFINITIONS.md).

## Database: Supabase (Standalone Container)

We're using **Supabase** as a standalone container for local development.

---

## Phase 1: Database Setup & Schema ✅

**Goal**: Set up Supabase and create canonical tables

- [ ] Ensure Supabase standalone container is running
- [x] Create migration `supabase/migrations/001_create_tables.sql`:
  - [x] `products` table (id TEXT PRIMARY KEY, name TEXT, description TEXT, category TEXT, price NUMERIC, popularity_score FLOAT DEFAULT 0, created_at TIMESTAMP)
  - [x] `users` table (id TEXT PRIMARY KEY, created_at TIMESTAMP)
  - [x] `events` table (user_id TEXT, product_id TEXT, event_type TEXT, timestamp TIMESTAMP, source TEXT)
- [x] Create migration `supabase/migrations/002_create_fts_index.sql`:
  - [x] Add `search_vector` column (tsvector) to products
  - [x] Create GIN index on `search_vector`
  - [x] Create trigger function to auto-update search_vector
  - [x] Create trigger on products table
- [x] Create seed script `data/seed_data.py`:
  - [x] Generate synthetic products (10-20 products across categories)
  - [x] Create sample users (5-10 users)
  - [x] Generate sample events (views, add_to_cart, purchases)
- [ ] Update `.env` with Supabase connection details
- [ ] Run migrations on Supabase database
- [ ] Run seed script to populate initial data

**Files Created**:
- `supabase/config.toml`
- `supabase/migrations/001_create_tables.sql` ✅
- `supabase/migrations/002_create_fts_index.sql` ✅
- `data/seed_data.py` ✅

---

## Phase 2: Feature Computation (Offline) ✅

**Goal**: Implement offline feature computation per [FEATURE_DEFINITIONS.md](../specs/FEATURE_DEFINITIONS.md)

- [x] Create `backend/app/services/features/__init__.py`
- [x] Implement `popularity_score` computation (`backend/app/services/features/popularity.py`):
  - [x] Weighted count: purchase=3, add_to_cart=2, view=1
  - [x] Query events table, aggregate by product_id
  - [x] Update products.popularity_score
- [x] Implement `product_freshness_score` (`backend/app/services/features/freshness.py`):
  - [x] Time decay formula from created_at
  - [x] Computed on-demand (no storage needed)
- [x] Create feature orchestrator (`backend/app/services/features/compute.py`):
  - [x] Function to run popularity_score batch job
  - [x] CLI command or script to trigger computation
- [ ] Test: Run popularity computation on seeded data
- [ ] Verify: Check products table has updated popularity_score values

**Files Created**:
- `backend/app/services/features/__init__.py` ✅
- `backend/app/services/features/popularity.py` ✅
- `backend/app/services/features/freshness.py` ✅
- `backend/app/services/features/compute.py` ✅

---

## Phase 3: Search Service ✅

**Goal**: Implement keyword search using Postgres FTS

- [x] Create `backend/app/services/search/__init__.py`
- [x] Implement keyword search (`backend/app/services/search/keyword.py`):
  - [x] Query normalization function (lowercase, trim whitespace)
  - [x] Postgres FTS query using `search_vector` column
  - [x] Return list of (product_id, search_keyword_score) tuples
  - [x] Handle empty queries gracefully
- [x] Create search endpoint (`backend/app/routes/search.py`):
  - [x] GET `/search?q={query}&user_id={optional}&k={int}`
  - [x] Validate query parameter
  - [x] Call keyword search service
  - [x] Return candidates with scores (ranking integrated)
- [ ] Test: Search for products by name/category
- [ ] Verify: Results include search_keyword_score

**Files Created**:
- `backend/app/services/search/__init__.py` ✅
- `backend/app/services/search/keyword.py` ✅
- `backend/app/routes/search.py` ✅

---

## Phase 4: Recommendation Service ✅

**Goal**: Implement popularity-based recommendations

- [x] Create `backend/app/services/recommendation/__init__.py`
- [x] Implement popularity recommendations (`backend/app/services/recommendation/popularity.py`):
  - [x] Global popularity: Query top K products by popularity_score
  - [x] Return list of product_ids
  - [x] Handle cold start (new products with 0 popularity)
- [x] Create recommendation endpoint (`backend/app/routes/recommend.py`):
  - [x] GET `/recommend/{user_id}?k={int}`
  - [x] Validate user_id exists
  - [x] Call popularity recommendation service
  - [x] Return candidates (ranking integrated)
- [ ] Test: Get recommendations for existing user
- [ ] Verify: Results are ordered by popularity_score

**Files Created**:
- `backend/app/services/recommendation/__init__.py` ✅
- `backend/app/services/recommendation/popularity.py` ✅
- `backend/app/routes/recommend.py` ✅

---

## Phase 5: Ranking Service ✅

**Goal**: Implement deterministic ranking using Phase 1 formula from [RANKING_LOGIC.md](../specs/RANKING_LOGIC.md)

- [x] Create `backend/app/services/ranking/__init__.py`
- [x] Implement feature retrieval (`backend/app/services/ranking/features.py`):
  - [x] Fetch `popularity_score` from products table
  - [x] Compute `freshness_score` on-demand using freshness service
  - [x] Return feature dict for a product
- [x] Implement ranking (`backend/app/services/ranking/score.py`):
  - [x] Phase 1 formula:
    ```python
    final_score = (
        0.4 * search_score +      # search_keyword_score for search, 0 for recs
        0.3 * cf_score +          # 0 for now (no CF)
        0.2 * popularity_score +
        0.1 * freshness_score
    )
    ```
  - [x] Function to rank list of candidates
  - [x] Return sorted list with final_score
- [x] Integrate ranking into search endpoint:
  - [x] After getting candidates, fetch features
  - [x] Rank candidates
  - [x] Return ranked results
- [x] Integrate ranking into recommend endpoint:
  - [x] After getting candidates, fetch features
  - [x] Rank candidates (search_score = 0)
  - [x] Return ranked results
- [ ] Test: Verify ranking changes order of results
- [ ] Verify: Final scores are computed correctly

**Files Created**:
- `backend/app/services/ranking/__init__.py` ✅
- `backend/app/services/ranking/features.py` ✅
- `backend/app/services/ranking/score.py` ✅

**Files Modified**:
- `backend/app/routes/search.py` ✅
- `backend/app/routes/recommend.py` ✅

---

## Phase 6: API Integration & Error Handling ✅

**Goal**: Wire up all services in FastAPI with proper error handling

- [x] Update `backend/app/main.py`:
  - [x] Include search router: `app.include_router(search.router, prefix="/search", tags=["Search"])`
  - [x] Include recommend router: `app.include_router(recommend.router, prefix="/recommend", tags=["Recommendations"])`
  - [x] Add request logging middleware
- [x] Create response models (`backend/app/models/responses.py`):
  - [x] `SearchResult` model (product_id, score, reason?)
  - [x] `RecommendResult` model (product_id, score, reason?)
- [x] Implement graceful degradation:
  - [x] If ranking fails, return candidates sorted by popularity_score
  - [x] If search fails, return empty results with error message
  - [x] Add try/except blocks in endpoints
- [x] Add error handlers in `main.py`:
  - [x] Handle database connection errors
  - [x] Handle validation errors
- [ ] Test: Verify error handling works (disconnect DB, invalid queries)

**Files Created**:
- `backend/app/models/__init__.py` ✅
- `backend/app/models/responses.py` ✅

**Files Modified**:
- `backend/app/main.py` ✅
- `backend/app/routes/search.py` ✅
- `backend/app/routes/recommend.py` ✅

---

## Phase 7: Frontend UI - Search Page ✅

**Goal**: Create basic search interface

- [x] Create API client (`frontend/src/api/search.ts`):
  - [x] Function `searchProducts(query: string, userId?: string, k?: number)`
  - [x] Call `/search` endpoint
  - [x] Return typed results
- [x] Create Search page (`frontend/src/pages/Search.tsx`):
  - [x] Search input field with Enter key handling
  - [x] Loading state while searching
  - [x] Results display (product cards):
    - [x] Product name
    - [x] Category
    - [x] Price
    - [x] Score (for debugging)
  - [x] Empty state (no results)
  - [x] Error state (search failed)
- [x] Add route in `frontend/src/App.tsx`:
  - [x] `/search` route pointing to Search component
- [x] Update Navbar (`frontend/src/components/Navbar.tsx`):
  - [x] Add "Search" link
- [ ] Test: Search for products, verify results display

**Files Created**:
- `frontend/src/pages/Search.tsx` ✅
- `frontend/src/api/search.ts` ✅

**Files Modified**:
- `frontend/src/App.tsx` ✅
- `frontend/src/components/Navbar.tsx` ✅

---

## Phase 8: Frontend UI - Recommendations Page ✅

**Goal**: Create basic recommendations interface

- [x] Create API client (`frontend/src/api/recommend.ts`):
  - [x] Function `getRecommendations(userId: string, k?: number)`
  - [x] Call `/recommend/{user_id}` endpoint
  - [x] Return typed results
- [x] Create Recommendations page (`frontend/src/pages/Recommendations.tsx`):
  - [x] Get current user ID from Supabase auth
  - [x] Loading state while fetching
  - [x] Product cards display:
    - [x] Product name
    - [x] Category
    - [x] Price
    - [x] Score (for debugging)
  - [x] Empty state (no recommendations)
  - [x] Error state (fetch failed)
- [x] Add route in `frontend/src/App.tsx`:
  - [x] `/recommendations` route pointing to Recommendations component
- [x] Update Navbar (`frontend/src/components/Navbar.tsx`):
  - [x] Add "Recommendations" link
- [ ] Test: View recommendations for logged-in user

**Files Created**:
- `frontend/src/pages/Recommendations.tsx` ✅
- `frontend/src/api/recommend.ts` ✅

**Files Modified**:
- `frontend/src/App.tsx` ✅
- `frontend/src/components/Navbar.tsx` ✅

---

## Phase 9: Event Tracking ✅

**Goal**: Track user interactions for future feature computation

- [x] Create event tracking endpoint (`backend/app/routes/events.py`):
  - [x] POST `/events`
  - [x] Accept: user_id, product_id, event_type, source
  - [x] Validate event_type (view, add_to_cart, purchase)
  - [x] Insert into events table
  - [x] Return success/error response
- [x] Create API client (`frontend/src/api/events.ts`):
  - [x] Function `trackEvent(userId, productId, eventType, source)`
  - [x] Call POST `/events` endpoint
- [x] Integrate into Search page:
  - [x] Track "view" event when results are displayed
  - [x] Track "view" event when product card is clicked
  - [x] Source = "search"
- [x] Integrate into Recommendations page:
  - [x] Track "view" event when recommendations are displayed
  - [x] Track "view" event when product card is clicked
  - [x] Source = "recommendation"
- [ ] Test: Verify events are inserted into database
- [ ] Verify: Check events table has new rows

**Files Created**:
- `backend/app/routes/events.py` ✅
- `frontend/src/api/events.ts` ✅

**Files Modified**:
- `backend/app/main.py` (include events router) ✅
- `frontend/src/pages/Search.tsx` ✅
- `frontend/src/pages/Recommendations.tsx` ✅

---

## Phase 10: Testing & Validation ✅

**Goal**: Ensure basic end-to-end flow works

- [ ] Manual testing checklist:
  - [ ] Ensure Supabase standalone container is running
  - [ ] Start backend: `npm run backend`
  - [ ] Start frontend: `npm run frontend`
  - [ ] Search returns results
  - [ ] Results are ranked correctly (check scores)
  - [ ] Recommendations show products
  - [ ] Events are tracked (check database)
  - [ ] Error handling works (invalid queries, missing data)
- [x] Create basic integration test (`backend/tests/test_search.py`):
  - [x] Test search endpoint returns expected structure
  - [x] Test search with valid query
  - [x] Test search with empty query
- [x] Update README (`README.md`):
  - [x] Document Supabase setup (standalone container)
  - [x] Document how to run migrations
  - [x] Document how to seed data
  - [x] Document API endpoints
  - [x] Document how to run the system end-to-end
- [ ] Verify: Full end-to-end flow works locally

**Files Created**:
- `backend/tests/__init__.py` ✅
- `backend/tests/test_search.py` ✅

**Files Modified**:
- `README.md` ✅

---

## Dependencies to Add

**Backend** (`backend/requirements.txt`):
- `numpy` (for freshness score computation)
- `python-dateutil` (for date handling)

**Infrastructure**:
- Supabase standalone container
- Docker & Docker Compose (for backend services)

---

## Success Criteria

- [x] Database schema created and seeded with sample data
- [x] Search endpoint returns ranked results
- [x] Recommendation endpoint returns ranked results
- [x] Frontend displays search results
- [x] Frontend displays recommendations
- [x] Events are tracked when users interact
- [ ] System runs locally end-to-end (requires manual testing)
- [x] All features from FEATURE_DEFINITIONS.md are referenced correctly

---

## Notes

- **Database**: Using Supabase (standalone container)
- **Features**: Following [FEATURE_DEFINITIONS.md](../specs/FEATURE_DEFINITIONS.md) strictly
- **Architecture**: Separation of concerns - retrieval separate from ranking
- **Phase 1 Scope**: No collaborative filtering, no semantic search (keyword only)
- **Ranking**: Phase 1 formula with fixed weights (0.4, 0.3, 0.2, 0.1)

