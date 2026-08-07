"""
LishFind Backend - Main Application Entry Point

Minimal FastAPI application optimized for Render deployment.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="LishFind API",
        description="AI Search Engine for the Real World - Backend API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Simple health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "message": "LishFind Backend is running"
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "LishFind API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    
    return app

# Create the app
app = create_app()

# Include basic API routes if available
try:
    from api.v1.endpoints import ai
    app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Service"])
except ImportError:
    print("⚠️  AI endpoints not available")

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment (Render uses PORT env var)
    port = int(os.environ.get("PORT", settings.PORT))
    host = os.environ.get("HOST", settings.HOST)
    
    print(f"🚀 Starting LishFind Backend on {host}:{port}")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )