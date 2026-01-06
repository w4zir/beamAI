"""
Rate limiting middleware using Redis sliding window counter.

Per API_CONTRACTS.md:
- Per IP: Search 100/min (burst 150), Recommend 50/min (burst 75)
- Per API Key: Search 1000/min, Recommend 500/min
- Abuse detection: Same query >20 times/minute, Sequential product_id enumeration
"""
import time
import hashlib
from typing import Optional, Dict, Set
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.cache import get_redis_client
from app.core.logging import get_logger
from app.core.metrics import (
    record_rate_limit_hit,
    record_abuse_detection,
    update_rate_limit_list_sizes,
)

logger = get_logger(__name__)

# Rate limits per API_CONTRACTS.md
RATE_LIMITS = {
    "/search": {
        "ip": {"limit": 100, "burst": 150, "window": 60},  # 100/min, burst 150
        "api_key": {"limit": 1000, "burst": 1500, "window": 60},  # 1000/min, burst 1500
    },
    "/recommend": {
        "ip": {"limit": 50, "burst": 75, "window": 60},  # 50/min, burst 75
        "api_key": {"limit": 500, "burst": 750, "window": 60},  # 500/min, burst 750
    },
}

# Abuse detection thresholds
ABUSE_THRESHOLDS = {
    "same_query": 20,  # Same query >20 times/minute
    "sequential_enumeration": 5,  # Sequential product_id requests
}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers."""
    # Check X-Forwarded-For header (for proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct client
    if request.client:
        return request.client.host
    
    return "unknown"


def get_api_key(request: Request) -> Optional[str]:
    """Extract API key from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    # Support "Bearer <token>" or "ApiKey <key>" format
    parts = auth_header.split(" ", 1)
    if len(parts) == 2:
        scheme, key = parts
        if scheme.lower() in ("bearer", "apikey"):
            return key
    
    return None


def hash_query(query: str) -> str:
    """Generate hash for query string."""
    return hashlib.md5(query.encode()).hexdigest()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window counter.
    
    Implements:
    - Per-IP rate limiting
    - Per-API-key rate limiting
    - Abuse detection (same query, sequential enumeration)
    - Whitelist/blacklist support
    """
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()
        self._query_history: Dict[str, list] = {}  # IP -> list of (timestamp, query_hash)
        self._product_history: Dict[str, list] = {}  # IP -> list of (timestamp, product_id)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Get endpoint path (normalize)
        endpoint = request.url.path
        if endpoint.startswith("/search"):
            endpoint = "/search"
        elif endpoint.startswith("/recommend"):
            endpoint = "/recommend"
        else:
            # Unknown endpoint, allow through
            return await call_next(request)
        
        # Get client identifier
        client_ip = get_client_ip(request)
        api_key = get_api_key(request)
        
        # Check blacklist
        if client_ip in self.blacklist or (api_key and api_key in self.blacklist):
            logger.warning(
                "rate_limit_blacklisted",
                ip=client_ip,
                api_key=api_key[:10] + "..." if api_key else None,
                endpoint=endpoint,
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"},
            )
        
        # Check whitelist (bypass rate limiting)
        if client_ip in self.whitelist or (api_key and api_key in self.whitelist):
            return await call_next(request)
        
        # Get rate limit config
        if endpoint not in RATE_LIMITS:
            return await call_next(request)
        
        config = RATE_LIMITS[endpoint]
        
        # Determine identifier (prefer API key over IP)
        identifier = api_key if api_key else client_ip
        limit_type = "api_key" if api_key else "ip"
        limit_config = config[limit_type]
        
        # Check rate limit using sliding window
        allowed, remaining, reset_time = await self._check_rate_limit(
            identifier=identifier,
            limit=limit_config["limit"],
            window=limit_config["window"],
            endpoint=endpoint,
        )
        
        if not allowed:
            record_rate_limit_hit(endpoint, limit_type)
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier[:10] + "..." if len(identifier) > 10 else identifier,
                limit_type=limit_type,
                endpoint=endpoint,
            )
            
            retry_after = int(reset_time - time.time())
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                },
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(limit_config["limit"])
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            return response
        
        # Abuse detection
        abuse_detected = await self._detect_abuse(
            client_ip=client_ip,
            endpoint=endpoint,
            request=request,
        )
        
        if abuse_detected:
            # Still process request but log abuse
            pass
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit_config["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    async def _check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int,
        endpoint: str,
    ) -> tuple[bool, int, float]:
        """
        Check rate limit using Redis sliding window counter.
        
        Returns:
            (allowed, remaining, reset_time)
        """
        if not self.redis_client:
            # Redis not available, allow request (graceful degradation)
            return True, limit, time.time() + window
        
        try:
            now = time.time()
            window_start = now - window
            key = f"ratelimit:{endpoint}:{identifier}"
            
            # Use Redis sorted set for sliding window
            # Add current request timestamp
            await self.redis_client.zadd(key, {str(now): now})
            
            # Remove old entries outside window
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in window
            count = await self.redis_client.zcard(key)
            
            # Set expiration on key
            await self.redis_client.expire(key, window)
            
            # Calculate remaining and reset time
            remaining = max(0, limit - count)
            reset_time = now + window
            
            allowed = count < limit
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.warning(
                "rate_limit_check_failed",
                identifier=identifier[:10] + "..." if len(identifier) > 10 else identifier,
                error=str(e),
                error_type=type(e).__name__,
            )
            # On error, allow request (fail open)
            return True, limit, time.time() + window
    
    async def _detect_abuse(
        self,
        client_ip: str,
        endpoint: str,
        request: Request,
    ) -> bool:
        """
        Detect abuse patterns.
        
        Returns:
            True if abuse detected, False otherwise
        """
        try:
            # Same query detection
            if endpoint == "/search":
                query = request.query_params.get("q")
                if query:
                    query_hash = hash_query(query)
                    now = time.time()
                    
                    # Clean old entries (older than 1 minute)
                    if client_ip in self._query_history:
                        self._query_history[client_ip] = [
                            (ts, qh) for ts, qh in self._query_history[client_ip]
                            if now - ts < 60
                        ]
                    
                    # Add current query
                    if client_ip not in self._query_history:
                        self._query_history[client_ip] = []
                    self._query_history[client_ip].append((now, query_hash))
                    
                    # Check if same query repeated too many times
                    same_query_count = sum(
                        1 for _, qh in self._query_history[client_ip]
                        if qh == query_hash
                    )
                    
                    if same_query_count > ABUSE_THRESHOLDS["same_query"]:
                        record_abuse_detection("same_query")
                        logger.warning(
                            "abuse_detected_same_query",
                            ip=client_ip,
                            query_hash=query_hash,
                            count=same_query_count,
                        )
                        return True
            
            # Sequential product_id enumeration detection
            if endpoint == "/recommend":
                # Extract product_id from path if present
                path_parts = request.url.path.split("/")
                if len(path_parts) >= 3:
                    # Check if it looks like a product_id
                    potential_id = path_parts[-1]
                    
                    now = time.time()
                    
                    # Clean old entries
                    if client_ip in self._product_history:
                        self._product_history[client_ip] = [
                            (ts, pid) for ts, pid in self._product_history[client_ip]
                            if now - ts < 60
                        ]
                    
                    # Add current product_id
                    if client_ip not in self._product_history:
                        self._product_history[client_ip] = []
                    self._product_history[client_ip].append((now, potential_id))
                    
                    # Check for sequential pattern (simplified: check if many different IDs)
                    unique_ids = len(set(pid for _, pid in self._product_history[client_ip]))
                    if unique_ids > ABUSE_THRESHOLDS["sequential_enumeration"] * 10:
                        record_abuse_detection("sequential_enumeration")
                        logger.warning(
                            "abuse_detected_sequential_enumeration",
                            ip=client_ip,
                            unique_ids=unique_ids,
                        )
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(
                "abuse_detection_error",
                ip=client_ip,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
    
    def add_to_whitelist(self, identifier: str) -> None:
        """Add identifier to whitelist."""
        self.whitelist.add(identifier)
        update_rate_limit_list_sizes(len(self.whitelist), len(self.blacklist))
        logger.info("rate_limit_whitelist_added", identifier=identifier[:10] + "...")
    
    def remove_from_whitelist(self, identifier: str) -> None:
        """Remove identifier from whitelist."""
        self.whitelist.discard(identifier)
        update_rate_limit_list_sizes(len(self.whitelist), len(self.blacklist))
        logger.info("rate_limit_whitelist_removed", identifier=identifier[:10] + "...")
    
    def add_to_blacklist(self, identifier: str) -> None:
        """Add identifier to blacklist."""
        self.blacklist.add(identifier)
        update_rate_limit_list_sizes(len(self.whitelist), len(self.blacklist))
        logger.info("rate_limit_blacklist_added", identifier=identifier[:10] + "...")
    
    def remove_from_blacklist(self, identifier: str) -> None:
        """Remove identifier from blacklist."""
        self.blacklist.discard(identifier)
        update_rate_limit_list_sizes(len(self.whitelist), len(self.blacklist))
        logger.info("rate_limit_blacklist_removed", identifier=identifier[:10] + "...")


# Global rate limit middleware instance
_rate_limit_middleware: Optional[RateLimitMiddleware] = None


def get_rate_limit_middleware() -> Optional[RateLimitMiddleware]:
    """Get global rate limit middleware instance."""
    return _rate_limit_middleware


def initialize_rate_limit_middleware(app) -> RateLimitMiddleware:
    """Initialize and return rate limit middleware."""
    global _rate_limit_middleware
    redis_client = get_redis_client()
    _rate_limit_middleware = RateLimitMiddleware(app, redis_client=redis_client)
    # Add middleware to app (will be updated with Redis client in startup)
    app.add_middleware(RateLimitMiddleware, app=app, redis_client=redis_client)
    return _rate_limit_middleware

