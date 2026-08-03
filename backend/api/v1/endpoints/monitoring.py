"""
Monitoring and metrics endpoints.

Provides health checks, metrics, and system information for monitoring systems.
"""

from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import PlainTextResponse

from monitoring.metrics import (
    metrics_collector, 
    health_checker,
    _request_metrics,
    _metrics_store
)
from core.config import settings
from api.auth.dependencies import get_current_user_optional
from models.user import User

router = APIRouter()


@router.get("/health", 
           summary="Application Health Check",
           description="Comprehensive health check for load balancers and monitoring systems")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns detailed health information about all application components.
    Used by load balancers, container orchestrators, and monitoring systems.
    """
    health_data = await health_checker.get_overall_health()
    
    # Set appropriate HTTP status code
    status_code = 200
    if health_data["status"] == "degraded":
        status_code = 200  # Still serving traffic
    elif health_data["status"] == "unhealthy":
        status_code = 503  # Service unavailable
    
    return Response(
        content=health_data,
        status_code=status_code,
        media_type="application/json"
    )


@router.get("/health/live",
           summary="Liveness Probe", 
           description="Basic liveness check for Kubernetes")
async def liveness_check():
    """
    Simple liveness check for Kubernetes liveness probes.
    Returns 200 if the application is running.
    """
    return {"status": "alive", "timestamp": health_checker.get_overall_health()["timestamp"]}


@router.get("/health/ready",
           summary="Readiness Probe",
           description="Readiness check for Kubernetes readiness probes")
async def readiness_check():
    """
    Readiness check for Kubernetes readiness probes.
    Returns 200 if the application is ready to serve traffic.
    """
    health_data = await health_checker.get_overall_health()
    
    # Consider ready if not completely unhealthy
    if health_data["status"] in ["healthy", "degraded"]:
        return {"status": "ready", "health": health_data["status"]}
    else:
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics",
           summary="Application Metrics",
           description="Prometheus-compatible metrics endpoint")
async def get_metrics():
    """
    Get application metrics in Prometheus format.
    
    Includes HTTP request metrics, system metrics, and custom application metrics.
    """
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics are disabled")
    
    # Collect all metrics
    request_metrics = metrics_collector.get_request_metrics()
    system_metrics = metrics_collector.get_system_metrics()
    app_metrics = metrics_collector.get_application_metrics()
    
    # Convert to Prometheus format
    prometheus_output = []
    
    # HTTP metrics
    prometheus_output.extend([
        f"# HELP http_requests_total Total number of HTTP requests",
        f"# TYPE http_requests_total counter",
        f"http_requests_total {request_metrics['total_requests']}",
        "",
        f"# HELP http_requests_active Currently active HTTP requests", 
        f"# TYPE http_requests_active gauge",
        f"http_requests_active {request_metrics['active_requests']}",
        "",
        f"# HELP http_request_errors_total Total number of HTTP request errors",
        f"# TYPE http_request_errors_total counter", 
        f"http_request_errors_total {request_metrics['error_count']}",
        ""
    ])
    
    # Response time metrics
    if "response_time" in request_metrics:
        rt = request_metrics["response_time"]
        prometheus_output.extend([
            f"# HELP http_request_duration_ms HTTP request duration in milliseconds",
            f"# TYPE http_request_duration_ms histogram",
            f"http_request_duration_ms_sum {rt['avg'] * request_metrics['total_requests']}",
            f"http_request_duration_ms_count {request_metrics['total_requests']}",
            ""
        ])
    
    # System metrics
    if system_metrics:
        prometheus_output.extend([
            f"# HELP system_cpu_usage_percent CPU usage percentage",
            f"# TYPE system_cpu_usage_percent gauge",
            f"system_cpu_usage_percent {system_metrics.get('cpu', {}).get('usage_percent', 0)}",
            "",
            f"# HELP system_memory_usage_percent Memory usage percentage", 
            f"# TYPE system_memory_usage_percent gauge",
            f"system_memory_usage_percent {system_metrics.get('memory', {}).get('usage_percent', 0)}",
            "",
            f"# HELP system_disk_usage_percent Disk usage percentage",
            f"# TYPE system_disk_usage_percent gauge", 
            f"system_disk_usage_percent {system_metrics.get('disk', {}).get('usage_percent', 0)}",
            ""
        ])
    
    # Application uptime
    prometheus_output.extend([
        f"# HELP app_uptime_seconds Application uptime in seconds",
        f"# TYPE app_uptime_seconds counter",
        f"app_uptime_seconds {app_metrics['uptime_seconds']}",
        ""
    ])
    
    return PlainTextResponse("\n".join(prometheus_output))


@router.get("/metrics/json",
           summary="JSON Metrics",
           description="Get metrics in JSON format for dashboards")
async def get_metrics_json():
    """
    Get comprehensive metrics in JSON format.
    
    Useful for custom dashboards and monitoring integrations.
    """
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics are disabled")
    
    return {
        "request_metrics": metrics_collector.get_request_metrics(),
        "system_metrics": metrics_collector.get_system_metrics(),
        "application_metrics": metrics_collector.get_application_metrics(),
        "timestamp": health_checker.get_overall_health()["timestamp"]
    }


@router.get("/status",
           summary="Service Status",
           description="Human-readable service status page")
async def get_status():
    """
    Get service status information for status pages and dashboards.
    """
    health_data = await health_checker.get_overall_health()
    request_metrics = metrics_collector.get_request_metrics()
    system_metrics = metrics_collector.get_system_metrics()
    app_metrics = metrics_collector.get_application_metrics()
    
    return {
        "service": {
            "name": "LishFind Backend",
            "version": app_metrics["version"],
            "environment": app_metrics["environment"],
            "uptime_seconds": app_metrics["uptime_seconds"],
            "status": health_data["status"]
        },
        "health": health_data,
        "performance": {
            "total_requests": request_metrics["total_requests"],
            "active_requests": request_metrics["active_requests"], 
            "error_rate": request_metrics["error_rate"],
            "avg_response_time": request_metrics.get("response_time", {}).get("avg")
        },
        "resources": {
            "cpu_usage": system_metrics.get("cpu", {}).get("usage_percent"),
            "memory_usage": system_metrics.get("memory", {}).get("usage_percent"),
            "disk_usage": system_metrics.get("disk", {}).get("usage_percent")
        }
    }


@router.get("/debug",
           summary="Debug Information", 
           description="Debug information for troubleshooting (admin only)")
async def get_debug_info(current_user: User = Depends(get_current_user_optional)):
    """
    Get debug information for troubleshooting.
    
    Only available in development or for admin users.
    """
    # Only allow in development or for admin users
    if not settings.DEBUG and (not current_user or current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "metrics_enabled": settings.METRICS_ENABLED,
        "request_metrics": dict(_request_metrics),
        "custom_metrics": dict(_metrics_store),
        "configuration": {
            "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "sqlite",
            "redis_enabled": bool(settings.REDIS_URL),
            "ai_provider": settings.AI_PROVIDER,
            "maps_provider": settings.MAPS_PROVIDER,
            "log_level": settings.LOG_LEVEL,
        }
    }


@router.get("/performance",
           summary="Performance Metrics",
           description="Get detailed performance metrics and optimization recommendations")
async def get_performance_metrics(current_user: User = Depends(get_current_user_optional)):
    """
    Get comprehensive performance metrics including cache stats, 
    database performance, and system resources.
    """
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Performance metrics are disabled")
    
    # Only allow in development or for admin users
    if not settings.DEBUG and (not current_user or current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    from performance.cache import cache_manager
    from performance.optimization import (
        ConnectionPoolOptimizer, 
        MemoryOptimizer,
        optimize_database_queries
    )
    
    # Gather performance metrics
    performance_data = {
        "cache_stats": await cache_manager.get_stats(),
        "database_pool": await ConnectionPoolOptimizer.get_pool_stats(),
        "memory_usage": MemoryOptimizer.get_memory_usage(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Add recommendations
    recommendations = []
    
    # Cache recommendations
    cache_stats = performance_data["cache_stats"]
    if cache_stats.get("hit_rate", 0) < 50:
        recommendations.append("Low cache hit rate - consider warming cache or adjusting TTL")
    
    # Database recommendations
    db_pool = performance_data["database_pool"]
    if "recommendations" in db_pool:
        recommendations.extend(db_pool["recommendations"])
    
    # Memory recommendations
    memory_stats = performance_data["memory_usage"]
    if "recommendations" in memory_stats:
        recommendations.extend(memory_stats["recommendations"])
    
    performance_data["recommendations"] = recommendations
    
    return performance_data


@router.post("/metrics/reset",
            summary="Reset Metrics",
            description="Reset metrics counters (admin only)")
async def reset_metrics(current_user: User = Depends(get_current_user_optional)):
    """
    Reset metrics counters.
    
    Only available for admin users in non-production environments.
    """
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=403, detail="Not allowed in production")
    
    # Reset metrics
    _request_metrics.update({
        "total_requests": 0,
        "requests_by_method": {},
        "requests_by_endpoint": {},
        "requests_by_status": {},
        "response_times": [],
        "active_requests": 0,
        "error_count": 0,
    })
    
    _metrics_store.clear()
    
    return {"message": "Metrics reset successfully"}


@router.post("/cache/clear",
            summary="Clear Application Cache",
            description="Clear application cache (admin only)")
async def clear_cache(
    pattern: str = None,
    current_user: User = Depends(get_current_user_optional)
):
    """
    Clear application cache entries.
    
    Optionally specify a pattern to clear specific cache entries.
    """
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from performance.cache import cache_manager
    
    if pattern:
        cleared = await cache_manager.clear_pattern(pattern)
        return {"message": f"Cache cleared for pattern '{pattern}'", "cleared_count": cleared}
    else:
        # Clear all cache (not implemented to prevent accidental full cache clear)
        raise HTTPException(status_code=400, detail="Pattern required for cache clearing")


@router.post("/optimization/run",
            summary="Run Performance Optimizations",
            description="Run database and performance optimizations (admin only)")
async def run_optimizations(current_user: User = Depends(get_current_user_optional)):
    """
    Run performance optimization tasks.
    
    Includes database optimization, cache warming, and resource cleanup.
    """
    if not current_user or current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from performance.optimization import optimize_database_queries
    from performance.cache import warm_popular_searches
    
    try:
        # Run optimizations
        await optimize_database_queries()
        await warm_popular_searches()
        
        return {
            "message": "Performance optimizations completed successfully",
            "optimizations_run": [
                "Database query analysis",
                "Cache warming for popular searches",
                "Connection pool optimization"
            ]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")