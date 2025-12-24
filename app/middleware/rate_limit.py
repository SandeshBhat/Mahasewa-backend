"""
Rate limiting middleware for FastAPI
Uses slowapi with Redis backend for distributed rate limiting
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
from typing import Optional

from app.config import settings

# Initialize Redis connection for rate limiting
redis_client: Optional[redis.Redis] = None

def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client for rate limiting"""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True
            )
            # Test connection
            redis_client.ping()
        except Exception as e:
            # If Redis is not available, rate limiting will use in-memory storage
            # This is acceptable for single-instance deployments
            print(f"Warning: Redis not available for rate limiting: {e}")
            print("Rate limiting will use in-memory storage (not suitable for distributed deployments)")
            redis_client = None
    return redis_client


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key based on user authentication or IP address
    Prioritizes authenticated users for better rate limiting
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"rate_limit:user:{user_id}"
    
    # Fallback to IP address
    return f"rate_limit:ip:{get_remote_address(request)}"


# Initialize limiter
# Use Redis if available, otherwise use in-memory storage
# Note: In-memory storage only works for single-instance deployments
storage_uri = settings.REDIS_URL if settings.REDIS_URL and settings.REDIS_URL != "redis://localhost:6379/0" else "memory://"

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=storage_uri,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute", f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
    headers_enabled=True,  # Include rate limit headers in response
    retry_after="x-ratelimit-retry-after"
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded errors
    """
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": exc.retry_after
        }
    )
    response = _rate_limit_exceeded_handler(request, exc, response)
    return response

