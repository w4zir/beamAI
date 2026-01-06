# API_CONTRACTS.md

## Search Endpoint

GET /search?q={query}&user_id={optional}&k={int}

Response:
```
[
  {
    "product_id": "string",
    "score": float,
    "reason": "optional"
  }
]
```

## Recommendation Endpoint

GET /recommend/{user_id}?k={int}

Response format same as search.

---

## Shadow Mode Endpoints (Phase 4.3)

**Purpose**: Test new models/algorithms without user impact

### Shadow Search

POST /admin/shadow/search

**Request Body**:
```json
{
  "query": "running shoes",
  "user_id": "user_123",
  "k": 10,
  "model_version": "v2.0.0"
}
```

**Response**: Same format as search endpoint

**Behavior**: 
- Process request with new model
- Compare with production model
- Log metrics (latency, scores, rankings)
- Do NOT serve results to user

### Shadow Recommend

POST /admin/shadow/recommend

**Request Body**:
```json
{
  "user_id": "user_123",
  "k": 10,
  "model_version": "v2.0.0"
}
```

**Response**: Same format as recommendation endpoint

**Behavior**: Same as shadow search

**Security**: Admin-only, requires authentication

---

## Authentication Endpoints (Phase 5.1)

**Purpose**: Manage API keys for authentication

### Create API Key

POST /auth/api-keys

**Request Body**:
```json
{
  "name": "Production Frontend",
  "rate_limit_search": 1000,
  "rate_limit_recommend": 500,
  "allowed_ips": ["192.168.1.0/24"],
  "expires_at": "2026-12-31T23:59:59Z"
}
```

**Response**:
```json
{
  "key_id": "key_123",
  "api_key": "sk_live_abc123...",
  "name": "Production Frontend",
  "created_at": "2026-01-01T00:00:00Z",
  "rate_limit_search": 1000,
  "rate_limit_recommend": 500
}
```

**Security**: Admin-only

### List API Keys

GET /auth/api-keys

**Response**:
```json
[
  {
    "key_id": "key_123",
    "name": "Production Frontend",
    "created_at": "2026-01-01T00:00:00Z",
    "last_used_at": "2026-01-02T10:30:00Z",
    "rate_limit_search": 1000,
    "rate_limit_recommend": 500
  }
]
```

**Security**: Admin-only

### Revoke API Key

DELETE /auth/api-keys/{key_id}

**Response**: 204 No Content

**Security**: Admin-only

---

## A/B Testing Endpoints (Phase 8.1)

**Purpose**: Manage experiments and get experiment variants

### Create Experiment

POST /experiments

**Request Body**:
```json
{
  "name": "Test New Ranking Weights",
  "description": "Test new ranking weights",
  "traffic_split": {"control": 0.5, "treatment": 0.5},
  "variants": {
    "control": {"config": {"ranking_weights": [0.4, 0.3, 0.2, 0.1]}},
    "treatment": {"config": {"ranking_weights": [0.3, 0.4, 0.2, 0.1]}}
  },
  "metrics": ["ctr", "cvr", "revenue"]
}
```

**Response**:
```json
{
  "experiment_id": "ranking_weights_v2",
  "name": "Test New Ranking Weights",
  "status": "running",
  "created_at": "2026-01-01T00:00:00Z"
}
```

**Security**: Admin-only

### Get Experiment

GET /experiments/{experiment_id}

**Response**: Experiment configuration and status

**Security**: Admin-only

### Assign Variant

POST /experiments/{experiment_id}/assign

**Request Body**:
```json
{
  "user_id": "user_123",
  "context": {"query": "running shoes", "source": "search"}
}
```

**Response**:
```json
{
  "variant": "treatment",
  "config": {"ranking_weights": [0.3, 0.4, 0.2, 0.1]}
}
```

**Usage**: Called by search/recommendation services to get experiment variant

**Security**: Internal service-to-service (or authenticated API clients)

### Get Experiment Results

GET /experiments/{experiment_id}/results

**Response**:
```json
{
  "experiment_id": "ranking_weights_v2",
  "status": "completed",
  "sample_size": {"control": 10000, "treatment": 10000},
  "metrics": {
    "ctr": {
      "control": 0.15,
      "treatment": 0.17,
      "difference": 0.02,
      "p_value": 0.03,
      "significant": true
    }
  },
  "winner": "treatment",
  "recommendation": "rollout"
}
```

**Security**: Admin-only

**See**: `specs/EXPERIMENTATION.md` for detailed experiment framework

---

## Explainability Endpoints (Phase 8.4)

**Purpose**: Explain ranking decisions for debugging and user trust

### Ranking Explanation

GET /search/explain?q={query}&product_id={product_id}

**Response**:
```json
{
  "product_id": "prod_123",
  "query": "running shoes",
  "final_score": 0.87,
  "breakdown": {
    "search_score": 0.92,
    "cf_score": 0.78,
    "popularity_score": 0.85,
    "freshness_score": 0.95
  },
  "weights": [0.4, 0.3, 0.2, 0.1],
  "explanation": "Strong keyword match + high collaborative filtering affinity",
  "rank": 3
}
```

**Usage**: Optional field in search/recommendation responses, or separate endpoint for debugging

### Debug Ranking

GET /debug/ranking/{product_id}?query={query}&user_id={user_id}

**Response**: Same format as ranking explanation

**Security**: Admin-only, internal debugging

**See**: `specs/AI_ARCHITECTURE.md` for AI-powered explainability (AI Phase 3)

## Rate Limits

### Per IP Address
- Search: 100 requests/minute (burst: 150)
- Recommend: 50 requests/minute (burst: 75)

### Per API Key (if authenticated)
- Search: 1000 requests/minute
- Recommend: 500 requests/minute

### Abuse Detection
- Same query >20 times/minute → throttle
- Sequential product_id enumeration → flag

### Implementation
- Redis with sliding window counters
- 429 status code with Retry-After header