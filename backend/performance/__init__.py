"""
Performance optimization modules for LishFind.

Provides caching, compression, optimization utilities, and performance monitoring.
"""

from .cache import (
    cache_manager,
    cached,
    query_cache,
    request_cache,
    cache_search_results,
    get_cached_search_results,
    cache_business_data,
    get_cached_business_data,
    invalidate_business_cache,
    warm_popular_searches,
    cache_middleware
)

from .optimization import (
    batch_processor,
    async_processor,
    BatchProcessor,
    QueryOptimizer,
    ConnectionPoolOptimizer,
    AsyncProcessor,
    MemoryOptimizer,
    optimize_async,
    cpu_bound,
    measure_performance,
    optimize_database_queries,
    cleanup_resources
)

from .compression import (
    CompressionMiddleware,
    ResponseOptimizer,
    BandwidthOptimizer,
    create_optimized_json_response,
    create_paginated_response,
    compress_string,
    decompress_string,
    get_compression_ratio
)

__all__ = [
    # Cache
    "cache_manager",
    "cached",
    "query_cache", 
    "request_cache",
    "cache_search_results",
    "get_cached_search_results",
    "cache_business_data",
    "get_cached_business_data",
    "invalidate_business_cache",
    "warm_popular_searches",
    "cache_middleware",
    
    # Optimization
    "batch_processor",
    "async_processor",
    "BatchProcessor",
    "QueryOptimizer",
    "ConnectionPoolOptimizer",
    "AsyncProcessor",
    "MemoryOptimizer",
    "optimize_async",
    "cpu_bound",
    "measure_performance",
    "optimize_database_queries",
    "cleanup_resources",
    
    # Compression
    "CompressionMiddleware",
    "ResponseOptimizer",
    "BandwidthOptimizer",
    "create_optimized_json_response",
    "create_paginated_response",
    "compress_string",
    "decompress_string",
    "get_compression_ratio",
]