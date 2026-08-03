"""
Main API v1 router for LishFind Backend.

Includes all API endpoint routers with proper prefixes and tags.
"""

from fastapi import APIRouter

# Import routers
from api.v1.endpoints import auth, ai, search, ranking, recommendations, business, cache, monitoring

# Create the main API v1 router
api_v1_router = APIRouter()

# Health check endpoint
@api_v1_router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for the API."""
    return {
        "status": "healthy",
        "service": "lishfind-api",
        "version": "1.0.0"
    }

# Include endpoint routers
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(ai.router, prefix="/ai", tags=["AI Service"])
api_v1_router.include_router(search.router, prefix="/search", tags=["Search & Intent"])
api_v1_router.include_router(ranking.router, prefix="/ranking", tags=["Business Ranking"])
api_v1_router.include_router(recommendations.router, prefix="/recommendations", tags=["AI Recommendations"])
api_v1_router.include_router(business.router, prefix="/business", tags=["Business Management"])
api_v1_router.include_router(cache.router, prefix="/cache", tags=["Cache Management"])
api_v1_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])

# Root-level monitoring endpoints (for load balancers)
api_v1_router.include_router(monitoring.router, prefix="", tags=["Health & Monitoring"])

# TODO: Include other endpoint routers as they are created
# api_v1_router.include_router(search.router, prefix="/search", tags=["Search"])
# api_v1_router.include_router(business.router, prefix="/business", tags=["Business"])
# api_v1_router.include_router(users.router, prefix="/users", tags=["Users"])