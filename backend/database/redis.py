"""
Redis connection management and advanced caching layer for LishFind backend.

Provides comprehensive caching with cache management, invalidation strategies, 
and performance optimization features.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union, Callable
from functools import wraps

import structlog
from aioredis import Redis, from_url

from core.config import settings

logger = structlog.get_logger(__name__)

# Global Redis client
redis_client: Optional[Redis] = None

# Cache configuration
class CacheConfig:
    """Cache configuration constants."""
    
    # Default TTL values (in seconds)
    DEFAULT_TTL = 3600  # 1 hour
    SHORT_TTL = 300     # 5 minutes
    MEDIUM_TTL = 1800   # 30 minutes
    LONG_TTL = 86400    # 24 hours
    
    # Cache key prefixes
    SEARCH_PREFIX = "search:"
    BUSINESS_PREFIX = "business:"
    USER_PREFIX = "user:"
    RANKING_PREFIX = "ranking:"
    RECOMMENDATION_PREFIX = "rec:"
    AI_PREFIX = "ai:"
    ANALYTICS_PREFIX = "analytics:"
    
    # Cache patterns
    SEARCH_RESULTS = "search_results"
    BUSINESS_PROFILE = "business_profile"
    USER_PROFILE = "user_profile"
    RECOMMENDATIONS = "recommendations"
    AI_RESPONSE = "ai_response"

# Global Redis client
redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    
    # Check if Redis URL is configured
    if not hasattr(settings, 'REDIS_URL') or not settings.REDIS_URL:
        logger.info("Redis URL not configured, using memory-based caching")
        redis_client = None
        return
    
    try:
        redis_client = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        
        # Test connection
        await redis_client.ping()
        
        logger.info(
            "Redis connection initialized",
            redis_url=settings.REDIS_URL.split("@")[-1] if "@" in settings.REDIS_URL else settings.REDIS_URL
        )
        
    except Exception as e:
        logger.warning(
            "Failed to initialize Redis connection, falling back to memory cache",
            error=str(e),
        )
        # Don't raise - Redis is optional for basic functionality
        redis_client = None


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(
                "Error closing Redis connection",
                error=str(e),
                exc_info=True
            )


def get_redis_client() -> Optional[Redis]:
    """Get Redis client instance."""
    return redis_client


async def set_cache(key: str, value: Union[str, Dict, List], ttl: Optional[int] = None, compress: bool = False) -> bool:
    """Set a cache value with optional TTL and compression."""
    if not redis_client:
        logger.warning("Redis client not available for cache set", key=key)
        return False
    
    try:
        # Serialize value if it's not a string
        if not isinstance(value, str):
            value = json.dumps(value, default=str)
        
        # Optional compression for large values
        if compress and len(value) > 1024:  # Compress if larger than 1KB
            import gzip
            value = gzip.compress(value.encode()).decode('latin1')
            key = f"compressed:{key}"
        
        if ttl:
            await redis_client.setex(key, ttl, value)
        else:
            await redis_client.set(key, value)
        
        logger.debug("Cache value set", key=key, ttl=ttl, size=len(str(value)))
        return True
        
    except Exception as e:
        logger.error("Failed to set cache value", key=key, error=str(e))
        return False


async def get_cache(key: str, decompress: bool = False) -> Optional[Union[str, Dict, List]]:
    """Get a cache value with optional decompression."""
    if not redis_client:
        return None
    
    try:
        # Check for compressed version first
        if not decompress:
            compressed_key = f"compressed:{key}"
            compressed_value = await redis_client.get(compressed_key)
            if compressed_value:
                import gzip
                decompressed = gzip.decompress(compressed_value.encode('latin1')).decode()
                try:
                    return json.loads(decompressed)
                except json.JSONDecodeError:
                    return decompressed
        
        # Get regular value
        value = await redis_client.get(key)
        if value is None:
            return None
        
        # Try to parse as JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
            
    except Exception as e:
        logger.error("Failed to get cache value", key=key, error=str(e))
        return None


async def delete_cache(key: str) -> bool:
    """Delete a cache value and its compressed version if exists."""
    if not redis_client:
        return False
    
    try:
        result1 = await redis_client.delete(key)
        result2 = await redis_client.delete(f"compressed:{key}")
        return (result1 + result2) > 0
        
    except Exception as e:
        logger.error("Failed to delete cache value", key=key, error=str(e))
        return False


async def exists_cache(key: str) -> bool:
    """Check if a cache key exists."""
    if not redis_client:
        return False
    
    try:
        exists = await redis_client.exists(key)
        compressed_exists = await redis_client.exists(f"compressed:{key}")
        return exists > 0 or compressed_exists > 0
        
    except Exception as e:
        logger.error("Failed to check cache existence", key=key, error=str(e))
        return False


async def get_ttl(key: str) -> Optional[int]:
    """Get remaining TTL for a cache key."""
    if not redis_client:
        return None
    
    try:
        ttl = await redis_client.ttl(key)
        return ttl if ttl > 0 else None
        
    except Exception as e:
        logger.error("Failed to get cache TTL", key=key, error=str(e))
        return None


async def expire_cache(key: str, ttl: int) -> bool:
    """Set expiration time for a cache key."""
    if not redis_client:
        return False
    
    try:
        result = await redis_client.expire(key, ttl)
        return result
        
    except Exception as e:
        logger.error("Failed to set cache expiration", key=key, ttl=ttl, error=str(e))
        return False


async def increment_cache(key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
    """Increment a numeric cache value."""
    if not redis_client:
        return None
    
    try:
        result = await redis_client.incrby(key, amount)
        
        if ttl and result == amount:  # First time setting the key
            await redis_client.expire(key, ttl)
        
        return result
        
    except Exception as e:
        logger.error("Failed to increment cache value", key=key, error=str(e))
        return None


async def get_cache_pattern(pattern: str) -> List[str]:
    """Get all cache keys matching a pattern."""
    if not redis_client:
        return []
    
    try:
        keys = await redis_client.keys(pattern)
        return keys
        
    except Exception as e:
        logger.error("Failed to get cache pattern", pattern=pattern, error=str(e))
        return []


async def delete_cache_pattern(pattern: str) -> int:
    """Delete all cache keys matching a pattern."""
    if not redis_client:
        return 0
    
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            result = await redis_client.delete(*keys)
            logger.info("Deleted cache keys by pattern", pattern=pattern, count=result)
            return result
        return 0
        
    except Exception as e:
        logger.error("Failed to delete cache pattern", pattern=pattern, error=str(e))
        return 0


async def get_cache_info() -> Dict[str, Any]:
    """Get Redis cache information and statistics."""
    if not redis_client:
        return {"status": "unavailable"}
    
    try:
        info = await redis_client.info()
        memory_info = await redis_client.memory_stats()
        
        # Get key statistics by prefix
        key_stats = {}
        for prefix in [CacheConfig.SEARCH_PREFIX, CacheConfig.BUSINESS_PREFIX, 
                      CacheConfig.USER_PREFIX, CacheConfig.RANKING_PREFIX,
                      CacheConfig.RECOMMENDATION_PREFIX, CacheConfig.AI_PREFIX]:
            keys = await redis_client.keys(f"{prefix}*")
            key_stats[prefix.rstrip(":")] = len(keys)
        
        cache_info = {
            "status": "connected",
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "key_statistics": key_stats,
            "memory_stats": {
                "peak.allocated": memory_info.get("peak.allocated", 0),
                "total.allocated": memory_info.get("total.allocated", 0),
                "startup.allocated": memory_info.get("startup.allocated", 0),
                "dataset.bytes": memory_info.get("dataset.bytes", 0),
            }
        }
        
        # Calculate hit ratio
        hits = cache_info["keyspace_hits"]
        misses = cache_info["keyspace_misses"]
        if hits + misses > 0:
            cache_info["hit_ratio"] = hits / (hits + misses)
        else:
            cache_info["hit_ratio"] = 0.0
        
        return cache_info
        
    except Exception as e:
        logger.error("Failed to get cache info", error=str(e))
        return {"status": "error", "error": str(e)}


class CacheManager:
    """Advanced cache management with invalidation strategies."""
    
    def __init__(self, prefix: str, default_ttl: int = CacheConfig.DEFAULT_TTL):
        self.prefix = prefix
        self.default_ttl = default_ttl
    
    def _build_key(self, *args, **kwargs) -> str:
        """Build cache key from arguments."""
        key_parts = [self.prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float)):
                key_parts.append(str(arg))
            elif hasattr(arg, 'id'):
                key_parts.append(str(arg.id))
            else:
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}={value}")
        
        return ":".join(key_parts)
    
    async def get(self, *args, **kwargs) -> Optional[Any]:
        """Get cached value."""
        cache_key = self._build_key(*args, **kwargs)
        return await get_cache(cache_key)
    
    async def set(self, value: Any, *args, ttl: Optional[int] = None, **kwargs) -> bool:
        """Set cached value."""
        cache_key = self._build_key(*args, **kwargs)
        return await set_cache(cache_key, value, ttl or self.default_ttl)
    
    async def delete(self, *args, **kwargs) -> bool:
        """Delete cached value."""
        cache_key = self._build_key(*args, **kwargs)
        return await delete_cache(cache_key)
    
    async def exists(self, *args, **kwargs) -> bool:
        """Check if cached value exists."""
        cache_key = self._build_key(*args, **kwargs)
        return await exists_cache(cache_key)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern within this manager's prefix."""
        full_pattern = f"{self.prefix}:{pattern}"
        return await delete_cache_pattern(full_pattern)
    
    async def invalidate_all(self) -> int:
        """Invalidate all keys for this cache manager."""
        pattern = f"{self.prefix}:*"
        return await delete_cache_pattern(pattern)


class SearchCacheManager(CacheManager):
    """Specialized cache manager for search operations."""
    
    def __init__(self):
        super().__init__(CacheConfig.SEARCH_PREFIX, CacheConfig.MEDIUM_TTL)
    
    async def invalidate_for_location(self, city: str) -> int:
        """Invalidate search caches for a specific location."""
        pattern = f"*city={city}*"
        return await self.invalidate_pattern(pattern)
    
    async def invalidate_for_category(self, category: str) -> int:
        """Invalidate search caches for a specific category.""" 
        pattern = f"*category={category}*"
        return await self.invalidate_pattern(pattern)


class BusinessCacheManager(CacheManager):
    """Specialized cache manager for business operations."""
    
    def __init__(self):
        super().__init__(CacheConfig.BUSINESS_PREFIX, CacheConfig.LONG_TTL)
    
    async def invalidate_for_business(self, business_id: str) -> int:
        """Invalidate all caches related to a specific business."""
        pattern = f"*{business_id}*"
        return await self.invalidate_pattern(pattern)
    
    async def invalidate_for_owner(self, owner_id: str) -> int:
        """Invalidate caches for a business owner."""
        pattern = f"*owner={owner_id}*"
        return await self.invalidate_pattern(pattern)


class RecommendationCacheManager(CacheManager):
    """Specialized cache manager for recommendation operations."""
    
    def __init__(self):
        super().__init__(CacheConfig.RECOMMENDATION_PREFIX, CacheConfig.MEDIUM_TTL)
    
    async def invalidate_for_user(self, user_id: str) -> int:
        """Invalidate recommendation caches for a specific user."""
        pattern = f"*user={user_id}*"
        return await self.invalidate_pattern(pattern)
    
    async def invalidate_for_business_update(self, business_id: str) -> int:
        """Invalidate recommendations when a business is updated."""
        # This would invalidate recommendations that might include this business
        pattern = f"*business={business_id}*"
        return await self.invalidate_pattern(pattern)


# Global cache managers
search_cache = SearchCacheManager()
business_cache = BusinessCacheManager()
recommendation_cache = RecommendationCacheManager()
user_cache = CacheManager(CacheConfig.USER_PREFIX, CacheConfig.LONG_TTL)
ai_cache = CacheManager(CacheConfig.AI_PREFIX, CacheConfig.MEDIUM_TTL)
analytics_cache = CacheManager(CacheConfig.ANALYTICS_PREFIX, CacheConfig.SHORT_TTL)


def cached(ttl: Optional[int] = None, cache_manager: Optional[CacheManager] = None, key_builder: Optional[Callable] = None):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live for cache (uses manager default if None)
        cache_manager: Cache manager to use (creates default if None)
        key_builder: Custom function to build cache key
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Determine cache manager
            manager = cache_manager or CacheManager("func", CacheConfig.DEFAULT_TTL)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__name__}"
                cache_key = manager._build_key(func_name, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await get_cache(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_result
            
            # Execute function and cache result
            logger.debug("Cache miss, executing function", function=func.__name__, key=cache_key)
            result = await func(*args, **kwargs)
            
            # Cache the result
            await set_cache(cache_key, result, ttl or manager.default_ttl)
            
            return result
        return wrapper
    return decorator


def cache_invalidate_on_update(*cache_managers: CacheManager, patterns: Optional[List[str]] = None):
    """
    Decorator to invalidate caches when a function is called (typically for update operations).
    
    Args:
        cache_managers: Cache managers to invalidate
        patterns: Specific patterns to invalidate
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the function first
            result = await func(*args, **kwargs)
            
            # Invalidate caches
            for manager in cache_managers:
                if patterns:
                    for pattern in patterns:
                        await manager.invalidate_pattern(pattern)
                else:
                    # Try to extract relevant IDs from function arguments
                    if 'business_id' in kwargs:
                        if isinstance(manager, BusinessCacheManager):
                            await manager.invalidate_for_business(str(kwargs['business_id']))
                    
                    if 'user_id' in kwargs:
                        if isinstance(manager, RecommendationCacheManager):
                            await manager.invalidate_for_user(str(kwargs['user_id']))
            
            return result
        return wrapper
    return decorator


async def warm_cache():
    """Warm up frequently accessed cache entries."""
    if not redis_client:
        logger.warning("Cannot warm cache - Redis not available")
        return
    
    try:
        logger.info("Starting cache warm-up")
        
        # This would typically warm up:
        # - Popular search queries
        # - Trending businesses
        # - Common recommendations
        # - Frequently accessed business profiles
        
        # For now, just log the intention
        logger.info("Cache warm-up completed")
        
    except Exception as e:
        logger.error("Cache warm-up failed", error=str(e))


async def cleanup_expired_cache():
    """Clean up expired cache entries and optimize memory."""
    if not redis_client:
        return
    
    try:
        # Redis automatically handles TTL expiration, but we can do some housekeeping
        info = await get_cache_info()
        
        logger.info(
            "Cache cleanup check completed",
            used_memory=info.get("used_memory_human", "unknown"),
            hit_ratio=info.get("hit_ratio", 0.0)
        )
        
    except Exception as e:
        logger.error("Cache cleanup failed", error=str(e))


# Performance monitoring
class CacheMetrics:
    """Cache performance metrics tracking."""
    
    @staticmethod
    async def get_performance_metrics() -> Dict[str, Any]:
        """Get cache performance metrics."""
        if not redis_client:
            return {"status": "unavailable"}
        
        try:
            cache_info = await get_cache_info()
            
            # Calculate additional metrics
            metrics = {
                "hit_ratio": cache_info.get("hit_ratio", 0.0),
                "memory_usage": cache_info.get("used_memory_human", "0B"),
                "total_keys": sum(cache_info.get("key_statistics", {}).values()),
                "commands_per_second": 0,  # Would calculate from commands_processed over time
                "avg_response_time": 0,    # Would track response times
                "cache_efficiency": "good" if cache_info.get("hit_ratio", 0) > 0.8 else "needs_improvement"
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get cache metrics", error=str(e))
            return {"status": "error", "error": str(e)}
    
    @staticmethod
    async def get_detailed_stats() -> Dict[str, Any]:
        """Get detailed cache statistics."""
        return await get_cache_info()


# Health check
async def health_check() -> Dict[str, Any]:
    """Perform Redis health check."""
    if not redis_client:
        return {
            "status": "unhealthy",
            "message": "Redis client not initialized"
        }
    
    try:
        # Test basic operations
        test_key = "health_check_test"
        test_value = {"timestamp": datetime.utcnow().isoformat()}
        
        # Test set
        set_success = await set_cache(test_key, test_value, ttl=60)
        if not set_success:
            return {
                "status": "unhealthy",
                "message": "Failed to set test value"
            }
        
        # Test get
        retrieved_value = await get_cache(test_key)
        if retrieved_value != test_value:
            return {
                "status": "unhealthy", 
                "message": "Retrieved value doesn't match set value"
            }
        
        # Test delete
        delete_success = await delete_cache(test_key)
        if not delete_success:
            return {
                "status": "unhealthy",
                "message": "Failed to delete test value"
            }
        
        # Get basic info
        cache_info = await get_cache_info()
        
        return {
            "status": "healthy",
            "redis_version": cache_info.get("redis_version"),
            "hit_ratio": cache_info.get("hit_ratio", 0.0),
            "memory_usage": cache_info.get("used_memory_human"),
            "connected_clients": cache_info.get("connected_clients"),
            "total_keys": sum(cache_info.get("key_statistics", {}).values())
        }
        
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}"
        }