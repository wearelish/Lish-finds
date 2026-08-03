"""
Application Performance Monitoring (APM) integration.

Provides distributed tracing, error tracking, and performance monitoring.
"""

import os
import time
import uuid
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
import traceback
import sys

import structlog
from fastapi import Request, Response

from core.config import settings

logger = structlog.get_logger(__name__)

# APM configuration
APM_ENABLED = getattr(settings, 'APM_ENABLED', False)
SENTRY_DSN = os.getenv('SENTRY_DSN')
DATADOG_ENABLED = os.getenv('DD_TRACE_ENABLED', '').lower() == 'true'

# Sentry integration (optional)
sentry_sdk = None
if APM_ENABLED and SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=getattr(settings, 'VERSION', '1.0.0'),
            traces_sample_rate=0.1 if settings.ENVIRONMENT == 'production' else 1.0,
            profiles_sample_rate=0.1 if settings.ENVIRONMENT == 'production' else 1.0,
            integrations=[
                FastApiIntegration(auto_enable=True),
                StarletteIntegration(auto_enable=True),
                SqlalchemyIntegration(),
            ],
            before_send=before_send_sentry,
            before_send_transaction=before_send_transaction_sentry,
        )
        logger.info("Sentry APM initialized", environment=settings.ENVIRONMENT)
    except ImportError:
        logger.warning("Sentry SDK not available, skipping Sentry integration")
        sentry_sdk = None

# Datadog integration (optional)
ddtrace = None
if APM_ENABLED and DATADOG_ENABLED:
    try:
        from ddtrace import tracer, patch
        from ddtrace.contrib.fastapi import patch as patch_fastapi
        import ddtrace
        
        # Patch libraries
        patch(sqlalchemy=True, requests=True, redis=True)
        patch_fastapi()
        
        # Configure tracer
        tracer.configure(
            hostname=os.getenv('DD_AGENT_HOST', 'localhost'),
            port=int(os.getenv('DD_TRACE_AGENT_PORT', '8126')),
        )
        
        logger.info("Datadog APM initialized")
    except ImportError:
        logger.warning("Datadog tracing not available, skipping Datadog integration")
        ddtrace = None


def before_send_sentry(event, hint):
    """Filter Sentry events before sending."""
    # Don't send health check errors
    if 'request' in event:
        url = event['request'].get('url', '')
        if '/health' in url or '/metrics' in url:
            return None
    
    # Filter out expected exceptions
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if exc_type.__name__ in ['ValidationError', 'HTTPException']:
            return None
    
    return event


def before_send_transaction_sentry(event, hint):
    """Filter Sentry transactions before sending."""
    # Don't trace health checks and metrics
    transaction_name = event.get('transaction', '')
    if any(path in transaction_name for path in ['/health', '/metrics', '/docs', '/openapi.json']):
        return None
    
    return event


class TraceContext:
    """Distributed tracing context."""
    
    def __init__(self, operation_name: str, trace_id: str = None, parent_span_id: str = None):
        self.operation_name = operation_name
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.start_time = time.time()
        self.tags = {}
        self.logs = []
    
    def set_tag(self, key: str, value: Any) -> None:
        """Set a tag on the current span."""
        self.tags[key] = value
    
    def log(self, message: str, **kwargs) -> None:
        """Add a log entry to the current span."""
        self.logs.append({
            'timestamp': time.time(),
            'message': message,
            **kwargs
        })
    
    def finish(self, error: Exception = None) -> None:
        """Finish the current span."""
        duration = time.time() - self.start_time
        
        # Log span completion
        log_data = {
            'operation': self.operation_name,
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'duration_ms': round(duration * 1000, 2),
            'tags': self.tags
        }
        
        if error:
            log_data['error'] = str(error)
            log_data['error_type'] = type(error).__name__
            logger.error("Span completed with error", **log_data)
        else:
            logger.info("Span completed", **log_data)
        
        # Send to APM systems
        if sentry_sdk:
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("operation", self.operation_name)
                for key, value in self.tags.items():
                    scope.set_tag(key, value)
                
                if error:
                    sentry_sdk.capture_exception(error)


class APMTracer:
    """Application performance monitoring tracer."""
    
    def __init__(self):
        self.enabled = APM_ENABLED
        self.current_trace: Optional[TraceContext] = None
    
    @contextmanager
    def trace(self, operation_name: str, **tags):
        """Context manager for tracing operations."""
        if not self.enabled:
            yield None
            return
        
        trace = TraceContext(
            operation_name=operation_name,
            parent_span_id=self.current_trace.span_id if self.current_trace else None
        )
        
        # Set initial tags
        for key, value in tags.items():
            trace.set_tag(key, value)
        
        previous_trace = self.current_trace
        self.current_trace = trace
        
        try:
            yield trace
            trace.finish()
        except Exception as e:
            trace.finish(error=e)
            raise
        finally:
            self.current_trace = previous_trace
    
    @asynccontextmanager
    async def async_trace(self, operation_name: str, **tags):
        """Async context manager for tracing operations."""
        if not self.enabled:
            yield None
            return
        
        trace = TraceContext(
            operation_name=operation_name,
            parent_span_id=self.current_trace.span_id if self.current_trace else None
        )
        
        # Set initial tags
        for key, value in tags.items():
            trace.set_tag(key, value)
        
        previous_trace = self.current_trace
        self.current_trace = trace
        
        try:
            yield trace
            trace.finish()
        except Exception as e:
            trace.finish(error=e)
            raise
        finally:
            self.current_trace = previous_trace


# Global tracer instance
apm_tracer = APMTracer()


def trace_function(operation_name: str = None, **default_tags):
    """Decorator for tracing functions."""
    def decorator(func):
        name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if hasattr(func, '__call__') and hasattr(func, '__await__'):
            # Async function
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with apm_tracer.async_trace(name, **default_tags) as trace:
                    if trace:
                        trace.set_tag("function", func.__name__)
                        trace.set_tag("module", func.__module__)
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            # Sync function
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with apm_tracer.trace(name, **default_tags) as trace:
                    if trace:
                        trace.set_tag("function", func.__name__)
                        trace.set_tag("module", func.__module__)
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator


class ErrorTracker:
    """Centralized error tracking and reporting."""
    
    def __init__(self):
        self.enabled = APM_ENABLED
        self.error_counts = {}
    
    def capture_exception(self, error: Exception, 
                         context: Dict[str, Any] = None,
                         user_id: str = None,
                         request: Request = None) -> None:
        """Capture and report an exception."""
        if not self.enabled:
            return
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Count errors
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Prepare error context
        error_context = {
            'error_type': error_type,
            'error_message': error_message,
            'traceback': traceback.format_exc(),
        }
        
        if context:
            error_context['extra'] = context
        
        if user_id:
            error_context['user_id'] = user_id
        
        if request:
            error_context['request'] = {
                'method': request.method,
                'url': str(request.url),
                'headers': dict(request.headers),
                'client_ip': request.client.host if request.client else None
            }
        
        # Log error
        logger.error("Exception captured", **error_context)
        
        # Send to APM systems
        if sentry_sdk:
            with sentry_sdk.configure_scope() as scope:
                if user_id:
                    scope.set_user({"id": user_id})
                
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                
                sentry_sdk.capture_exception(error)
    
    def capture_message(self, message: str, level: str = "info",
                       context: Dict[str, Any] = None,
                       user_id: str = None) -> None:
        """Capture a custom message."""
        if not self.enabled:
            return
        
        # Log message
        getattr(logger, level.lower(), logger.info)(message, **(context or {}))
        
        # Send to APM systems
        if sentry_sdk:
            with sentry_sdk.configure_scope() as scope:
                if user_id:
                    scope.set_user({"id": user_id})
                
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                
                sentry_sdk.capture_message(message, level=level)
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
        return self.error_counts.copy()


# Global error tracker
error_tracker = ErrorTracker()


# FastAPI middleware for APM
async def apm_middleware(request: Request, call_next: Callable):
    """APM middleware for FastAPI."""
    
    # Skip APM for health checks and metrics
    if request.url.path in ['/health', '/metrics', '/docs', '/openapi.json']:
        return await call_next(request)
    
    operation_name = f"{request.method} {request.url.path}"
    
    async with apm_tracer.async_trace(operation_name) as trace:
        if trace:
            trace.set_tag("http.method", request.method)
            trace.set_tag("http.url", str(request.url))
            trace.set_tag("user_agent", request.headers.get("user-agent", ""))
            
            if request.client:
                trace.set_tag("client.ip", request.client.host)
        
        try:
            response = await call_next(request)
            
            if trace:
                trace.set_tag("http.status_code", response.status_code)
                if response.status_code >= 400:
                    trace.set_tag("error", True)
            
            return response
            
        except Exception as e:
            if trace:
                trace.set_tag("error", True)
                trace.set_tag("error.type", type(e).__name__)
                trace.set_tag("error.message", str(e))
            
            # Capture exception
            error_tracker.capture_exception(e, request=request)
            raise


# Performance monitoring decorators
def monitor_performance(operation_name: str = None):
    """Decorator for monitoring function performance."""
    def decorator(func):
        name = operation_name or f"{func.__module__}.{func.__name__}"
        return trace_function(name)(func)
    return decorator


def monitor_database_query(query_name: str = None):
    """Decorator for monitoring database queries."""
    def decorator(func):
        name = query_name or f"db.{func.__name__}"
        return trace_function(name, component="database")(func)
    return decorator


def monitor_external_api(api_name: str = None):
    """Decorator for monitoring external API calls."""
    def decorator(func):
        name = api_name or f"external.{func.__name__}"
        return trace_function(name, component="external_api")(func)
    return decorator


# Convenience functions
def capture_exception(error: Exception, **context) -> None:
    """Capture an exception with context."""
    error_tracker.capture_exception(error, context)


def capture_message(message: str, level: str = "info", **context) -> None:
    """Capture a custom message."""
    error_tracker.capture_message(message, level, context)


def set_user_context(user_id: str, email: str = None, username: str = None) -> None:
    """Set user context for current request."""
    if sentry_sdk:
        with sentry_sdk.configure_scope() as scope:
            scope.set_user({
                "id": user_id,
                "email": email,
                "username": username
            })


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", **data) -> None:
    """Add a breadcrumb for debugging."""
    if sentry_sdk:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data
        )