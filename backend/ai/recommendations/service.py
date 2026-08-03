"""
High-level recommendation service for LishFind backend.

Provides user profile management, recommendation generation, and analytics.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ai.recommendations.engine import RecommendationEngine
from ai.recommendations.models import (
    RecommendationRequest,
    RecommendationResult,
    RecommendationStrategy,
    RecommendationType,
    UserProfile,
    UserInteraction,
    RecommendationFeedback,
    RecommendationAnalytics
)
from database.redis import get_cache, set_cache

logger = structlog.get_logger(__name__)


class RecommendationService:
    """High-level recommendation service with user profile management."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.recommendation_engine = RecommendationEngine(session)
        self.cache_ttl = 3600  # 1 hour cache for recommendations
        self.profile_cache_ttl = 86400  # 24 hours for user profiles
    
    async def get_recommendations_for_user(
        self,
        user_id: Optional[UUID],
        recommendation_type: RecommendationType = RecommendationType.RECOMMENDED_FOR_YOU,
        current_location: Optional[Dict[str, float]] = None,
        context_business_id: Optional[UUID] = None,
        limit: int = 10,
        strategy: RecommendationStrategy = RecommendationStrategy.HYBRID
    ) -> RecommendationResult:
        """
        Get personalized recommendations for a user.
        
        Args:
            user_id: User ID for personalization (None for anonymous)
            recommendation_type: Type of recommendations to generate
            current_location: User's current location
            context_business_id: Business for context-based recommendations
            limit: Number of recommendations to return
            strategy: Recommendation strategy to use
            
        Returns:
            RecommendationResult with personalized recommendations
        """
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(
                user_id, recommendation_type, current_location, context_business_id, limit, strategy
            )
            
            cached_result = await self._get_cached_recommendations(cache_key)
            if cached_result:
                logger.info(
                    "Recommendations served from cache",
                    user_id=user_id,
                    cache_key=cache_key
                )
                return cached_result
            
            # Load user profile if available
            user_profile = None
            if user_id:
                user_profile = await self.get_user_profile(user_id)
            
            # Create recommendation request
            request = RecommendationRequest(
                user_id=user_id,
                current_location=current_location,
                context_business_id=context_business_id,
                recommendation_type=recommendation_type,
                strategy=strategy,
                limit=limit,
                include_reasoning=True,
                diversity_factor=0.3
            )
            
            # Generate recommendations
            result = await self.recommendation_engine.generate_recommendations(
                request=request,
                user_profile=user_profile
            )
            
            # Cache successful results
            if result.recommendations:
                await self._cache_recommendations(cache_key, result)
            
            # Log recommendation generation
            await self._log_recommendation_request(request, result)
            
            logger.info(
                "Recommendations generated for user",
                user_id=user_id,
                recommendation_type=recommendation_type.value,
                strategy=strategy.value,
                recommendations_count=len(result.recommendations),
                processing_time_ms=result.processing_time_ms
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to get recommendations for user",
                user_id=user_id,
                recommendation_type=recommendation_type.value,
                error=str(e),
                exc_info=True
            )
            
            # Return empty result on error
            return RecommendationResult(
                recommendations=[],
                request_type=recommendation_type,
                strategy_used=strategy,
                total_candidates=0,
                processing_time_ms=0,
                user_id=user_id,
                average_confidence=0.0,
                diversity_score=0.0,
                novelty_score=0.0,
                strategy_explanation="Error generating recommendations",
                used_fallback=True,
                fallback_reason=str(e)
            )
    
    async def get_similar_business_recommendations(
        self,
        business_id: UUID,
        user_id: Optional[UUID] = None,
        current_location: Optional[Dict[str, float]] = None,
        limit: int = 10
    ) -> RecommendationResult:
        """Get businesses similar to the specified business."""
        
        try:
            user_profile = None
            if user_id:
                user_profile = await self.get_user_profile(user_id)
            
            request = RecommendationRequest(
                user_id=user_id,
                current_location=current_location,
                context_business_id=business_id,
                recommendation_type=RecommendationType.SIMILAR_BUSINESSES,
                strategy=RecommendationStrategy.CONTENT_BASED,
                limit=limit
            )
            
            result = await self.recommendation_engine.generate_recommendations(
                request=request,
                user_profile=user_profile
            )
            
            logger.info(
                "Similar business recommendations generated",
                business_id=business_id,
                user_id=user_id,
                recommendations_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to get similar business recommendations",
                business_id=business_id,
                error=str(e)
            )
            raise
    
    async def get_trending_recommendations(
        self,
        current_location: Optional[Dict[str, float]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 10
    ) -> RecommendationResult:
        """Get trending business recommendations."""
        
        try:
            request = RecommendationRequest(
                current_location=current_location,
                categories=categories,
                recommendation_type=RecommendationType.TRENDING_NOW,
                strategy=RecommendationStrategy.TRENDING,
                limit=limit
            )
            
            result = await self.recommendation_engine.generate_recommendations(
                request=request,
                user_profile=None
            )
            
            logger.info(
                "Trending recommendations generated",
                categories=categories,
                recommendations_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to get trending recommendations",
                categories=categories,
                error=str(e)
            )
            raise
    
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get or create user profile for recommendations."""
        
        try:
            # Try cache first
            cache_key = f"user_profile:{user_id}"
            cached_data = await get_cache(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return UserProfile(**data)
            
            # Generate profile from user behavior
            profile = await self._build_user_profile(user_id)
            
            # Cache the profile
            if profile:
                await set_cache(
                    cache_key,
                    json.dumps(profile.dict(), default=str),
                    ttl=self.profile_cache_ttl
                )
            
            return profile
            
        except Exception as e:
            logger.error(
                "Failed to get user profile",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def update_user_profile(
        self,
        user_id: UUID,
        profile_updates: Dict[str, Any]
    ) -> UserProfile:
        """Update user profile with new preferences."""
        
        try:
            # Get existing profile
            existing_profile = await self.get_user_profile(user_id)
            
            if existing_profile:
                # Update existing profile
                profile_dict = existing_profile.dict()
                profile_dict.update(profile_updates)
                profile_dict['updated_at'] = datetime.utcnow()
                updated_profile = UserProfile(**profile_dict)
            else:
                # Create new profile
                profile_dict = {
                    'user_id': user_id,
                    'updated_at': datetime.utcnow(),
                    **profile_updates
                }
                updated_profile = UserProfile(**profile_dict)
            
            # Save to cache
            cache_key = f"user_profile:{user_id}"
            await set_cache(
                cache_key,
                json.dumps(updated_profile.dict(), default=str),
                ttl=self.profile_cache_ttl
            )
            
            logger.info(
                "User profile updated",
                user_id=user_id,
                updates=list(profile_updates.keys())
            )
            
            return updated_profile
            
        except Exception as e:
            logger.error(
                "Failed to update user profile",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def record_user_interaction(self, interaction: UserInteraction) -> None:
        """Record user interaction for learning."""
        
        try:
            # Store interaction (in production, this would go to a database)
            interaction_key = f"interaction:{interaction.user_id}:{datetime.utcnow().timestamp()}"
            
            await set_cache(
                interaction_key,
                json.dumps(interaction.dict(), default=str),
                ttl=86400 * 30  # Keep for 30 days
            )
            
            # Update user profile based on interaction
            await self._update_profile_from_interaction(interaction)
            
            logger.info(
                "User interaction recorded",
                user_id=interaction.user_id,
                business_id=interaction.business_id,
                interaction_type=interaction.interaction_type.value
            )
            
        except Exception as e:
            logger.error(
                "Failed to record user interaction",
                user_id=interaction.user_id,
                error=str(e)
            )
    
    async def record_recommendation_feedback(self, feedback: RecommendationFeedback) -> None:
        """Record feedback on recommendations for learning."""
        
        try:
            # Store feedback
            feedback_key = f"feedback:{feedback.user_id}:{feedback.recommendation_id}"
            
            await set_cache(
                feedback_key,
                json.dumps(feedback.dict(), default=str),
                ttl=86400 * 90  # Keep for 90 days
            )
            
            # Use feedback to improve future recommendations
            await self._update_profile_from_feedback(feedback)
            
            logger.info(
                "Recommendation feedback recorded",
                user_id=feedback.user_id,
                business_id=feedback.business_id,
                helpful=feedback.helpful,
                clicked=feedback.clicked
            )
            
        except Exception as e:
            logger.error(
                "Failed to record recommendation feedback",
                user_id=feedback.user_id,
                error=str(e)
            )
    
    async def get_recommendation_analytics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> RecommendationAnalytics:
        """Get recommendation system analytics."""
        
        try:
            # In production, this would query analytics database
            # For now, return placeholder analytics
            
            analytics = RecommendationAnalytics(
                click_through_rate=0.15,
                conversion_rate=0.08,
                user_satisfaction=0.78,
                strategy_performance={
                    "hybrid": {"ctr": 0.18, "conversion": 0.10, "satisfaction": 0.82},
                    "collaborative_filtering": {"ctr": 0.16, "conversion": 0.09, "satisfaction": 0.79},
                    "content_based": {"ctr": 0.14, "conversion": 0.07, "satisfaction": 0.76},
                    "ai_powered": {"ctr": 0.20, "conversion": 0.12, "satisfaction": 0.85},
                    "trending": {"ctr": 0.12, "conversion": 0.06, "satisfaction": 0.72}
                },
                average_diversity=0.68,
                average_novelty=0.45,
                business_coverage=0.75,
                user_coverage=0.85,
                peak_hours=[12, 13, 19, 20, 21],
                daily_patterns={
                    "monday": 0.8, "tuesday": 0.9, "wednesday": 0.85,
                    "thursday": 0.95, "friday": 1.2, "saturday": 1.4, "sunday": 1.1
                },
                category_distribution={
                    "restaurant": 0.35, "cafe": 0.18, "retail": 0.15,
                    "entertainment": 0.12, "service": 0.10, "other": 0.10
                },
                period_start=start_date,
                period_end=end_date,
                total_recommendations=12500
            )
            
            logger.info(
                "Recommendation analytics generated",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                total_recommendations=analytics.total_recommendations
            )
            
            return analytics
            
        except Exception as e:
            logger.error(
                "Failed to generate recommendation analytics",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e)
            )
            raise
    
    async def _build_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Build user profile from interaction history."""
        
        try:
            # This would analyze user's historical interactions
            # For now, return a basic profile
            
            profile = UserProfile(
                user_id=user_id,
                category_preferences={
                    "restaurant": 0.8,
                    "cafe": 0.7,
                    "retail": 0.5,
                    "entertainment": 0.6
                },
                price_range_preferences={
                    "budget": 0.6,
                    "moderate": 0.8,
                    "expensive": 0.4
                },
                preferred_distance_km=5.0,
                rating_sensitivity=0.7,
                review_count_importance=0.5,
                total_interactions=0,
                favorite_categories=["restaurant", "cafe"],
                avoided_categories=[],
                most_active_hours=[12, 13, 19, 20, 21],
                follows_trends=True,
                prefers_popular_places=True,
                profile_completeness=0.6
            )
            
            logger.debug(
                "User profile built from interactions",
                user_id=user_id,
                completeness=profile.profile_completeness
            )
            
            return profile
            
        except Exception as e:
            logger.error(
                "Failed to build user profile",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def _update_profile_from_interaction(self, interaction: UserInteraction) -> None:
        """Update user profile based on interaction."""
        
        try:
            # Get current profile
            profile = await self.get_user_profile(interaction.user_id)
            if not profile:
                return
            
            # Update interaction count
            profile.total_interactions += 1
            
            # Get business details for profile updates
            # This would query the business from database
            # For now, we'll make basic updates
            
            updates = {
                'total_interactions': profile.total_interactions,
                'updated_at': datetime.utcnow()
            }
            
            # Update based on interaction type
            if interaction.interaction_type in [UserInteractionType.FAVORITE, UserInteractionType.REVIEW]:
                if interaction.rating_given and interaction.rating_given >= 4.0:
                    # Positive interaction - could update category preferences
                    pass
            
            # Save updated profile
            await self.update_user_profile(interaction.user_id, updates)
            
        except Exception as e:
            logger.error(
                "Failed to update profile from interaction",
                user_id=interaction.user_id,
                error=str(e)
            )
    
    async def _update_profile_from_feedback(self, feedback: RecommendationFeedback) -> None:
        """Update user profile based on recommendation feedback."""
        
        try:
            profile = await self.get_user_profile(feedback.user_id)
            if not profile:
                return
            
            # Adjust preferences based on feedback
            updates = {'updated_at': datetime.utcnow()}
            
            # If user found recommendation helpful, we can boost related preferences
            if feedback.helpful:
                # This would require knowing the business category from feedback
                pass
            
            # If user dismissed recommendation, we might reduce related preferences
            if feedback.dismissed:
                # This would require knowing what was dismissed
                pass
            
            await self.update_user_profile(feedback.user_id, updates)
            
        except Exception as e:
            logger.error(
                "Failed to update profile from feedback",
                user_id=feedback.user_id,
                error=str(e)
            )
    
    def _generate_cache_key(
        self,
        user_id: Optional[UUID],
        recommendation_type: RecommendationType,
        current_location: Optional[Dict[str, float]],
        context_business_id: Optional[UUID],
        limit: int,
        strategy: RecommendationStrategy
    ) -> str:
        """Generate cache key for recommendations."""
        
        # Create a hash-friendly key
        user_str = str(user_id) if user_id else "anonymous"
        
        location_str = ""
        if current_location:
            # Round location for cache efficiency
            lat = round(current_location.get('latitude', 0), 2)
            lon = round(current_location.get('longitude', 0), 2)
            location_str = f"{lat},{lon}"
        
        context_str = str(context_business_id) if context_business_id else ""
        
        cache_key = f"rec:{user_str}:{recommendation_type.value}:{location_str}:{context_str}:{limit}:{strategy.value}"
        
        return cache_key
    
    async def _get_cached_recommendations(self, cache_key: str) -> Optional[RecommendationResult]:
        """Get cached recommendation result."""
        
        try:
            cached_data = await get_cache(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return RecommendationResult(**data)
        except Exception as e:
            logger.warning(
                "Error retrieving cached recommendations",
                cache_key=cache_key,
                error=str(e)
            )
        
        return None
    
    async def _cache_recommendations(self, cache_key: str, result: RecommendationResult) -> None:
        """Cache recommendation result."""
        
        try:
            # Convert to dict for JSON serialization
            result_dict = result.dict()
            cached_data = json.dumps(result_dict, default=str)
            
            await set_cache(cache_key, cached_data, ttl=self.cache_ttl)
            
            logger.debug("Recommendations cached", cache_key=cache_key)
            
        except Exception as e:
            logger.warning(
                "Error caching recommendations",
                cache_key=cache_key,
                error=str(e)
            )
    
    async def _log_recommendation_request(
        self,
        request: RecommendationRequest,
        result: RecommendationResult
    ) -> None:
        """Log recommendation request for analytics."""
        
        try:
            # This would typically be sent to an analytics service
            # or background task queue
            
            analytics_data = {
                "user_id": str(request.user_id) if request.user_id else None,
                "recommendation_type": request.recommendation_type.value,
                "strategy_used": result.strategy_used.value,
                "recommendations_count": len(result.recommendations),
                "processing_time_ms": result.processing_time_ms,
                "average_confidence": result.average_confidence,
                "diversity_score": result.diversity_score,
                "novelty_score": result.novelty_score,
                "used_fallback": result.used_fallback,
                "personalization_applied": result.personalization_applied,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Store analytics data
            analytics_key = f"rec_analytics:{datetime.utcnow().timestamp()}"
            await set_cache(
                analytics_key,
                json.dumps(analytics_data, default=str),
                ttl=86400 * 30  # Keep for 30 days
            )
            
            logger.debug(
                "Recommendation analytics logged",
                user_id=request.user_id,
                recommendations_count=len(result.recommendations)
            )
            
        except Exception as e:
            logger.warning(
                "Error logging recommendation analytics",
                user_id=request.user_id,
                error=str(e)
            )