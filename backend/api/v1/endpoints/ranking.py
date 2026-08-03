"""
Ranking API endpoints for LishFind backend.

Provides APIs for business ranking, analytics, and configuration.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user, get_current_admin_user, get_optional_current_user
from database.connection import get_db_session
from models.user import User
from ranking.models import (
    RankingAlgorithm,
    RankingConfig,
    RankingResult,
    UserPreferences,
    RankingBatch,
    RankingBatchResult
)
from ranking.service import RankingService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ranking", tags=["ranking"])


class RankBusinessesRequest(BaseModel):
    """Request schema for ranking businesses."""
    
    business_ids: List[UUID] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of business IDs to rank"
    )
    
    algorithm: RankingAlgorithm = Field(
        RankingAlgorithm.BALANCED,
        description="Ranking algorithm to use"
    )
    
    user_location: Optional[Dict[str, float]] = Field(
        None,
        description="User location for distance-based ranking",
        example={"latitude": 28.6139, "longitude": 77.2090}
    )
    
    config_override: Optional[RankingConfig] = Field(
        None,
        description="Custom ranking configuration"
    )


class UpdatePreferencesRequest(BaseModel):
    """Request schema for updating user preferences."""
    
    category_preferences: Optional[Dict[str, float]] = Field(
        None,
        description="Category preferences (category -> score 0.0-1.0)",
        example={"restaurant": 0.9, "cafe": 0.7}
    )
    
    prefer_high_rated: Optional[bool] = Field(
        None,
        description="Prefer highly rated businesses"
    )
    
    min_preferred_rating: Optional[float] = Field(
        None,
        ge=1.0,
        le=5.0,
        description="Minimum preferred rating"
    )
    
    prefer_nearby: Optional[bool] = Field(
        None,
        description="Prefer nearby businesses"
    )
    
    max_preferred_distance_km: Optional[float] = Field(
        None,
        ge=0.1,
        le=100,
        description="Maximum preferred distance"
    )
    
    preferred_price_ranges: Optional[List[str]] = Field(
        None,
        description="Preferred price ranges"
    )
    
    preferred_amenities: Optional[List[str]] = Field(
        None,
        description="Preferred amenities"
    )


@router.post(
    "/rank",
    response_model=List[RankingResult],
    summary="Rank businesses",
    description="Rank a list of businesses using specified algorithm and user preferences.",
)
async def rank_businesses(
    request: RankBusinessesRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> List[RankingResult]:
    """Rank businesses using the specified algorithm."""
    
    try:
        ranking_service = RankingService(session)
        
        results = await ranking_service.rank_search_results(
            business_ids=request.business_ids,
            algorithm=request.algorithm,
            user_id=current_user.id if current_user else None,
            user_location=request.user_location,
            config_override=request.config_override
        )
        
        logger.info(
            "Business ranking API request completed",
            business_count=len(request.business_ids),
            algorithm=request.algorithm.value,
            user_id=current_user.id if current_user else None,
            results_count=len(results)
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "Business ranking API failed",
            business_ids=request.business_ids,
            algorithm=request.algorithm.value,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ranking failed: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=RankingBatchResult,
    summary="Batch rank businesses",
    description="Process a batch ranking request with custom configuration.",
)
async def rank_businesses_batch(
    batch_request: RankingBatch,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> RankingBatchResult:
    """Process a batch ranking request."""
    
    try:
        ranking_service = RankingService(session)
        
        result = await ranking_service.rank_businesses_batch(batch_request)
        
        logger.info(
            "Batch ranking API request completed",
            business_count=len(batch_request.businesses),
            algorithm=batch_request.config.algorithm.value,
            processing_time_ms=result.processing_time_ms,
            user_id=current_user.id if current_user else None
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Batch ranking API failed",
            business_count=len(batch_request.businesses),
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch ranking failed: {str(e)}"
        )


@router.get(
    "/analytics/{business_ids}",
    summary="Get ranking analytics",
    description="Get detailed ranking analytics for a set of businesses.",
)
async def get_ranking_analytics(
    business_ids: str,  # Comma-separated UUIDs
    algorithm: RankingAlgorithm = RankingAlgorithm.BALANCED,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get ranking analytics for businesses (admin only)."""
    
    try:
        # Parse business IDs
        business_id_list = [UUID(bid.strip()) for bid in business_ids.split(',')]
        
        ranking_service = RankingService(session)
        
        analytics = await ranking_service.get_ranking_analytics(
            business_ids=business_id_list,
            algorithm=algorithm
        )
        
        logger.info(
            "Ranking analytics generated",
            business_count=len(business_id_list),
            algorithm=algorithm.value,
            admin_user_id=current_user.id
        )
        
        return analytics
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid business ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Ranking analytics failed",
            business_ids=business_ids,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics generation failed: {str(e)}"
        )


@router.get(
    "/compare/{business_ids}",
    summary="Compare ranking algorithms",
    description="Compare ranking results across different algorithms.",
)
async def compare_ranking_algorithms(
    business_ids: str,  # Comma-separated UUIDs
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Compare ranking algorithms (admin only)."""
    
    try:
        # Parse business IDs
        business_id_list = [UUID(bid.strip()) for bid in business_ids.split(',')]
        
        # Prepare user location
        user_location = None
        if latitude and longitude:
            user_location = {"latitude": latitude, "longitude": longitude}
        
        ranking_service = RankingService(session)
        
        comparison = await ranking_service.get_algorithm_comparison(
            business_ids=business_id_list,
            user_location=user_location
        )
        
        # Convert results to serializable format
        serialized_comparison = {}
        for algorithm, results in comparison.items():
            serialized_comparison[algorithm.value] = [
                {
                    "business_id": str(result.business_id),
                    "final_score": result.final_score,
                    "distance_score": result.distance_score,
                    "rating_score": result.rating_score,
                    "popularity_score": result.popularity_score
                }
                for result in results[:10]  # Top 10 results only
            ]
        
        logger.info(
            "Algorithm comparison completed",
            business_count=len(business_id_list),
            algorithms_compared=len(comparison),
            admin_user_id=current_user.id
        )
        
        return {
            "business_count": len(business_id_list),
            "algorithms_compared": list(comparison.keys()) if comparison else [],
            "results": serialized_comparison
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid business ID format: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "Algorithm comparison failed",
            business_ids=business_ids,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Algorithm comparison failed: {str(e)}"
        )


@router.get(
    "/preferences",
    response_model=UserPreferences,
    summary="Get user preferences",
    description="Get current user's ranking preferences.",
)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> UserPreferences:
    """Get user's ranking preferences."""
    
    try:
        ranking_service = RankingService(session)
        
        # Load user preferences
        preferences = await ranking_service._load_user_preferences(current_user.id)
        
        if preferences:
            logger.debug(
                "User preferences retrieved",
                user_id=current_user.id,
                category_count=len(preferences.category_preferences)
            )
            return preferences
        else:
            # Return default preferences if none found
            default_preferences = UserPreferences(
                user_id=current_user.id,
                category_preferences={},
                prefer_high_rated=True,
                min_preferred_rating=4.0,
                prefer_nearby=True
            )
            
            return default_preferences
        
    except Exception as e:
        logger.error(
            "Failed to get user preferences",
            user_id=current_user.id,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}"
        )


@router.put(
    "/preferences",
    summary="Update user preferences",
    description="Update current user's ranking preferences.",
)
async def update_user_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
) -> Dict[str, str]:
    """Update user's ranking preferences."""
    
    try:
        ranking_service = RankingService(session)
        
        # Load existing preferences or create new ones
        existing_preferences = await ranking_service._load_user_preferences(current_user.id)
        
        if existing_preferences:
            # Update existing preferences
            if request.category_preferences is not None:
                existing_preferences.category_preferences = request.category_preferences
            if request.prefer_high_rated is not None:
                existing_preferences.prefer_high_rated = request.prefer_high_rated
            if request.min_preferred_rating is not None:
                existing_preferences.min_preferred_rating = request.min_preferred_rating
            if request.prefer_nearby is not None:
                existing_preferences.prefer_nearby = request.prefer_nearby
            if request.max_preferred_distance_km is not None:
                existing_preferences.max_preferred_distance_km = request.max_preferred_distance_km
            if request.preferred_price_ranges is not None:
                existing_preferences.preferred_price_ranges = request.preferred_price_ranges
            if request.preferred_amenities is not None:
                existing_preferences.preferred_amenities = request.preferred_amenities
            
            updated_preferences = existing_preferences
        else:
            # Create new preferences
            updated_preferences = UserPreferences(
                user_id=current_user.id,
                category_preferences=request.category_preferences or {},
                prefer_high_rated=request.prefer_high_rated if request.prefer_high_rated is not None else True,
                min_preferred_rating=request.min_preferred_rating or 4.0,
                prefer_nearby=request.prefer_nearby if request.prefer_nearby is not None else True,
                max_preferred_distance_km=request.max_preferred_distance_km,
                preferred_price_ranges=request.preferred_price_ranges or [],
                preferred_amenities=request.preferred_amenities or []
            )
        
        # Save updated preferences
        await ranking_service.update_user_preferences(current_user.id, updated_preferences)
        
        logger.info(
            "User preferences updated",
            user_id=current_user.id,
            category_preferences_count=len(updated_preferences.category_preferences)
        )
        
        return {"message": "Preferences updated successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to update user preferences",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )