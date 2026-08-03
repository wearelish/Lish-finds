"""
Enhanced production logging configuration.

Structured logging with JSON output, log rotation, and monitoring integration.
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any

import structlog
from pythonjsonlogger import jsonlogger

from core.config import settings


def setup_logging() -> None:
    """Configure structured logging for production."""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure standard library logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": CustomJSONFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "plain": {
                "format": "%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if settings.LOG_FORMAT == "json" else "plain",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "json",
                "filename": log_dir / "lishfind.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging.ERROR,
                "formatter": "json",
                "filename": log_dir / "lishfind-error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": logging.INFO,
                "propagate": False
            },
            "uvicorn.error": {
                "handlers": ["console", "error_file"],
                "level": logging.INFO,
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["file"] if settings.ENABLE_ACCESS_LOGS else [],
                "level": logging.INFO,
                "propagate": False
            },
            "sqlalchemy.engine": {
                "handlers": ["file"],
                "level": logging.INFO if settings.DEBUG else logging.WARNING,
                "propagate": False
            }
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(logging_config)
    
    # Configure structlog
    configure_structlog()
    
    # Log startup information
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging configured",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        debug=settings.DEBUG
    )


def configure_structlog() -> None:
    """Configure structlog for structured logging."""
    
    processors = [
        # Add log level and timestamp
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        
        # Add caller info in development
        structlog.dev.set_exc_info if settings.DEBUG else structlog.processors.format_exc_info,
    ]
    
    if settings.LOG_FORMAT == "json":
        # Production JSON logging
        processors.extend([
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ])
    else:
        # Development console logging
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['service'] = 'lishfind-backend'
        log_record['environment'] = settings.ENVIRONMENT
        log_record['version'] = getattr(settings, 'VERSION', '1.0.0')
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        if hasattr(record, 'session_id'):
            log_record['session_id'] = record.session_id
        
        # Add performance metrics if available
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms
        
        # Ensure level name is lowercase for consistency
        if 'levelname' in log_record:
            log_record['level'] = log_record['levelname'].lower()


class RequestContextFilter(logging.Filter):
    """Add request context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Try to get context from structlog context or request state
        try:
            import contextvars
            
            # These would be set by middleware
            request_id_var = contextvars.ContextVar('request_id', default=None)
            user_id_var = contextvars.ContextVar('user_id', default=None)
            
            request_id = request_id_var.get()
            user_id = user_id_var.get()
            
            if request_id:
                record.request_id = request_id
            if user_id:
                record.user_id = user_id
                
        except (ImportError, LookupError):
            pass
        
        return True


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def setup_request_logging(app) -> None:
    """Setup request-specific logging middleware."""
    
    @app.middleware("http")
    async def logging_middleware(request, call_next):
        """Add request context to logs."""
        import uuid
        import time
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get logger
        logger = get_logger("request")
        
        # Log request start
        start_time = time.time()
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            request_id=request_id,
            user_agent=request.headers.get("user-agent", ""),
            client_ip=request.client.host if request.client else "unknown"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
                request_id=request_id
            )
            
            return response
            
        except Exception as e:
            # Log request error
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                duration_ms=round(duration * 1000, 2),
                request_id=request_id,
                exc_info=True
            )
            raise


# Performance logging utilities
class PerformanceLogger:
    """Context manager for performance logging."""
    
    def __init__(self, operation_name: str, logger: structlog.BoundLogger = None):
        self.operation_name = operation_name
        self.logger = logger or get_logger("performance")
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug("Operation started", operation=self.operation_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                "Operation failed",
                operation=self.operation_name,
                duration_ms=round(duration * 1000, 2),
                error=str(exc_val)
            )
        else:
            level = "warning" if duration > 1.0 else "info"
            self.logger.log(
                level,
                "Operation completed",
                operation=self.operation_name,
                duration_ms=round(duration * 1000, 2)
            )


def log_performance(operation_name: str):
    """Decorator for performance logging."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(f"perf.{func.__module__}.{func.__name__}")
            with PerformanceLogger(operation_name, logger):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(f"perf.{func.__module__}.{func.__name__}")
            with PerformanceLogger(operation_name, logger):
                return func(*args, **kwargs)
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator