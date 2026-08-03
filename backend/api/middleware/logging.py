"""
Logging middleware for request/response tracking and performance monitoring.

Captures request details, response times, and errors for comprehensive logging.
"""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Get structured logger
logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        await self._log_request_start(request, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log successful response
            await self._log_response(request, response, request_id, process_time)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time for failed requests
            process_time = time.time() - start_time
            
            # Log error
            await self._log_error(request, e, request_id, process_time)
            
            # Re-raise the exception
            raise
    
    async def _log_request_start(self, request: Request, request_id: str) -> None:
        """Log the start of a request."""
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent", ""),
            client_host=request.client.host if request.client else None,
            path=request.url.path,
            query_params=dict(request.query_params),
            headers={
                key: value for key, value in request.headers.items()
                if key.lower() not in ["authorization", "cookie"]  # Don't log sensitive headers
            }
        )
    
    async def _log_response(
        self, 
        request: Request, 
        response: Response, 
        request_id: str, 
        process_time: float
    ) -> None:
        """Log successful response details."""
        logger.info(
            "Request completed",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
            response_size=response.headers.get("content-length", "unknown"),
            path=request.url.path,
        )
    
    async def _log_error(
        self, 
        request: Request, 
        error: Exception, 
        request_id: str, 
        process_time: float
    ) -> None:
        """Log request errors."""
        logger.error(
            "Request failed",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            error_type=type(error).__name__,
            error_message=str(error),
            process_time_ms=round(process_time * 1000, 2),
            path=request.url.path,
            exc_info=True,
        )