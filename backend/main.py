"""
LishFind Backend - Main Application Entry Point

AI-powered local search engine backend built with FastAPI.
Implements clean architecture with separated concerns for scalability.

Production-ready deployment configuration for cloud hosting.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from api.middleware.logging import LoggingMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.security import SecurityMiddleware
from monitoring.metrics import metrics_middleware
from monitoring.apm import apm_middleware
from performance.compression import CompressionMiddleware
from performance.cache import cache_manager
from api.v1.router import api_v1_router
from core.config import settings
from core.exceptions import setup_exception_handlers
from database.connection import init_db, close_db
from database.redis import init_redis, close_redis, get_redis_client
from docs.api_docs import setup_enhanced_docs
from utils.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    setup_logging()
    await init_db()
    await init_redis()
    
    # Initialize cache manager
    await cache_manager.init_redis()
    
    yield
    
    # Shutdown
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="LishFind API",
        description="AI Search Engine for the Real World - Backend API",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Setup enhanced documentation
    setup_enhanced_docs(app)
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middleware (order matters - these are processed in reverse order)
    if settings.GZIP_COMPRESSION:
        app.add_middleware(CompressionMiddleware, min_size=1024)
    
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(RateLimitMiddleware, redis_client_func=get_redis_client)
    app.add_middleware(LoggingMiddleware)
    
    # Add monitoring middleware
    app.middleware("http")(metrics_middleware)
    app.middleware("http")(apm_middleware)
    
    # Exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(api_v1_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        from database.connection import health_check as db_health_check
        from database.redis import health_check as redis_health_check
        
        # Check database health
        db_health = await db_health_check()
        
        # Check Redis health (if enabled)
        redis_health = {"status": "disabled"}
        if settings.REDIS_URL:
            redis_health = await redis_health_check()
        
        # Overall health status
        overall_status = "healthy"
        if db_health["status"] != "healthy":
            overall_status = "unhealthy"
        elif redis_health["status"] not in ["healthy", "disabled"]:
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "database": db_health,
            "redis": redis_health,
            "checks": {
                "database": db_health["status"] == "healthy",
                "redis": redis_health["status"] in ["healthy", "disabled"],
            }
        }
    
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "LishFind API",
            "version": "1.0.0",
            "description": "AI-Powered Local Search Engine Backend",
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc",
                "openapi_json": "/openapi.json"
            },
            "endpoints": {
                "health": "/health",
                "api_v1": "/api/v1"
            },
            "support": {
                "email": "api-support@lishfind.com",
                "documentation": "https://docs.lishfind.com"
            }
        }
    
    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment (Render uses PORT env var)
    port = int(os.environ.get("PORT", getattr(settings, 'PORT', 8001)))
    host = os.environ.get("HOST", getattr(settings, 'HOST', '0.0.0.0'))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )