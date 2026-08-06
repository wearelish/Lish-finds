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

# Import available middleware
try:
    from api.middleware.logging import LoggingMiddleware
except ImportError:
    LoggingMiddleware = None

try:
    from api.middleware.rate_limit import RateLimitMiddleware
except ImportError:
    RateLimitMiddleware = None

try:
    from api.middleware.security import SecurityMiddleware
except ImportError:
    SecurityMiddleware = None

# Import core modules
from api.v1.router import api_v1_router
from core.config import settings

# Optional imports for production features
try:
    from core.exceptions import setup_exception_handlers
except ImportError:
    def setup_exception_handlers(app):
        pass

try:
    from database.connection import init_db, close_db
except ImportError:
    async def init_db():
        pass
    async def close_db():
        pass

try:
    from database.redis import init_redis, close_redis, get_redis_client
except ImportError:
    async def init_redis():
        pass
    async def close_redis():
        pass
    def get_redis_client():
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    try:
        await init_db()
        await init_redis()
        print("✅ Database and Redis initialized")
    except Exception as e:
        print(f"⚠️  Database/Redis initialization failed: {e}")
    
    yield
    
    # Shutdown
    try:
        await close_db()
        await close_redis()
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")


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
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add available middleware
    if SecurityMiddleware:
        app.add_middleware(SecurityMiddleware)
    
    if RateLimitMiddleware and get_redis_client():
        app.add_middleware(RateLimitMiddleware, redis_client_func=get_redis_client)
    
    if LoggingMiddleware:
        app.add_middleware(LoggingMiddleware)
    
    # Exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    app.include_router(api_v1_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        
        # Basic health response for cloud deployment
        health_data = {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "features": {
                "ai_provider": settings.AI_PROVIDER,
                "database": "configured" if settings.DATABASE_URL else "not_configured",
                "redis": "enabled" if settings.REDIS_URL else "disabled",
            }
        }
        
        # Try to check database health if available
        try:
            from database.connection import health_check as db_health_check
            db_health = await db_health_check()
            health_data["database_health"] = db_health
        except Exception as e:
            health_data["database_health"] = {"status": "unavailable", "error": str(e)}
        
        return health_data
    
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
    port = int(os.environ.get("PORT", getattr(settings, 'PORT', 8000)))
    host = os.environ.get("HOST", getattr(settings, 'HOST', '0.0.0.0'))
    
    print(f"🚀 Starting LishFind Backend on {host}:{port}")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")
    
    uvicorn.run(
        app,  # Use app instance directly for better Render compatibility
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )