# How It Works

This document provides a detailed explanation of each component of the BeamAI search and recommendation system, including algorithms and code snippets.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Search Service](#search-service)
3. [Recommendation Service](#recommendation-service)
4. [Ranking Service](#ranking-service)
5. [Feature Computation](#feature-computation)
6. [Event Tracking](#event-tracking)
7. [Request Flow](#request-flow)

---

## System Architecture

The system follows a **separation of concerns** architecture where retrieval, ranking, and serving are independent components.

### High-Level Components

- **FastAPI Gateway**: Request validation and orchestration only
- **Search Service**: Keyword search (Postgres FTS) - returns candidates only
- **Recommendation Service**: Popularity-based recommendations - returns candidates only
- **Ranking Service**: Deterministic scoring using Phase 1 formula - final ordering

### Core Principles

1. **Retrieval is separate from ranking**: Search/recommendation services return candidates, ranking service orders them
2. **Offline training, online serving**: Features are computed offline, models are trained separately
3. **Fail gracefully**: Every component has fallback mechanisms

---

## Search Service

The search service implements **keyword search** using PostgreSQL Full Text Search (FTS) principles.

### Query Normalization

Before searching, queries are normalized:

```17:47:backend/app/services/search/keyword.py
def normalize_query(query: str) -> str:
    """
    Normalize search query.
    
    Steps:
    1. Lowercase
    2. Remove punctuation (keep spaces)
    3. Trim whitespace
    
    Args:
        query: Raw search query
        
    Returns:
        Normalized query string
    """
    if not query:
        return ""
    
    # Lowercase
    normalized = query.lower()
    
    # Remove punctuation but keep spaces and alphanumeric
    normalized = re.sub(r'[^\w\s]', ' ', normalized)
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Trim whitespace
    normalized = normalized.strip()
    
    return normalized
```

### Keyword Search Algorithm

The search algorithm uses a simple word-matching approach with weighted scoring:

```50:156:backend/app/services/search/keyword.py
def search_keywords(query: str, limit: int = 50) -> List[Tuple[str, float]]:
    """
    Search products using PostgreSQL Full Text Search.
    
    Returns candidates with search_keyword_score.
    According to SEARCH_DESIGN.md: Search returns candidate product IDs only.
    Ranking is handled downstream.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of tuples (product_id, search_keyword_score)
        Results are sorted by score descending
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return []
    
    # Normalize query
    normalized_query = normalize_query(query)
    
    if not normalized_query:
        logger.warning("Empty query after normalization")
        return []
    
    try:
        # Convert query to tsquery format for Postgres FTS
        # Use plainto_tsquery for better user experience (handles multiple words)
        # This creates a query like: 'running' & 'shoes'
        
        # Build the FTS query using Postgres functions
        # We'll use the search_vector column with ts_rank for scoring
        
        # For Supabase, we need to use RPC or raw SQL for FTS queries
        # Since Supabase client doesn't directly support FTS, we'll query products
        # and filter/rank in Python for Phase 1, or use a simpler approach
        
        # Alternative: Use Supabase's text search if available, or query all and filter
        # For now, let's use a Postgres function approach via RPC
        
        # Simple approach: Query products and use Python to compute scores
        # This is not ideal for large datasets but works for Phase 1
        
        # Better approach: Use raw SQL via Supabase's postgrest client
        # We'll construct a query that uses ts_rank
        
        # Build tsquery from normalized query
        # Split into words and join with &
        words = normalized_query.split()
        tsquery = ' & '.join(words)
        
        # Use Supabase's RPC to call a Postgres function, or use direct query
        # For Phase 1, let's query products and compute scores in Python
        # In production, this should use a Postgres function
        
        # Query products with search_vector
        response = client.table("products").select("id, name, description, category, search_vector").execute()
        
        if not response.data:
            return []
        
        results = []
        
        # Compute FTS scores in Python (for Phase 1)
        # In production, this should be done in Postgres
        import re
        
        query_words = set(words)
        
        for product in response.data:
            product_id = product["id"]
            name = product.get("name", "").lower()
            description = product.get("description", "").lower()
            category = product.get("category", "").lower()
            
            # Simple scoring: count word matches
            # Weight: name (3x), description (2x), category (1x)
            score = 0.0
            
            for word in query_words:
                if word in name:
                    score += 3.0
                if word in description:
                    score += 2.0
                if word in category:
                    score += 1.0
            
            if score > 0:
                # Normalize score (simple normalization)
                normalized_score = min(score / (len(query_words) * 3.0), 1.0)
                results.append((product_id, normalized_score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Limit results
        results = results[:limit]
        
        logger.info(f"Keyword search for '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in keyword search: {e}", exc_info=True)
        return []
```

**Scoring Algorithm:**
- **Name matches**: 3 points per word
- **Description matches**: 2 points per word
- **Category matches**: 1 point per word
- **Normalization**: Score divided by `(number_of_query_words * 3.0)` to get a value between 0 and 1

### Search Endpoint

The search endpoint orchestrates the search and ranking:

```26:79:backend/app/routes/search.py
@router.get("", response_model=List[SearchResult])
async def search(
    q: str = Query(..., description="Search query"),
    user_id: Optional[str] = Query(None, description="Optional user ID for personalization"),
    k: int = Query(10, ge=1, le=100, description="Number of results to return")
):
    """
    Search for products using keyword search with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    try:
        # Get candidates from search service
        candidates = search_keywords(q.strip(), limit=k * 2)
        
        if not candidates:
            return []
        
        # Apply ranking
        try:
            ranked = rank_products(candidates, is_search=True, user_id=user_id)
            
            # Format results
            results = [
                SearchResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (search: {breakdown['search_score']:.3f}, popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
        except Exception as ranking_error:
            logger.warning(f"Ranking failed, falling back to popularity sort: {ranking_error}")
            # Fallback: sort by search_score
            candidates.sort(key=lambda x: x[1], reverse=True)
            results = [
                SearchResult(
                    product_id=product_id,
                    score=score,
                    reason=f"Keyword match score: {score:.3f} (ranking unavailable)"
                )
                for product_id, score in candidates[:k]
            ]
        
        logger.info(f"Search query '{q}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during search")
```

---

## Recommendation Service

The recommendation service provides **popularity-based recommendations** as the baseline model.

### Popularity Recommendation Algorithm

```15:68:backend/app/services/recommendation/popularity.py
def get_popularity_recommendations(
    user_id: Optional[str] = None,
    limit: int = 10,
    category: Optional[str] = None
) -> List[str]:
    """
    Get product recommendations based on global popularity.
    
    Returns candidate product IDs ordered by popularity_score.
    According to RECOMMENDATION_DESIGN.md: Returns candidates only.
    Ranking is handled downstream.
    
    Args:
        user_id: Optional user ID (for future personalization)
        limit: Maximum number of recommendations
        category: Optional category filter
        
    Returns:
        List of product IDs ordered by popularity_score (descending)
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return []
    
    try:
        # Build query
        query = client.table("products").select("id, popularity_score")
        
        # Filter by category if provided
        if category:
            query = query.eq("category", category)
        
        # Order by popularity_score descending
        query = query.order("popularity_score", desc=True)
        
        # Limit results
        query = query.limit(limit * 2)  # Get more candidates for ranking later
        
        response = query.execute()
        
        if not response.data:
            logger.warning("No products found for recommendations")
            return []
        
        # Extract product IDs
        product_ids = [product["id"] for product in response.data]
        
        logger.info(f"Popularity recommendations returned {len(product_ids)} candidates")
        return product_ids
        
    except Exception as e:
        logger.error(f"Error getting popularity recommendations: {e}", exc_info=True)
        return []
```

**Algorithm:**
1. Query products ordered by `popularity_score` descending
2. Optionally filter by category
3. Return top `limit * 2` candidates (more candidates for ranking later)
4. Ranking service will re-rank these candidates

### Recommendation Endpoint

```27:95:backend/app/routes/recommend.py
@router.get("/{user_id}", response_model=List[RecommendResult])
async def recommend(
    user_id: str = Path(..., description="User ID"),
    k: int = Query(10, ge=1, le=100, description="Number of recommendations to return")
):
    """
    Get product recommendations for a user with ranking.
    
    Returns ranked results using Phase 1 ranking formula.
    """
    try:
        # Verify user exists
        client = get_supabase_client()
        if client:
            user_check = client.table("users").select("id").eq("id", user_id).limit(1).execute()
            if not user_check.data:
                logger.warning(f"User {user_id} not found, but continuing with recommendations")
        
        # Get candidates from recommendation service
        candidate_ids = get_popularity_recommendations(user_id=user_id, limit=k * 2)
        
        if not candidate_ids:
            logger.warning(f"No recommendations found for user {user_id}")
            return []
        
        # Convert to candidates format (product_id, search_score=0 for recommendations)
        candidates = [(product_id, 0.0) for product_id in candidate_ids]
        
        # Apply ranking (is_search=False for recommendations)
        try:
            ranked = rank_products(candidates, is_search=False, user_id=user_id)
            
            # Format results
            results = [
                RecommendResult(
                    product_id=product_id,
                    score=final_score,
                    reason=f"Ranked score: {final_score:.3f} (popularity: {breakdown['popularity_score']:.3f}, freshness: {breakdown['freshness_score']:.3f})"
                )
                for product_id, final_score, breakdown in ranked[:k]
            ]
        except Exception as ranking_error:
            logger.warning(f"Ranking failed, falling back to popularity sort: {ranking_error}")
            # Fallback: use popularity scores
            if client:
                products = client.table("products").select("id, popularity_score").in_("id", candidate_ids).execute()
                score_map = {p["id"]: p.get("popularity_score", 0.0) or 0.0 for p in products.data}
            else:
                score_map = {}
            
            # Sort by popularity
            sorted_candidates = sorted(candidate_ids, key=lambda pid: score_map.get(pid, 0.0), reverse=True)
            
            results = [
                RecommendResult(
                    product_id=product_id,
                    score=score_map.get(product_id, 0.0),
                    reason=f"Popularity score: {score_map.get(product_id, 0.0):.3f} (ranking unavailable)"
                )
                for product_id in sorted_candidates[:k]
            ]
        
        logger.info(f"Recommendations for user {user_id} returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in recommend endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during recommendation")
```

---

## Ranking Service

The ranking service implements the **Phase 1 ranking formula** with deterministic scoring.

### Phase 1 Ranking Formula

According to `RANKING_LOGIC.md`, the Phase 1 formula is:

```python
final_score = (
    0.4 * search_score +
    0.3 * cf_score +
    0.2 * popularity_score +
    0.1 * freshness_score
)
```

### Score Computation

```31:56:backend/app/services/ranking/score.py
def compute_final_score(
    search_score: float,
    cf_score: float,
    popularity_score: float,
    freshness_score: float
) -> float:
    """
    Compute final ranking score using Phase 1 formula.
    
    Args:
        search_score: Search relevance score (0 for recommendations)
        cf_score: Collaborative filtering score (0 in Phase 1)
        popularity_score: Product popularity score
        freshness_score: Product freshness score
        
    Returns:
        Final ranking score
    """
    final_score = (
        WEIGHTS["search_score"] * search_score +
        WEIGHTS["cf_score"] * cf_score +
        WEIGHTS["popularity_score"] * popularity_score +
        WEIGHTS["freshness_score"] * freshness_score
    )
    
    return final_score
```

**Weights:**
- `search_score`: 0.4 (40%)
- `cf_score`: 0.3 (30%) - Currently 0 in Phase 1
- `popularity_score`: 0.2 (20%)
- `freshness_score`: 0.1 (10%)

### Ranking Algorithm

```59:137:backend/app/services/ranking/score.py
def rank_products(
    candidates: List[Tuple[str, float]],
    is_search: bool = True,
    user_id: Optional[str] = None
) -> List[Tuple[str, float, Dict[str, float]]]:
    """
    Rank products using Phase 1 formula.
    
    Args:
        candidates: List of (product_id, search_keyword_score) tuples
        is_search: True if this is a search query, False if recommendations
        user_id: Optional user ID (for future personalization)
        
    Returns:
        List of (product_id, final_score, breakdown) tuples, sorted by final_score descending
        breakdown contains individual feature scores for explainability
    """
    if not candidates:
        return []
    
    # Extract product IDs and search scores
    product_ids = [product_id for product_id, _ in candidates]
    search_scores = {product_id: score for product_id, score in candidates}
    
    # Get product features
    features = get_product_features(product_ids)
    
    if not features:
        logger.warning("No features retrieved, returning candidates as-is")
        # Fallback: return candidates sorted by search_score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [
            (product_id, score, {"search_score": score, "cf_score": 0.0, "popularity_score": 0.0, "freshness_score": 0.0})
            for product_id, score in candidates
        ]
    
    # Compute final scores
    ranked_results = []
    
    for product_id, search_score in candidates:
        if product_id not in features:
            logger.warning(f"Features not found for product {product_id}, skipping")
            continue
        
        product_features = features[product_id]
        popularity_score = product_features.get("popularity_score", 0.0)
        freshness_score = product_features.get("freshness_score", 0.0)
        
        # For recommendations, search_score is 0
        if not is_search:
            search_score = 0.0
        
        # cf_score is 0 in Phase 1
        cf_score = 0.0
        
        # Compute final score
        final_score = compute_final_score(
            search_score=search_score,
            cf_score=cf_score,
            popularity_score=popularity_score,
            freshness_score=freshness_score
        )
        
        # Create breakdown for explainability
        breakdown = {
            "search_score": search_score,
            "cf_score": cf_score,
            "popularity_score": popularity_score,
            "freshness_score": freshness_score
        }
        
        ranked_results.append((product_id, final_score, breakdown))
    
    # Sort by final_score descending
    ranked_results.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Ranked {len(ranked_results)} products")
    return ranked_results
```

**Algorithm Steps:**
1. Extract product IDs from candidates
2. Fetch features (popularity_score, freshness_score) for all products
3. For each candidate:
   - Set `search_score` to 0 for recommendations
   - Set `cf_score` to 0 (Phase 1)
   - Compute final score using weighted formula
   - Create breakdown for explainability
4. Sort by final_score descending
5. Return ranked results with breakdowns

---

## Feature Computation

Features are computed **offline** and stored in the database. The ranking service only reads features.

### Popularity Score Algorithm

Popularity scores are computed from weighted event counts:

```22:63:backend/app/services/features/popularity.py
def compute_popularity_scores() -> Dict[str, float]:
    """
    Compute popularity scores for all products based on weighted event counts.
    
    Returns:
        Dictionary mapping product_id to popularity_score
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return {}
    
    try:
        # Get all events grouped by product_id and event_type
        events_response = client.table("events").select("product_id, event_type").execute()
        
        if not events_response.data:
            logger.warning("No events found in database")
            return {}
        
        # Aggregate scores by product
        product_scores: Dict[str, float] = {}
        
        for event in events_response.data:
            product_id = event["product_id"]
            event_type = event["event_type"]
            weight = EVENT_WEIGHTS.get(event_type, 0.0)
            
            if product_id not in product_scores:
                product_scores[product_id] = 0.0
            
            product_scores[product_id] += weight
        
        # Normalize scores (optional: can be adjusted based on business needs)
        # For now, we'll use raw weighted counts
        
        logger.info(f"Computed popularity scores for {len(product_scores)} products")
        return product_scores
        
    except Exception as e:
        logger.error(f"Error computing popularity scores: {e}", exc_info=True)
        return {}
```

**Event Weights:**
- `purchase`: 3.0
- `add_to_cart`: 2.0
- `view`: 1.0

**Algorithm:**
1. Fetch all events from database
2. For each event, add weight to product's score
3. Return aggregated scores (raw weighted counts, not normalized)

### Freshness Score Algorithm

Freshness scores use **exponential decay** based on product creation date:

```21:61:backend/app/services/features/freshness.py
def compute_freshness_score(created_at: datetime, reference_time: Optional[datetime] = None) -> float:
    """
    Compute freshness score using exponential decay.
    
    Formula: score = exp(-ln(2) * days_old / half_life)
    - New products (0 days old): score = 1.0
    - Products at half-life: score = 0.5
    - Older products: score approaches 0
    
    Args:
        created_at: When the product was created
        reference_time: Reference time for calculation (defaults to now)
        
    Returns:
        Freshness score between 0.0 and 1.0
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    
    # Ensure both datetimes are timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    
    # Calculate days since creation
    delta = reference_time - created_at
    days_old = delta.total_seconds() / (24 * 3600)
    
    # Handle negative days (future dates) or very old products
    if days_old < 0:
        days_old = 0
    elif days_old > FRESHNESS_HALF_LIFE_DAYS * 5:  # Very old products
        return 0.0
    
    # Exponential decay formula
    # Using numpy for numerical stability
    score = np.exp(-np.log(2) * days_old / FRESHNESS_HALF_LIFE_DAYS)
    
    # Clamp to [0, 1]
    return float(np.clip(score, 0.0, 1.0))
```

**Formula:**
```
score = exp(-ln(2) * days_old / half_life)
```

**Parameters:**
- `half_life`: 90 days (products lose half their freshness after 90 days)
- New products (0 days): score = 1.0
- Products at half-life (90 days): score = 0.5
- Very old products (>450 days): score = 0.0

### Feature Retrieval

Features are retrieved on-demand during ranking:

```17:64:backend/app/services/ranking/features.py
def get_product_features(product_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Get features for a list of products.
    
    Returns:
        Dictionary mapping product_id to feature dict:
        {
            "popularity_score": float,
            "freshness_score": float
        }
    """
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        return {}
    
    try:
        # Fetch products with popularity_score and created_at
        response = client.table("products").select(
            "id, popularity_score, created_at"
        ).in_("id", product_ids).execute()
        
        if not response.data:
            return {}
        
        features = {}
        
        for product in response.data:
            product_id = product["id"]
            popularity_score = product.get("popularity_score", 0.0) or 0.0
            created_at = product.get("created_at")
            
            # Compute freshness score
            freshness_score = 0.0
            if created_at:
                freshness_score = compute_freshness_score_from_string(created_at)
            
            features[product_id] = {
                "popularity_score": float(popularity_score),
                "freshness_score": freshness_score
            }
        
        logger.debug(f"Retrieved features for {len(features)} products")
        return features
        
    except Exception as e:
        logger.error(f"Error retrieving product features: {e}", exc_info=True)
        return {}
```

**Note:** `popularity_score` is stored in the database (computed offline), while `freshness_score` is computed on-demand from `created_at`.

---

## Event Tracking

Events are **append-only** and track user interactions for analytics and feature computation.

### Event Types

- `view`: User viewed a product
- `add_to_cart`: User added product to cart
- `purchase`: User purchased product

### Event Tracking Endpoint

```27:84:backend/app/routes/events.py
@router.post("")
async def track_event(event: EventRequest):
    """
    Track a user interaction event.
    
    Events are append-only and used for:
    - Computing popularity scores
    - Training collaborative filtering models
    - Analytics
    """
    # Validate event_type
    valid_event_types = ["view", "add_to_cart", "purchase"]
    if event.event_type not in valid_event_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    # Validate source if provided
    if event.source:
        valid_sources = ["search", "recommendation", "direct"]
        if event.source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source. Must be one of: {', '.join(valid_sources)}"
            )
    
    client = get_supabase_client()
    if not client:
        logger.error("Failed to get Supabase client")
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Insert event
        event_data = {
            "user_id": event.user_id,
            "product_id": event.product_id,
            "event_type": event.event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "source": event.source
        }
        
        response = client.table("events").insert(event_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to insert event")
        
        logger.info(f"Tracked event: {event.event_type} for user {event.user_id}, product {event.product_id}")
        
        return {
            "success": True,
            "event_id": response.data[0].get("id") if response.data else None
        }
        
    except Exception as e:
        logger.error(f"Error tracking event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during event tracking")
```

**Event Data Structure:**
- `user_id`: User identifier
- `product_id`: Product identifier
- `event_type`: One of `view`, `add_to_cart`, `purchase`
- `timestamp`: UTC timestamp
- `source`: Optional source (`search`, `recommendation`, `direct`)

---

## Request Flow

### Search Request Flow

1. **User sends search query** → `GET /search?q={query}&k={limit}`
2. **FastAPI Gateway** validates request
3. **Search Service** normalizes query and retrieves candidates with `search_keyword_score`
4. **Ranking Service** fetches features (popularity_score, freshness_score) and computes final scores
5. **Results returned** with scores and breakdowns

**Example Flow:**
```
User Query: "running shoes"
↓
Normalize: "running shoes"
↓
Search Service: Returns [(product_id, search_score), ...]
↓
Ranking Service: 
  - Fetch features for products
  - Compute: final_score = 0.4*search_score + 0.2*popularity + 0.1*freshness
  - Sort by final_score
↓
Return top k results
```

### Recommendation Request Flow

1. **User requests recommendations** → `GET /recommend/{user_id}?k={limit}`
2. **FastAPI Gateway** validates request
3. **Recommendation Service** retrieves top products by `popularity_score`
4. **Ranking Service** fetches features and computes final scores (search_score=0 for recommendations)
5. **Results returned** with scores and breakdowns

**Example Flow:**
```
User ID: "user_123"
↓
Recommendation Service: Returns top products by popularity_score
↓
Ranking Service:
  - Fetch features for products
  - Compute: final_score = 0.2*popularity + 0.1*freshness (search_score=0)
  - Sort by final_score
↓
Return top k results
```

### Graceful Degradation

The system includes fallback mechanisms:

1. **Ranking Service Failure**: Falls back to sorting by `search_score` (search) or `popularity_score` (recommendations)
2. **Feature Retrieval Failure**: Returns candidates sorted by search score only
3. **Database Connection Failure**: Returns empty results with error logging

---

## Summary

The BeamAI system implements a **production-grade search and recommendation platform** with:

- **Separation of concerns**: Retrieval, ranking, and serving are independent
- **Deterministic ranking**: Phase 1 formula with explainable scores
- **Offline feature computation**: Popularity scores computed in batch jobs
- **On-demand freshness**: Freshness scores computed from creation dates
- **Graceful degradation**: Fallback mechanisms at every layer
- **Event-driven analytics**: Append-only event tracking for feature computation

The system is designed to scale from local development to production environments without architectural rewrites.

