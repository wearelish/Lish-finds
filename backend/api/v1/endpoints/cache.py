"""
Cache management API endpoints for LishFind backend.

Provides cache monitoring, management, and optimization tools for administrators.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_admin_user
from database.connection import get_db_session
from database.redis import (
    get_cache_info,
    delete_cache_pattern,
    search_cache,
    business_cache,
    recommendation_cache,
    user_cache,
    ai_cache,
    analytics_cache,
    CacheMetrics,
    health_check,
    warm_cache,
    cleanup_expired_cache
)
from models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/cache", tags=["cache-management"])


class CacheStatsResponse(BaseModel):
    """Response schema for cache statistics."""
    
    status: str = Field(..., description="Cache system status")
    redis_version: Optional[str] = Field(None, description="Redis version")
    memory_usage: Optional[str] = Field(None, description="Memory usage")
    hit_ratio: float = Field(0.0, description="Cache hit ratio")
    total_keys: int = Field(0, description="Total number of cached keys")
    connected_clients: Optional[int] = Field(None, description="Connected Redis clients")
    
    # Key statistics by category
    key_statistics: Dict[str, int] = Field(default_factory=dict, description="Keys by category")
    
    # Performance metrics
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


class CacheInvalidationRequest(BaseModel):
    """Request schema for cache invalidation."""
    
    cache_type: str = Field(
        ...,
        description="Type of cache to invalidate",
        example="search"
    )
    
    pattern: Optional[str] = Field(
        None,
        description="Pattern to match for selective invalidation",
        example="*business_id=123*"
    )
    
    specific_keys: Optional[List[str]] = Field(
        None,
        description="Specific cache keys to invalidate"
    )


class CacheHealthResponse(BaseModel):
    """Response schema for cache health check."""
    
    status: str = Field(..., description="Health status: healthy/unhealthy")
    message: Optional[str] = Field(None, description="Status message")
    redis_version: Optional[str] = Field(None, description="Redis version")
    hit_ratio: Optional[float] = Field(None, description="Cache hit ratio")
    memory_usage: Optional[str] = Field(None, description="Memory usage")
    connected_clients: Optional[int] = Field(None, description="Connected clients")
    total_keys: Optional[int] = Field(None, description="Total cached keys")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")


@router.get(
    "/health",
    response_model=CacheHealthResponse,
    summary="Cache health check",
    description="Perform comprehensive cache system health check.",
)
async def cache_health_check() -> CacheHealthResponse:
    """Perform cache system health check."""
    
    try:
        health_result = await health_check()
        
        response = CacheHealthResponse(
            status=health_result["status"],
            message=health_result.get("message"),
            redis_version=health_result.get("redis_version"),
            hit_ratio=health_result.get("hit_ratio"),
            memory_usage=health_result.get("memory_usage"),
            connected_clients=health_result.get("connected_clients"),
            total_keys=health_result.get("total_keys")
        )
        
        logger.info(
            "Cache health check performed",
            status=response.status,
            hit_ratio=response.hit_ratio
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Cache health check failed",
            error=str(e),
            exc_info=True
        )
        
        return CacheHealthResponse(
            status="error",
            message=f"Health check failed: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="Get cache statistics",
    description="Get comprehensive cache statistics and performance metrics (admin only).",
)
async def get_cache_statistics(
    current_user: User = Depends(get_current_admin_user)
) -> CacheStatsResponse:
    """Get cache statistics and performance metrics."""
    
    try:
        # Get basic cache info
        cache_info = await get_cache_info()
        
        # Get performance metrics
        performance_metrics = await CacheMetrics.get_performance_metrics()
        
        response = CacheStatsResponse(
            status=cache_info.get("status", "unknown"),
            redis_version=cache_info.get("redis_version"),
            memory_usage=cache_info.get("used_memory_human"),
            hit_ratio=cache_info.get("hit_ratio", 0.0),
            total_keys=sum(cache_info.get("key_statistics", {}).values()),
            connected_clients=cache_info.get("connected_clients"),
            key_statistics=cache_info.get("key_statistics", {}),
            performance_metrics=performance_metrics
        )
        
        logger.info(
            "Cache statistics retrieved",
            admin_user_id=current_user.id,
            status=response.status,
            total_keys=response.total_keys,
            hit_ratio=response.hit_ratio
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get cache statistics",
            admin_user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}"
        )


@router.get(
    "/detailed-stats",
    summary="Get detailed cache statistics",
    description="Get detailed cache statistics with memory and performance data (admin only).",
)
async def get_detailed_cache_statistics(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get detailed cache statistics."""
    
    try:
        detailed_stats = await CacheMetrics.get_detailed_stats()
        
        logger.info(
            "Detailed cache statistics retrieved",
            admin_user_id=current_user.id
        )
        
        return detailed_stats
        
    except Exception as e:
        logger.error(
            "Failed to get detailed cache statistics",
            admin_user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get detailed statistics: {str(e)}"
        )


@router.post(
    "/invalidate",
    summary="Invalidate cache",
    description="Invalidate cache entries by pattern or specific keys (admin only).",
)
async def invalidate_cache(
    request: CacheInvalidationRequest,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Invalidate cache entries."""
    
    try:
        invalidated_count = 0
        
        # Get appropriate cache manager
        cache_managers = {
            "search": search_cache,
            "business": business_cache,
            "recommendation": recommendation_cache,
            "user": user_cache,
            "ai": ai_cache,
            "analytics": analytics_cache
        }
        
        cache_manager = cache_managers.get(request.cache_type)
        if not cache_manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cache type: {request.cache_type}. Available: {list(cache_managers.keys())}"
            )
        
        # Invalidate by pattern
        if request.pattern:
            invalidated_count = await cache_manager.invalidate_pattern(request.pattern)
        
        # Invalidate specific keys
        elif request.specific_keys:
            for key in request.specific_keys:
                success = await cache_manager.delete(key)
                if success:
                    invalidated_count += 1
        
        # Invalidate all for this cache type
        else:
            invalidated_count = await cache_manager.invalidate_all()
        
        logger.info(
            "Cache invalidated",
            admin_user_id=current_user.id,
            cache_type=request.cache_type,
            pattern=request.pattern,
            specific_keys_count=len(request.specific_keys) if request.specific_keys else 0,
            invalidated_count=invalidated_count
        )
        
        return {
            "message": f"Successfully invalidated {invalidated_count} cache entries",
            "cache_type": request.cache_type,
            "invalidated_count": invalidated_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to invalidate cache",
            admin_user_id=current_user.id,
            cache_type=request.cache_type,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.post(
    "/warm-up",
    summary="Warm up cache",
    description="Warm up frequently accessed cache entries (admin only).",
)
async def warm_up_cache(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Warm up cache with frequently accessed data."""
    
    try:
        await warm_cache()
        
        logger.info(
            "Cache warm-up initiated",
            admin_user_id=current_user.id
        )
        
        return {
            "message": "Cache warm-up completed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Cache warm-up failed",
            admin_user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache warm-up failed: {str(e)}"
        )


@router.post(
    "/cleanup",
    summary="Clean up cache",
    description="Clean up expired cache entries and optimize memory (admin only).",
)
async def cleanup_cache(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Clean up expired cache entries."""
    
    try:
        await cleanup_expired_cache()
        
        logger.info(
            "Cache cleanup initiated",
            admin_user_id=current_user.id
        )
        
        return {
            "message": "Cache cleanup completed successfully"
        }
        
    except Exception as e:
        logger.error(
            "Cache cleanup failed", 
            admin_user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache cleanup failed: {str(e)}"
        )


@router.get(
    "/performance",
    summary="Get cache performance metrics",
    description="Get real-time cache performance metrics (admin only).",
)
async def get_cache_performance_metrics(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get cache performance metrics."""
    
    try:
        performance_metrics = await CacheMetrics.get_performance_metrics()
        
        logger.debug(
            "Cache performance metrics retrieved",
            admin_user_id=current_user.id
        )
        
        return performance_metrics
        
    except Exception as e:
        logger.error(
            "Failed to get cache performance metrics",
            admin_user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get(
    "/keys/{cache_type}",
    summary="List cache keys",
    description="List cache keys for a specific cache type (admin only).",
)
async def list_cache_keys(
    cache_type: str,
    pattern: str = Query("*", description="Pattern to match cache keys"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of keys to return"),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """List cache keys for a specific cache type."""
    
    try:
        # Map cache type to prefix
        cache_prefixes = {
            "search": "search:",
            "business": "business:",
            "recommendation": "rec:",
            "user": "user:",
            "ai": "ai:",
            "analytics": "analytics:"
        }
        
        if cache_type not in cache_prefixes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cache type: {cache_type}. Available: {list(cache_prefixes.keys())}"
            )
        
        # Build full pattern
        full_pattern = f"{cache_prefixes[cache_type]}{pattern}"
        
        # Get keys (Redis KEYS command - use carefully in production)
        from database.redis import get_cache_pattern
        keys = await get_cache_pattern(full_pattern)
        
        # Limit results
        limited_keys = keys[:limit] if len(keys) > limit else keys
        
        logger.info(
            "Cache keys listed",
            admin_user_id=current_user.id,
            cache_type=cache_type,
            pattern=pattern,
            total_found=len(keys),
            returned=len(limited_keys)
        )
        
        return {
            "cache_type": cache_type,
            "pattern": pattern,
            "keys": limited_keys,
            "total_found": len(keys),
            "returned": len(limited_keys),
            "truncated": len(keys) > limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to list cache keys",
            admin_user_id=current_user.id,
            cache_type=cache_type,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list cache keys: {str(e)}"
        )