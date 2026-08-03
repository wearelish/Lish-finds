"""
Recommendation API endpoints for LishFind backend.

Provides personalized business recommendations, user preferences, and analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai.recommendations.models import (
    RecommendationStrategy,
    RecommendationType,
    RecommendationResult,
    UserInteraction,
    UserInteractionType,
    RecommendationFeedback
)
from ai.recommendations.service import RecommendationService
from api.auth.dependencies import get_current_user, get_current_admin_user, get_optional_current_user
from database.connection import get_db_session
from models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class GetRecommendationsRequest(BaseModel):
    """Request schema for getting recommendations."""
    
    recommendation_type: RecommendationType = Field(
        RecommendationType.RECOMMENDED_FOR_YOU,
        description="Type of recommendations to generate"
    )
    
    strategy: RecommendationStrategy = Field(
        RecommendationStrategy.HYBRID,
        description="Recommendation strategy to use"
    )
    
    current_location: Optional[Dict[str, float]] = Field(
        None,
        description="User's current location",
        example={"latitude": 28.6139, "longitude": 77.2090}
    )
    
    context_business_id: Optional[UUID] = Field(
        None,
        description="Business ID for context-based recommendations"
    )
    
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Number of recommendations to return"
    )
    
    categories: Optional[List[str]] = Field(
        None,
        description="Filter by business categories",
        example=["restaurant", "cafe"]
    )


class RecordInteractionRequest(BaseModel):
    """Request schema for recording user interactions."""
    
    business_id: UUID = Field(..., description="Business ID")
    interaction_type: UserInteractionType = Field(..., description="Type of interaction")
    
    # Optional interaction details
    duration_seconds: Optional[int] = Field(None, description="Duration of interaction")
    rating_given: Optional[float] = Field(None, ge=1.0, le=5.0, description="Rating given")
    review_text: Optional[str] = Field(None, description="Review text")
    
    # Context
    search_query: Optional[str] = Field(None, description="Search query that led to interaction")
    recommendation_id: Optional[str] = Field(None, description="Recommendation ID")
    user_location: Optional[Dict[str, float]] = Field(None, description="User location")


class RecordFeedbackRequest(BaseModel):
    """Request schema for recording recommendation feedback."""
    
    recommendation_id: str = Field(..., description="Recommendation ID")
    business_id: UUID = Field(..., description="Recommended business ID")
    
    # Explicit feedback
    helpful: Optional[bool] = Field(None, description="Was recommendation helpful?")
    relevant: Optional[bool] = Field(None, description="Was recommendation relevant?")
    surprising: Optional[bool] = Field(None, description="Was recommendation surprising?")
    
    # Actions taken
    clicked: bool = Field(False, description="Did user click on recommendation?")
    visited: bool = Field(False, description="Did user visit the business?")
    dismissed: bool = Field(False, description="Did user dismiss recommendation?")
    
    # Free-form feedback
    feedback_text: Optional[str] = Field(None, description="Additional feedback")


class UserPreferenceUpdate(BaseModel):
    """Request schema for updating user preferences."""
    
    category_preferences: Optional[Dict[str, float]] = Field(
        None,
        description="Category preferences (0.0 to 1.0)",
        example={"restaurant": 0.9, "cafe": 0.7}
    )
    
    price_range_preferences: Optional[Dict[str, float]] = Field(
        None,
        description="Price range preferences",
        example={"budget": 0.8, "moderate": 0.9, "expensive": 0.3}
    )
    
    preferred_distance_km: Optional[float] = Field(
        None,
        ge=0.1,
        le=50.0,
        description="Preferred search distance in km"
    )
    
    rating_sensitivity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="How much ratings matter (0-1)"
    )
    
    follows_trends: Optional[bool] = Field(
        None,
        description="Whether user likes trending places"
    )
    
    prefers_popular_places: Optional[bool] = Field(
        None,
        description="Preference for popular venues"
    )


@router.get(
    "/",
    response_model=RecommendationResult,
    summary="Get personalized recommendations",
    description="Get personalized business recommendations for the current user.",
)
async def get_recommendations(
    recommendation_type: RecommendationType = RecommendationType.RECOMMENDED_FOR_YOU,
    strategy: RecommendationStrategy = RecommendationStrategy.HYBRID,
    latitude: Optional[float] = Query(None, description="User latitude"),
    longitude: Optional[float] = Query(None, description="User longitude"),
    context_business_id: Optional[UUID] = Query(None, description="Context business ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> RecommendationResult:
    """Get personalized recommendations for the user."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        # Prepare location
        current_location = None
        if latitude is not None and longitude is not None:
            current_location = {"latitude": latitude, "longitude": longitude}
        
        result = await recommendation_service.get_recommendations_for_user(
            user_id=current_user.id if current_user else None,
            recommendation_type=recommendation_type,
            current_location=current_location,
            context_business_id=context_business_id,
            limit=limit,
            strategy=strategy
        )
        
        logger.info(
            "Recommendations API request completed",
            user_id=current_user.id if current_user else None,
            recommendation_type=recommendation_type.value,
            strategy=strategy.value,
            recommendations_count=len(result.recommendations)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Recommendations API failed",
            user_id=current_user.id if current_user else None,
            recommendation_type=recommendation_type.value,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )


@router.post(
    "/",
    response_model=RecommendationResult,
    summary="Get recommendations with detailed request",
    description="Get recommendations using detailed request parameters.",
)
async def get_recommendations_detailed(
    request: GetRecommendationsRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> RecommendationResult:
    """Get recommendations with detailed request parameters."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        result = await recommendation_service.get_recommendations_for_user(
            user_id=current_user.id if current_user else None,
            recommendation_type=request.recommendation_type,
            current_location=request.current_location,
            context_business_id=request.context_business_id,
            limit=request.limit,
            strategy=request.strategy
        )
        
        logger.info(
            "Detailed recommendations API request completed",
            user_id=current_user.id if current_user else None,
            recommendation_type=request.recommendation_type.value,
            recommendations_count=len(result.recommendations)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Detailed recommendations API failed",
            user_id=current_user.id if current_user else None,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )


@router.get(
    "/similar/{business_id}",
    response_model=RecommendationResult,
    summary="Get similar businesses",
    description="Get businesses similar to the specified business.",
)
async def get_similar_businesses(
    business_id: UUID,
    latitude: Optional[float] = Query(None, description="User latitude"),
    longitude: Optional[float] = Query(None, description="User longitude"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_optional_current_user)
) -> RecommendationResult:
    """Get businesses similar to the specified business."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        # Prepare location
        current_location = None
        if latitude is not None and longitude is not None:
            current_location = {"latitude": latitude, "longitude": longitude}
        
        result = await recommendation_service.get_similar_business_recommendations(
            business_id=business_id,
            user_id=current_user.id if current_user else None,
            current_location=current_location,
            limit=limit
        )
        
        logger.info(
            "Similar businesses API request completed",
            business_id=business_id,
            user_id=current_user.id if current_user else None,
            recommendations_count=len(result.recommendations)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Similar businesses API failed",
            business_id=business_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get similar businesses: {str(e)}"
        )


@router.get(
    "/trending",
    response_model=RecommendationResult,
    summary="Get trending businesses",
    description="Get currently trending business recommendations.",
)
async def get_trending_businesses(
    latitude: Optional[float] = Query(None, description="User latitude"),
    longitude: Optional[float] = Query(None, description="User longitude"),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    session: AsyncSession = Depends(get_db_session)
) -> RecommendationResult:
    """Get trending business recommendations."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        # Prepare location
        current_location = None
        if latitude is not None and longitude is not None:
            current_location = {"latitude": latitude, "longitude": longitude}
        
        # Parse categories
        category_list = None
        if categories:
            category_list = [cat.strip() for cat in categories.split(',')]
        
        result = await recommendation_service.get_trending_recommendations(
            current_location=current_location,
            categories=category_list,
            limit=limit
        )
        
        logger.info(
            "Trending businesses API request completed",
            categories=category_list,
            recommendations_count=len(result.recommendations)
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Trending businesses API failed",
            categories=categories,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending businesses: {str(e)}"
        )


@router.post(
    "/interaction",
    summary="Record user interaction",
    description="Record a user interaction with a business for learning purposes.",
)
async def record_interaction(
    request: RecordInteractionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Record user interaction with a business."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        # Create interaction object
        interaction = UserInteraction(
            user_id=current_user.id,
            business_id=request.business_id,
            interaction_type=request.interaction_type,
            duration_seconds=request.duration_seconds,
            rating_given=request.rating_given,
            review_text=request.review_text,
            search_query=request.search_query,
            recommendation_id=request.recommendation_id,
            user_location=request.user_location,
            day_of_week=datetime.now().strftime('%A').lower(),
            hour_of_day=datetime.now().hour
        )
        
        await recommendation_service.record_user_interaction(interaction)
        
        logger.info(
            "User interaction recorded via API",
            user_id=current_user.id,
            business_id=request.business_id,
            interaction_type=request.interaction_type.value
        )
        
        return {"message": "Interaction recorded successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to record interaction via API",
            user_id=current_user.id,
            business_id=request.business_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record interaction: {str(e)}"
        )


@router.post(
    "/feedback",
    summary="Record recommendation feedback",
    description="Record feedback on a recommendation for learning purposes.",
)
async def record_feedback(
    request: RecordFeedbackRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Record feedback on a recommendation."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        # Create feedback object
        feedback = RecommendationFeedback(
            recommendation_id=request.recommendation_id,
            user_id=current_user.id,
            business_id=request.business_id,
            helpful=request.helpful,
            relevant=request.relevant,
            surprising=request.surprising,
            clicked=request.clicked,
            visited=request.visited,
            dismissed=request.dismissed,
            feedback_text=request.feedback_text
        )
        
        await recommendation_service.record_recommendation_feedback(feedback)
        
        logger.info(
            "Recommendation feedback recorded via API",
            user_id=current_user.id,
            recommendation_id=request.recommendation_id,
            business_id=request.business_id,
            helpful=request.helpful
        )
        
        return {"message": "Feedback recorded successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to record feedback via API",
            user_id=current_user.id,
            recommendation_id=request.recommendation_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record feedback: {str(e)}"
        )


@router.get(
    "/profile",
    summary="Get user recommendation profile",
    description="Get the current user's recommendation profile and preferences.",
)
async def get_user_profile(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's recommendation profile."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        profile = await recommendation_service.get_user_profile(current_user.id)
        
        if profile:
            logger.debug(
                "User recommendation profile retrieved via API",
                user_id=current_user.id,
                profile_completeness=profile.profile_completeness
            )
            
            return profile.dict()
        else:
            return {
                "user_id": str(current_user.id),
                "message": "No profile data available yet. Profile will be built as you interact with recommendations."
            }
        
    except Exception as e:
        logger.error(
            "Failed to get user profile via API",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )


@router.put(
    "/profile",
    summary="Update user preferences",
    description="Update the current user's recommendation preferences.",
)
async def update_user_preferences(
    request: UserPreferenceUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Update user's recommendation preferences."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        # Convert request to updates dict
        updates = {}
        if request.category_preferences is not None:
            updates['category_preferences'] = request.category_preferences
        if request.price_range_preferences is not None:
            updates['price_range_preferences'] = request.price_range_preferences
        if request.preferred_distance_km is not None:
            updates['preferred_distance_km'] = request.preferred_distance_km
        if request.rating_sensitivity is not None:
            updates['rating_sensitivity'] = request.rating_sensitivity
        if request.follows_trends is not None:
            updates['follows_trends'] = request.follows_trends
        if request.prefers_popular_places is not None:
            updates['prefers_popular_places'] = request.prefers_popular_places
        
        await recommendation_service.update_user_profile(current_user.id, updates)
        
        logger.info(
            "User preferences updated via API",
            user_id=current_user.id,
            updates=list(updates.keys())
        )
        
        return {"message": "Preferences updated successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to update user preferences via API",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.get(
    "/analytics",
    summary="Get recommendation analytics",
    description="Get recommendation system analytics and performance metrics (admin only).",
)
async def get_recommendation_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days for analytics"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get recommendation system analytics (admin only)."""
    
    try:
        recommendation_service = RecommendationService(session)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        analytics = await recommendation_service.get_recommendation_analytics(
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(
            "Recommendation analytics retrieved via API",
            admin_user_id=current_user.id,
            days=days,
            total_recommendations=analytics.total_recommendations
        )
        
        return analytics.dict()
        
    except Exception as e:
        logger.error(
            "Failed to get recommendation analytics via API",
            admin_user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}"
        )