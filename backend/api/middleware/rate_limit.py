"""
Rate limiting middleware using Redis for distributed rate limiting.

Implements token bucket algorithm for flexible rate limiting with burst support.
"""

import time
from typing import Callable, Optional

import structlog
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm."""
    
    def __init__(self, app, redis_client_func=None):
        super().__init__(app)
        self.redis_client_func = redis_client_func
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.burst_limit = settings.RATE_LIMIT_BURST
        self.window_size = 60  # 1 minute window
    
    @property
    def redis_client(self):
        """Get Redis client from the function."""
        if self.redis_client_func:
            return self.redis_client_func()
        return None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""
        # Skip rate limiting for health checks and internal endpoints
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not await self._is_request_allowed(client_id, request):
            # Log rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                path=request.url.path,
                method=request.method,
                rate_limit=self.rate_limit,
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.rate_limit} requests per minute allowed",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        await self._add_rate_limit_headers(response, client_id)
        
        return response
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        # Skip for health checks
        if request.url.path == "/health":
            return True
        
        # Skip for documentation endpoints in development
        if settings.DEBUG and request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return True
        
        return False
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # Fallback to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxies."""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def _is_request_allowed(self, client_id: str, request: Request) -> bool:
        """Check if request is allowed based on rate limits."""
        if not self.redis_client:
            # If Redis is not available, allow all requests (fail open)
            logger.warning("Redis not available for rate limiting, allowing request")
            return True
        
        try:
            current_time = int(time.time())
            window_start = current_time - (current_time % self.window_size)
            
            # Create Redis key for this client and time window
            key = f"rate_limit:{client_id}:{window_start}"
            
            # Get current count for this window
            current_count = await self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Check if request is allowed
            if current_count >= self.rate_limit:
                return False
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_size)
            await pipe.execute()
            
            return True
            
        except Exception as e:
            # If Redis operations fail, allow the request (fail open)
            logger.error(
                "Rate limiting Redis operation failed",
                error=str(e),
                client_id=client_id,
                exc_info=True
            )
            return True
    
    async def _add_rate_limit_headers(self, response: Response, client_id: str) -> None:
        """Add rate limiting headers to response."""
        if not self.redis_client:
            return
        
        try:
            current_time = int(time.time())
            window_start = current_time - (current_time % self.window_size)
            key = f"rate_limit:{client_id}:{window_start}"
            
            # Get current usage
            current_count = await self.redis_client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Calculate remaining requests and reset time
            remaining = max(0, self.rate_limit - current_count)
            reset_time = window_start + self.window_size
            
            # Add headers
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
        except Exception as e:
            logger.error(
                "Failed to add rate limit headers",
                error=str(e),
                client_id=client_id
            )