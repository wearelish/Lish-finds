"""
Advanced caching strategies for LishFind application.

Implements multi-level caching with Redis, in-memory, and query result caching.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import pickle

import structlog
from fastapi import Request

from core.config import settings
from database.redis import get_redis_client

logger = structlog.get_logger(__name__)

# In-memory cache for frequently accessed data
_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_stats = {"hits": 0, "misses": 0, "sets": 0}

class CacheManager:
    """Advanced cache manager with multiple cache layers."""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = bool(settings.REDIS_URL)
        self.default_ttl = settings.CACHE_TTL_SECONDS
        self.memory_cache_size = 1000  # Max items in memory cache
        
    async def init_redis(self):
        """Initialize Redis connection if available."""
        if self.enabled:
            try:
                self.redis_client = await get_redis_client()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning("Redis cache initialization failed", error=str(e))
                self.enabled = False
    
    def _build_key(self, prefix: str, *args, **kwargs) -> str:
        """Build a consistent cache key."""
        # Create a unique key from arguments
        key_data = {
            'args': args,
            'kwargs': {k: v for k, v in kwargs.items() if not k.startswith('_')}
        }
        
        # Hash the key data for consistent keys
        key_hash = hashlib.md5(
            json.dumps(key_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]
        
        return f"lishfind:{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then Redis)."""
        # Check memory cache first
        if key in _memory_cache:
            cache_entry = _memory_cache[key]
            if cache_entry['expires'] > time.time():
                _cache_stats["hits"] += 1
                logger.debug("Memory cache hit", key=key)
                return cache_entry['data']
            else:
                # Expired, remove from memory cache
                del _memory_cache[key]
        
        # Check Redis cache
        if self.enabled and self.redis_client:
            try:
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    try:
                        data = pickle.loads(cached_data)
                        _cache_stats["hits"] += 1
                        logger.debug("Redis cache hit", key=key)
                        
                        # Store in memory cache for faster future access
                        self._set_memory_cache(key, data, 300)  # 5 min in memory
                        return data
                    except Exception as e:
                        logger.warning("Failed to deserialize cached data", key=key, error=str(e))
            except Exception as e:
                logger.warning("Redis cache get failed", key=key, error=str(e))
        
        _cache_stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (both memory and Redis)."""
        ttl = ttl or self.default_ttl
        
        try:
            # Set in memory cache
            self._set_memory_cache(key, value, min(ttl, 600))  # Max 10 min in memory
            
            # Set in Redis cache
            if self.enabled and self.redis_client:
                try:
                    serialized_data = pickle.dumps(value)
                    await self.redis_client.setex(key, ttl, serialized_data)
                    logger.debug("Redis cache set", key=key, ttl=ttl)
                except Exception as e:
                    logger.warning("Redis cache set failed", key=key, error=str(e))
                    return False
            
            _cache_stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    def _set_memory_cache(self, key: str, value: Any, ttl: int):
        """Set value in memory cache with size limit."""
        # Enforce cache size limit
        if len(_memory_cache) >= self.memory_cache_size:
            # Remove oldest entries
            sorted_items = sorted(
                _memory_cache.items(),
                key=lambda x: x[1]['created']
            )
            for old_key, _ in sorted_items[:self.memory_cache_size // 4]:
                del _memory_cache[old_key]
        
        _memory_cache[key] = {
            'data': value,
            'created': time.time(),
            'expires': time.time() + ttl
        }
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        deleted = False
        
        # Remove from memory cache
        if key in _memory_cache:
            del _memory_cache[key]
            deleted = True
        
        # Remove from Redis cache
        if self.enabled and self.redis_client:
            try:
                result = await self.redis_client.delete(key)
                deleted = deleted or bool(result)
            except Exception as e:
                logger.warning("Redis cache delete failed", key=key, error=str(e))
        
        return deleted
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all cache keys matching a pattern."""
        cleared = 0
        
        # Clear from memory cache
        keys_to_delete = [k for k in _memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _memory_cache[key]
        cleared += len(keys_to_delete)
        
        # Clear from Redis cache
        if self.enabled and self.redis_client:
            try:
                keys = await self.redis_client.keys(f"*{pattern}*")
                if keys:
                    result = await self.redis_client.delete(*keys)
                    cleared += result
            except Exception as e:
                logger.warning("Redis pattern clear failed", pattern=pattern, error=str(e))
        
        logger.info("Cache pattern cleared", pattern=pattern, count=cleared)
        return cleared
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = _cache_stats.copy()
        stats["memory_cache_size"] = len(_memory_cache)
        stats["hit_rate"] = (
            stats["hits"] / max(stats["hits"] + stats["misses"], 1) * 100
        )
        
        if self.enabled and self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats["redis_info"] = {
                    "connected_clients": redis_info.get("connected_clients"),
                    "used_memory_human": redis_info.get("used_memory_human"),
                    "keyspace_hits": redis_info.get("keyspace_hits"),
                    "keyspace_misses": redis_info.get("keyspace_misses"),
                }
            except Exception:
                stats["redis_info"] = "unavailable"
        
        return stats


# Global cache manager
cache_manager = CacheManager()


def cached(
    prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    skip_if: Optional[Callable] = None
):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Custom function to build cache key
        skip_if: Function to determine if caching should be skipped
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check if caching should be skipped
            if skip_if and skip_if(*args, **kwargs):
                return await func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_manager._build_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit for function", function=func.__name__, key=cache_key)
                return cached_result
            
            # Execute function and cache result
            logger.debug("Cache miss for function", function=func.__name__, key=cache_key)
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, we can't use async cache operations
            # This is a simplified version for sync functions
            return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class QueryCache:
    """Specialized cache for database queries."""
    
    def __init__(self):
        self.prefix = "query"
        self.default_ttl = 3600  # 1 hour for queries
    
    async def get_search_results(
        self, 
        query: str, 
        filters: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        cache_key = cache_manager._build_key(
            f"{self.prefix}:search",
            query.lower().strip(),
            **filters
        )
        return await cache_manager.get(cache_key)
    
    async def set_search_results(
        self,
        query: str,
        filters: Dict[str, Any],
        results: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache search results."""
        cache_key = cache_manager._build_key(
            f"{self.prefix}:search",
            query.lower().strip(),
            **filters
        )
        return await cache_manager.set(cache_key, results, ttl or self.default_ttl)
    
    async def get_business_details(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get cached business details."""
        cache_key = f"{self.prefix}:business:{business_id}"
        return await cache_manager.get(cache_key)
    
    async def set_business_details(
        self,
        business_id: str,
        business_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache business details."""
        cache_key = f"{self.prefix}:business:{business_id}"
        return await cache_manager.set(cache_key, business_data, ttl or 7200)  # 2 hours
    
    async def invalidate_business(self, business_id: str) -> bool:
        """Invalidate all cache entries for a business."""
        patterns = [
            f"business:{business_id}",
            f"search",  # Search results might contain this business
            f"recommendations"  # Recommendations might include this business
        ]
        
        total_cleared = 0
        for pattern in patterns:
            cleared = await cache_manager.clear_pattern(pattern)
            total_cleared += cleared
        
        logger.info("Business cache invalidated", business_id=business_id, cleared=total_cleared)
        return total_cleared > 0


# Global query cache
query_cache = QueryCache()


class RequestCache:
    """Request-level caching middleware."""
    
    def __init__(self):
        self.cacheable_endpoints = {
            "/api/v1/search/",
            "/api/v1/recommendations/",
            "/api/v1/ranking/",
            "/api/v1/business/",
        }
        self.cache_ttl = 300  # 5 minutes for API responses
    
    def is_cacheable(self, request: Request) -> bool:
        """Check if request is cacheable."""
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Check if endpoint is cacheable
        path = request.url.path
        for endpoint in self.cacheable_endpoints:
            if path.startswith(endpoint):
                return True
        
        return False
    
    def build_request_key(self, request: Request) -> str:
        """Build cache key for request."""
        # Include path, query parameters, and relevant headers
        key_parts = [
            request.url.path,
            str(sorted(request.query_params.items())),
        ]
        
        # Include user-specific data if authenticated
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        key_string = "|".join(key_parts)
        return cache_manager._build_key("request", key_string)
    
    async def get_cached_response(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get cached response for request."""
        if not self.is_cacheable(request):
            return None
        
        cache_key = self.build_request_key(request)
        return await cache_manager.get(cache_key)
    
    async def cache_response(
        self,
        request: Request,
        response_data: Dict[str, Any]
    ) -> bool:
        """Cache response for request."""
        if not self.is_cacheable(request):
            return False
        
        cache_key = self.build_request_key(request)
        return await cache_manager.set(cache_key, response_data, self.cache_ttl)


# Global request cache
request_cache = RequestCache()


# Convenience functions
async def cache_search_results(
    query: str,
    results: List[Dict[str, Any]],
    **filters
) -> bool:
    """Cache search results with filters."""
    return await query_cache.set_search_results(query, filters, results)


async def get_cached_search_results(
    query: str,
    **filters
) -> Optional[List[Dict[str, Any]]]:
    """Get cached search results."""
    return await query_cache.get_search_results(query, filters)


async def cache_business_data(
    business_id: str,
    business_data: Dict[str, Any]
) -> bool:
    """Cache business data."""
    return await query_cache.set_business_details(business_id, business_data)


async def get_cached_business_data(business_id: str) -> Optional[Dict[str, Any]]:
    """Get cached business data."""
    return await query_cache.get_business_details(business_id)


async def invalidate_business_cache(business_id: str) -> bool:
    """Invalidate business-related cache entries."""
    return await query_cache.invalidate_business(business_id)


# Cache warming functions
async def warm_popular_searches():
    """Pre-populate cache with popular search results."""
    popular_queries = [
        "restaurants near me",
        "coffee shops",
        "gas stations",
        "pharmacies",
        "hotels"
    ]
    
    logger.info("Starting cache warming for popular searches")
    
    for query in popular_queries:
        try:
            # This would call your actual search function
            # results = await search_service.search(query, ...)
            # await cache_search_results(query, results)
            logger.debug("Cache warmed for query", query=query)
        except Exception as e:
            logger.warning("Failed to warm cache for query", query=query, error=str(e))
    
    logger.info("Cache warming completed")


# Middleware for automatic request caching
async def cache_middleware(request: Request, call_next):
    """Middleware for automatic request/response caching."""
    
    # Try to get cached response
    cached_response = await request_cache.get_cached_response(request)
    if cached_response:
        logger.debug("Serving cached response", path=request.url.path)
        return cached_response
    
    # Process request
    response = await call_next(request)
    
    # Cache successful responses
    if hasattr(response, 'status_code') and response.status_code == 200:
        # Extract response data (this depends on your response format)
        try:
            if hasattr(response, 'body'):
                response_data = response.body
                await request_cache.cache_response(request, response_data)
        except Exception as e:
            logger.warning("Failed to cache response", error=str(e))
    
    return response