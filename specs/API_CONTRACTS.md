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