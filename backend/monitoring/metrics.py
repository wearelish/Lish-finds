"""
Application metrics collection and monitoring.

Provides Prometheus-compatible metrics and health monitoring.
"""

import time
import psutil
import asyncio
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from fastapi import Request, Response

from core.config import settings
from database.connection import health_check as db_health_check
from database.redis import health_check as redis_health_check

logger = structlog.get_logger(__name__)

# Metrics storage (use Redis or external metrics store in production clusters)
_metrics_store: Dict[str, Any] = defaultdict(lambda: {
    "count": 0,
    "sum": 0.0,
    "min": float('inf'),
    "max": 0.0,
    "histogram": defaultdict(int),
    "recent_values": deque(maxlen=100)
})

# Request tracking
_request_metrics = {
    "total_requests": 0,
    "requests_by_method": defaultdict(int),
    "requests_by_endpoint": defaultdict(int),
    "requests_by_status": defaultdict(int),
    "response_times": deque(maxlen=1000),
    "active_requests": 0,
    "error_count": 0,
}

# System metrics cache
_system_metrics_cache = {
    "last_update": 0,
    "data": {}
}


@dataclass
class HealthStatus:
    """Health check status."""
    service: str
    status: str  # healthy, degraded, unhealthy
    checks: Dict[str, Any]
    response_time_ms: float
    message: Optional[str] = None


class MetricsCollector:
    """Collect and manage application metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.enabled = settings.METRICS_ENABLED
    
    def record_request(self, method: str, endpoint: str, status_code: int, 
                      duration_ms: float) -> None:
        """Record HTTP request metrics."""
        if not self.enabled:
            return
        
        _request_metrics["total_requests"] += 1
        _request_metrics["requests_by_method"][method] += 1
        _request_metrics["requests_by_endpoint"][endpoint] += 1
        _request_metrics["requests_by_status"][status_code] += 1
        _request_metrics["response_times"].append(duration_ms)
        
        if status_code >= 400:
            _request_metrics["error_count"] += 1
        
        # Record in histogram buckets
        self.record_histogram("http_request_duration_ms", duration_ms)
    
    def record_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None) -> None:
        """Record counter metric."""
        if not self.enabled:
            return
        
        metric_key = self._build_metric_key(name, tags)
        _metrics_store[metric_key]["count"] += value
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record gauge metric."""
        if not self.enabled:
            return
        
        metric_key = self._build_metric_key(name, tags)
        metric = _metrics_store[metric_key]
        metric["count"] = value
        metric["recent_values"].append(value)
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record histogram metric."""
        if not self.enabled:
            return
        
        metric_key = self._build_metric_key(name, tags)
        metric = _metrics_store[metric_key]
        
        metric["count"] += 1
        metric["sum"] += value
        metric["min"] = min(metric["min"], value)
        metric["max"] = max(metric["max"], value)
        metric["recent_values"].append(value)
        
        # Histogram buckets
        buckets = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
        for bucket in buckets:
            if value <= bucket:
                metric["histogram"][bucket] += 1
    
    def record_timing(self, name: str, start_time: float, tags: Dict[str, str] = None) -> None:
        """Record timing metric from start time."""
        duration_ms = (time.time() - start_time) * 1000
        self.record_histogram(name, duration_ms, tags)
    
    def increment_active_requests(self) -> None:
        """Increment active request counter."""
        _request_metrics["active_requests"] += 1
    
    def decrement_active_requests(self) -> None:
        """Decrement active request counter."""
        _request_metrics["active_requests"] = max(0, _request_metrics["active_requests"] - 1)
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """Get HTTP request metrics."""
        response_times = list(_request_metrics["response_times"])
        
        metrics = {
            "total_requests": _request_metrics["total_requests"],
            "active_requests": _request_metrics["active_requests"],
            "error_count": _request_metrics["error_count"],
            "error_rate": (
                _request_metrics["error_count"] / max(_request_metrics["total_requests"], 1)
            ) * 100,
            "requests_by_method": dict(_request_metrics["requests_by_method"]),
            "requests_by_status": dict(_request_metrics["requests_by_status"]),
        }
        
        if response_times:
            response_times.sort()
            count = len(response_times)
            metrics["response_time"] = {
                "avg": sum(response_times) / count,
                "min": min(response_times),
                "max": max(response_times),
                "p50": response_times[int(count * 0.5)],
                "p95": response_times[int(count * 0.95)],
                "p99": response_times[int(count * 0.99)]
            }
        
        return metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource metrics with caching."""
        now = time.time()
        
        # Cache system metrics for 10 seconds to avoid expensive calls
        if now - _system_metrics_cache["last_update"] < 10:
            return _system_metrics_cache["data"]
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            
            # Disk metrics (for main disk)
            disk = psutil.disk_usage('/')
            
            # Network metrics (sum of all interfaces)
            network = psutil.net_io_counters()
            
            metrics = {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                },
                "memory": {
                    "total_bytes": memory.total,
                    "available_bytes": memory.available,
                    "used_bytes": memory.used,
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_bytes": disk.total,
                    "used_bytes": disk.used,
                    "free_bytes": disk.free,
                    "usage_percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                }
            }
            
            # Cache the results
            _system_metrics_cache["last_update"] = now
            _system_metrics_cache["data"] = metrics
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect system metrics", error=str(e))
            return {}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics."""
        uptime_seconds = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime_seconds,
            "environment": settings.ENVIRONMENT,
            "version": getattr(settings, 'VERSION', '1.0.0'),
            "custom_metrics": {
                key: {
                    "count": metric["count"],
                    "sum": metric["sum"] if metric["sum"] != 0 else None,
                    "min": metric["min"] if metric["min"] != float('inf') else None,
                    "max": metric["max"] if metric["max"] != 0 else None,
                    "avg": (metric["sum"] / metric["count"]) if metric["count"] > 0 else None
                }
                for key, metric in _metrics_store.items()
                if metric["count"] > 0
            }
        }
    
    def _build_metric_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Build metric key with tags."""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name},{tag_str}"


class HealthChecker:
    """Comprehensive health checking system."""
    
    def __init__(self):
        self.checks = {}
        self.last_check = {}
        self.check_interval = settings.HEALTH_CHECK_INTERVAL
    
    async def check_database(self) -> HealthStatus:
        """Check database health."""
        start_time = time.time()
        
        try:
            result = await db_health_check()
            response_time = (time.time() - start_time) * 1000
            
            if result["status"] == "healthy":
                return HealthStatus(
                    service="database",
                    status="healthy",
                    checks=result,
                    response_time_ms=response_time
                )
            else:
                return HealthStatus(
                    service="database",
                    status="unhealthy",
                    checks=result,
                    response_time_ms=response_time,
                    message=result.get("error")
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="database",
                status="unhealthy",
                checks={"error": str(e)},
                response_time_ms=response_time,
                message=str(e)
            )
    
    async def check_redis(self) -> HealthStatus:
        """Check Redis health."""
        start_time = time.time()
        
        try:
            result = await redis_health_check()
            response_time = (time.time() - start_time) * 1000
            
            status = "healthy" if result["status"] in ["healthy", "disabled"] else "unhealthy"
            
            return HealthStatus(
                service="redis",
                status=status,
                checks=result,
                response_time_ms=response_time
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="redis",
                status="unhealthy",
                checks={"error": str(e)},
                response_time_ms=response_time,
                message=str(e)
            )
    
    def check_system_resources(self) -> HealthStatus:
        """Check system resource health."""
        start_time = time.time()
        
        try:
            metrics = metrics_collector.get_system_metrics()
            
            issues = []
            status = "healthy"
            
            # Check memory usage
            if metrics.get("memory", {}).get("usage_percent", 0) > 90:
                issues.append("High memory usage (>90%)")
                status = "degraded"
            
            # Check disk usage
            if metrics.get("disk", {}).get("usage_percent", 0) > 85:
                issues.append("High disk usage (>85%)")
                status = "degraded"
            
            # Check CPU usage (this is instantaneous, so might not be reliable)
            cpu_usage = metrics.get("cpu", {}).get("usage_percent", 0)
            if cpu_usage > 95:
                issues.append("High CPU usage (>95%)")
                status = "degraded"
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthStatus(
                service="system",
                status=status,
                checks={
                    "memory_usage_percent": metrics.get("memory", {}).get("usage_percent"),
                    "disk_usage_percent": metrics.get("disk", {}).get("usage_percent"),
                    "cpu_usage_percent": cpu_usage,
                    "issues": issues
                },
                response_time_ms=response_time,
                message="; ".join(issues) if issues else None
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthStatus(
                service="system",
                status="unhealthy",
                checks={"error": str(e)},
                response_time_ms=response_time,
                message=str(e)
            )
    
    async def run_all_checks(self) -> Dict[str, HealthStatus]:
        """Run all health checks."""
        checks = {}
        
        try:
            # Run checks in parallel
            db_check, redis_check = await asyncio.gather(
                self.check_database(),
                self.check_redis(),
                return_exceptions=True
            )
            
            if isinstance(db_check, HealthStatus):
                checks["database"] = db_check
            if isinstance(redis_check, HealthStatus):
                checks["redis"] = redis_check
            
            # System check (synchronous)
            checks["system"] = self.check_system_resources()
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
        
        return checks
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall application health."""
        checks = await self.run_all_checks()
        
        # Determine overall status
        overall_status = "healthy"
        unhealthy_services = []
        degraded_services = []
        
        for service, check in checks.items():
            if check.status == "unhealthy":
                overall_status = "unhealthy"
                unhealthy_services.append(service)
            elif check.status == "degraded":
                if overall_status == "healthy":
                    overall_status = "degraded"
                degraded_services.append(service)
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                service: {
                    "status": check.status,
                    "response_time_ms": check.response_time_ms,
                    "message": check.message,
                    "checks": check.checks
                }
                for service, check in checks.items()
            },
            "summary": {
                "total_services": len(checks),
                "healthy": sum(1 for c in checks.values() if c.status == "healthy"),
                "degraded": len(degraded_services),
                "unhealthy": len(unhealthy_services),
                "unhealthy_services": unhealthy_services,
                "degraded_services": degraded_services
            }
        }


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()


# FastAPI middleware for metrics collection
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    
    # Skip metrics collection for metrics endpoints to avoid noise
    if request.url.path in ["/metrics", "/health"]:
        return await call_next(request)
    
    start_time = time.time()
    metrics_collector.increment_active_requests()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        duration_ms = (time.time() - start_time) * 1000
        endpoint = request.url.path
        
        metrics_collector.record_request(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration_ms=duration_ms
        )
        
        return response
        
    except Exception as e:
        # Record error metrics
        duration_ms = (time.time() - start_time) * 1000
        metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,
            duration_ms=duration_ms
        )
        raise
        
    finally:
        metrics_collector.decrement_active_requests()


# Convenience functions
def record_counter(name: str, value: float = 1.0, **tags) -> None:
    """Record counter metric."""
    metrics_collector.record_counter(name, value, tags)

def record_gauge(name: str, value: float, **tags) -> None:
    """Record gauge metric."""
    metrics_collector.record_gauge(name, value, tags)

def record_histogram(name: str, value: float, **tags) -> None:
    """Record histogram metric."""
    metrics_collector.record_histogram(name, value, tags)

def record_timing(name: str, start_time: float, **tags) -> None:
    """Record timing metric."""
    metrics_collector.record_timing(name, start_time, tags)