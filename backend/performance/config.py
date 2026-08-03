"""
Performance configuration and tuning parameters for LishFind.

Centralized configuration for cache settings, optimization parameters, and performance thresholds.
"""

from typing import Dict, Any
from dataclasses import dataclass
from core.config import settings


@dataclass
class CacheConfig:
    """Cache configuration parameters."""
    
    # Default TTL values (in seconds)
    SEARCH_RESULTS_TTL: int = 1800      # 30 minutes
    BUSINESS_DETAILS_TTL: int = 3600    # 1 hour
    USER_DATA_TTL: int = 900            # 15 minutes
    RECOMMENDATIONS_TTL: int = 2400     # 40 minutes
    RANKINGS_TTL: int = 1800            # 30 minutes
    
    # Memory cache settings
    MEMORY_CACHE_SIZE: int = 1000       # Max items in memory
    MEMORY_CACHE_TTL: int = 300         # 5 minutes max in memory
    
    # Cache warming settings
    WARM_CACHE_ON_STARTUP: bool = True
    POPULAR_SEARCHES_TO_WARM: int = 10
    
    # Cache invalidation
    AUTO_INVALIDATE_STALE: bool = True
    STALE_THRESHOLD_HOURS: int = 24


@dataclass
class DatabaseConfig:
    """Database performance configuration."""
    
    # Connection pool settings
    POOL_SIZE: int = settings.DATABASE_POOL_SIZE
    MAX_OVERFLOW: int = settings.DATABASE_MAX_OVERFLOW
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 3600
    
    # Query optimization
    SLOW_QUERY_THRESHOLD: float = 1.0   # Log queries > 1 second
    QUERY_CACHE_SIZE: int = 500
    EXPLAIN_SLOW_QUERIES: bool = True
    
    # Batch processing
    DEFAULT_BATCH_SIZE: int = 100
    MAX_BATCH_SIZE: int = 1000
    BATCH_CONCURRENCY: int = 5


@dataclass
class CompressionConfig:
    """Response compression configuration."""
    
    # Compression settings
    ENABLED: bool = settings.GZIP_COMPRESSION
    MIN_SIZE: int = 1024                # Don't compress responses < 1KB
    COMPRESSION_LEVEL: int = 6          # Balance between speed and compression
    
    # Content types to compress
    COMPRESSIBLE_TYPES: set = None
    
    def __post_init__(self):
        if self.COMPRESSIBLE_TYPES is None:
            self.COMPRESSIBLE_TYPES = {
                "application/json",
                "application/javascript", 
                "text/html",
                "text/css",
                "text/plain",
                "text/xml",
                "application/xml",
                "image/svg+xml"
            }


@dataclass
class ConcurrencyConfig:
    """Concurrency and async processing configuration."""
    
    # Thread pool settings
    MAX_THREAD_WORKERS: int = min(4, (settings.WORKER_PROCESSES or 1) * 2)
    
    # Async processing limits
    MAX_CONCURRENT_REQUESTS: int = settings.MAX_CONCURRENT_REQUESTS
    DEFAULT_SEMAPHORE_LIMIT: int = 10
    
    # Background task settings
    MAX_BACKGROUND_TASKS: int = 50
    BACKGROUND_TASK_TIMEOUT: int = 300  # 5 minutes


@dataclass
class OptimizationConfig:
    """General optimization configuration."""
    
    # Performance thresholds
    SLOW_RESPONSE_THRESHOLD: float = 2.0       # Log responses > 2 seconds
    HIGH_MEMORY_THRESHOLD: float = 85.0        # % memory usage threshold
    HIGH_CPU_THRESHOLD: float = 80.0           # % CPU usage threshold
    
    # Optimization intervals
    AUTO_OPTIMIZE_INTERVAL: int = 3600         # Run optimizations every hour
    GC_OPTIMIZE_INTERVAL: int = 1800           # Garbage collection every 30 min
    CACHE_CLEANUP_INTERVAL: int = 900          # Cache cleanup every 15 min
    
    # Feature flags
    ENABLE_QUERY_PROFILING: bool = True
    ENABLE_MEMORY_PROFILING: bool = settings.DEBUG
    ENABLE_AUTO_OPTIMIZATION: bool = True


@dataclass
class BandwidthConfig:
    """Bandwidth optimization configuration."""
    
    # Connection type response limits
    SLOW_CONNECTION_MAX_RESULTS: int = 10
    MEDIUM_CONNECTION_MAX_RESULTS: int = 20
    MOBILE_CONNECTION_MAX_RESULTS: int = 15
    FAST_CONNECTION_MAX_RESULTS: int = 50
    
    # Response optimization
    LIGHTWEIGHT_RESPONSE_FIELDS: set = None
    EXCLUDE_ON_SLOW_CONNECTION: list = None
    
    def __post_init__(self):
        if self.LIGHTWEIGHT_RESPONSE_FIELDS is None:
            self.LIGHTWEIGHT_RESPONSE_FIELDS = {
                'id', 'name', 'category', 'rating', 'latitude', 
                'longitude', 'address', 'phone', 'is_open'
            }
        
        if self.EXCLUDE_ON_SLOW_CONNECTION is None:
            self.EXCLUDE_ON_SLOW_CONNECTION = [
                'description', 'detailed_categories', 'attributes',
                'photos', 'reviews', 'hours_detailed'
            ]


class PerformanceConfig:
    """Main performance configuration class."""
    
    def __init__(self):
        self.cache = CacheConfig()
        self.database = DatabaseConfig()
        self.compression = CompressionConfig()
        self.concurrency = ConcurrencyConfig()
        self.optimization = OptimizationConfig()
        self.bandwidth = BandwidthConfig()
    
    def get_environment_specific_config(self) -> Dict[str, Any]:
        """Get configuration optimized for current environment."""
        
        if settings.ENVIRONMENT == "production":
            return self._get_production_config()
        elif settings.ENVIRONMENT == "staging":
            return self._get_staging_config()
        else:
            return self._get_development_config()
    
    def _get_production_config(self) -> Dict[str, Any]:
        """Production-optimized configuration."""
        return {
            "cache": {
                "ttl_multiplier": 1.5,          # Longer cache times
                "memory_cache_size": 2000,      # Larger memory cache
                "aggressive_caching": True,
            },
            "database": {
                "pool_size": max(20, self.database.POOL_SIZE),
                "slow_query_threshold": 0.5,   # Stricter threshold
                "query_timeout": 30,
            },
            "compression": {
                "compression_level": 9,         # Maximum compression
                "min_size": 512,               # Compress smaller responses
            },
            "concurrency": {
                "max_concurrent": min(100, self.concurrency.MAX_CONCURRENT_REQUESTS),
                "semaphore_limit": 20,
            }
        }
    
    def _get_staging_config(self) -> Dict[str, Any]:
        """Staging configuration (similar to production but more forgiving)."""
        return {
            "cache": {
                "ttl_multiplier": 1.0,
                "memory_cache_size": 1000,
                "aggressive_caching": False,
            },
            "database": {
                "pool_size": max(10, self.database.POOL_SIZE // 2),
                "slow_query_threshold": 1.0,
                "query_timeout": 60,
            },
            "compression": {
                "compression_level": 6,
                "min_size": 1024,
            },
            "concurrency": {
                "max_concurrent": min(50, self.concurrency.MAX_CONCURRENT_REQUESTS),
                "semaphore_limit": 10,
            }
        }
    
    def _get_development_config(self) -> Dict[str, Any]:
        """Development configuration (optimized for debugging)."""
        return {
            "cache": {
                "ttl_multiplier": 0.5,          # Shorter cache times for testing
                "memory_cache_size": 100,       # Smaller cache for debugging
                "aggressive_caching": False,
            },
            "database": {
                "pool_size": 5,
                "slow_query_threshold": 2.0,    # More lenient for debugging
                "query_timeout": 120,
            },
            "compression": {
                "compression_level": 1,         # Fast compression for dev
                "min_size": 2048,              # Less aggressive compression
            },
            "concurrency": {
                "max_concurrent": 10,
                "semaphore_limit": 5,
            }
        }
    
    def apply_runtime_optimizations(self):
        """Apply runtime optimizations based on current system state."""
        
        # This could dynamically adjust configuration based on:
        # - Current system load
        # - Memory usage
        # - Database performance
        # - Cache hit rates
        
        pass  # Implementation would go here
    
    def get_cache_ttl(self, cache_type: str) -> int:
        """Get appropriate TTL for cache type based on environment."""
        
        base_ttls = {
            "search": self.cache.SEARCH_RESULTS_TTL,
            "business": self.cache.BUSINESS_DETAILS_TTL,
            "user": self.cache.USER_DATA_TTL,
            "recommendations": self.cache.RECOMMENDATIONS_TTL,
            "rankings": self.cache.RANKINGS_TTL,
        }
        
        base_ttl = base_ttls.get(cache_type, 3600)  # Default 1 hour
        
        # Apply environment-specific multiplier
        env_config = self.get_environment_specific_config()
        multiplier = env_config.get("cache", {}).get("ttl_multiplier", 1.0)
        
        return int(base_ttl * multiplier)
    
    def should_use_aggressive_caching(self) -> bool:
        """Determine if aggressive caching should be used."""
        env_config = self.get_environment_specific_config()
        return env_config.get("cache", {}).get("aggressive_caching", False)


# Global performance configuration instance
perf_config = PerformanceConfig()


# Utility functions
def get_cache_ttl(cache_type: str) -> int:
    """Get TTL for specific cache type."""
    return perf_config.get_cache_ttl(cache_type)


def get_batch_size(operation_type: str = "default") -> int:
    """Get optimal batch size for operation type."""
    
    batch_sizes = {
        "search": 50,
        "database_insert": perf_config.database.DEFAULT_BATCH_SIZE,
        "api_request": 20,
        "cache_warm": 25,
        "default": perf_config.database.DEFAULT_BATCH_SIZE
    }
    
    return batch_sizes.get(operation_type, batch_sizes["default"])


def get_compression_level() -> int:
    """Get compression level based on environment."""
    env_config = perf_config.get_environment_specific_config()
    return env_config.get("compression", {}).get("compression_level", 6)


def should_enable_profiling() -> bool:
    """Determine if performance profiling should be enabled."""
    return (
        perf_config.optimization.ENABLE_QUERY_PROFILING and 
        (settings.DEBUG or settings.ENVIRONMENT != "production")
    )