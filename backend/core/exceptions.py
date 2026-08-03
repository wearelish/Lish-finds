"""
Exception handlers and custom exceptions for LishFind API.

Provides structured error handling with proper HTTP status codes and 
user-friendly error messages.
"""

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


# Custom Exception Classes
class LishFindException(Exception):
    """Base exception for LishFind application."""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class AuthenticationException(LishFindException):
    """Authentication related exceptions."""
    pass


class AuthorizationException(LishFindException):
    """Authorization related exceptions."""
    pass


class BusinessNotFoundException(LishFindException):
    """Exception raised when a business is not found."""
    pass


class UserNotFoundException(LishFindException):
    """Exception raised when a user is not found."""
    pass


class InvalidSearchQueryException(LishFindException):
    """Exception raised when search query is invalid."""
    pass


class AIProviderException(LishFindException):
    """Exception raised when AI provider fails."""
    pass


class RateLimitExceededException(LishFindException):
    """Exception raised when rate limit is exceeded."""
    pass


class DatabaseException(LishFindException):
    """Database operation exceptions."""
    pass


class ValidationException(LishFindException):
    """Data validation exceptions."""
    pass


class ExternalServiceException(LishFindException):
    """External service integration exceptions."""
    pass


# Exception Handlers
async def lishfind_exception_handler(request: Request, exc: LishFindException):
    """Handler for custom LishFind exceptions."""
    logger.error(
        "LishFind exception occurred",
        exception_type=type(exc).__name__,
        message=exc.message,
        code=exc.code,
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, 'request_id', 'unknown')
    )
    
    # Map exception types to HTTP status codes
    status_code_map = {
        AuthenticationException: status.HTTP_401_UNAUTHORIZED,
        AuthorizationException: status.HTTP_403_FORBIDDEN,
        BusinessNotFoundException: status.HTTP_404_NOT_FOUND,
        UserNotFoundException: status.HTTP_404_NOT_FOUND,
        InvalidSearchQueryException: status.HTTP_400_BAD_REQUEST,
        AIProviderException: status.HTTP_503_SERVICE_UNAVAILABLE,
        RateLimitExceededException: status.HTTP_429_TOO_MANY_REQUESTS,
        DatabaseException: status.HTTP_503_SERVICE_UNAVAILABLE,
        ValidationException: status.HTTP_400_BAD_REQUEST,
        ExternalServiceException: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": exc.code,
                "message": exc.message,
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for FastAPI HTTP exceptions."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, 'request_id', 'unknown')
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
        },
        headers=getattr(exc, "headers", None)
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler for Starlette HTTP exceptions."""
    logger.warning(
        "Starlette HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, 'request_id', 'unknown')
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors."""
    logger.warning(
        "Validation error occurred",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, 'request_id', 'unknown')
    )
    
    # Format validation errors for better user experience
    formatted_errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
        formatted_errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": formatted_errors,
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handler for unexpected exceptions."""
    logger.error(
        "Unexpected exception occurred",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, 'request_id', 'unknown'),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": getattr(request.state, 'request_id', 'unknown')
            }
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Set up exception handlers for the FastAPI application."""
    
    # Custom exception handlers
    app.add_exception_handler(LishFindException, lishfind_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)