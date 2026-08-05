"""
Main API v1 router for LishFind Backend.

Includes all API endpoint routers with proper prefixes and tags.
"""

from fastapi import APIRouter

# Create the main API v1 router
api_v1_router = APIRouter()

# Health check endpoint
@api_v1_router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for the API."""
    return {
        "status": "healthy",
        "service": "lishfind-api", 
        "version": "1.0.0",
        "message": "LishFind API is running"
    }

# Import and include available routers
try:
    from api.v1.endpoints import ai
    api_v1_router.include_router(ai.router, prefix="/ai", tags=["AI Service"])
except ImportError:
    print("⚠️  AI endpoints not available")

try:
    from api.v1.endpoints import search
    api_v1_router.include_router(search.router, prefix="/search", tags=["Search & Intent"])
except ImportError:
    print("⚠️  Search endpoints not available")

try:
    from api.v1.endpoints import auth
    api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
except ImportError:
    print("⚠️  Auth endpoints not available")

try:
    from api.v1.endpoints import business
    api_v1_router.include_router(business.router, prefix="/business", tags=["Business Management"])
except ImportError:
    print("⚠️  Business endpoints not available")

try:
    from api.v1.endpoints import monitoring
    api_v1_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
except ImportError:
    print("⚠️  Monitoring endpoints not available")

# Add more endpoints as they become available
# This ensures the app starts even if some modules are missing