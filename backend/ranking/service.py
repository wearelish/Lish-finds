"""
High-level ranking service for LishFind backend.

Integrates ranking engine with business data and provides caching.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.redis import get_cache, set_cache
from models.business import Business, BusinessStatus
from models.user import User
from ranking.engine import RankingEngine
from ranking.models import (
    RankingConfig,
    RankingAlgorithm, 
    BusinessRankingData,
    RankingResult,
    UserPreferences,
    RankingBatch,
    RankingBatchResult
)

logger = structlog.get_logger(__name__)


class RankingService:
    """High-level ranking service with business data integration."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ranking_engine = RankingEngine()
        self.cache_ttl = 3600  # 1 hour cache for ranking results
        self.preferences_cache_ttl = 86400  # 24 hours for user preferences
    
    async def rank_search_results(
        self,
        business_ids: List[UUID],
        algorithm: RankingAlgorithm = RankingAlgorithm.BALANCED,
        user_id: Optional[UUID] = None,
        user_location: Optional[Dict[str, float]] = None,
        config_override: Optional[RankingConfig] = None
    ) -> List[RankingResult]:
        """
        Rank businesses from search results.
        
        Args:
            business_ids: List of business IDs to rank
            algorithm: Ranking algorithm to use
            user_id: Optional user ID for personalization
            user_location: User location for distance calculations
            config_override: Optional custom ranking configuration
            
        Returns:
            List of ranking results sorted by score
        """
        
        try:
            # Load business data
            business_data = await self._load_business_data(business_ids, user_location)
            
            if not business_data:
                logger.warning("No business data loaded for ranking", business_ids=business_ids)
                return []
            
            # Get ranking configuration
            config = config_override or self._get_algorithm_config(algorithm)
            
            # Load user preferences if available
            user_preferences = None
            if user_id and config.enable_personalization:
                user_preferences = await self._load_user_preferences(user_id)
            
            # Perform ranking
            results = await self.ranking_engine.rank_businesses(
                businesses=business_data,
                config=config,
                user_preferences=user_preferences,
                user_location=user_location
            )
            
            # Cache results for performance
            await self._cache_ranking_results(business_ids, results, config, user_id)
            
            logger.info(
                "Business ranking completed",
                total_businesses=len(business_data),
                algorithm=algorithm.value,
                user_id=user_id,
                has_user_location=user_location is not None
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Ranking search results failed",
                business_ids=business_ids,
                algorithm=algorithm.value,
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            
            # Return default ranking (by business ID order)
            return [
                RankingResult(
                    business_id=business_id,
                    final_score=0.5,
                    algorithm_used=algorithm
                )
                for business_id in business_ids
            ]
    
    async def rank_businesses_batch(
        self,
        batch_request: RankingBatch
    ) -> RankingBatchResult:
        """Process a batch ranking request."""
        
        try:
            result = await self.ranking_engine.rank_batch(batch_request)
            
            logger.info(
                "Batch ranking completed",
                total_businesses=result.total_businesses,
                processing_time_ms=result.processing_time_ms,
                algorithm=result.algorithm_used.value
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Batch ranking failed",
                total_businesses=len(batch_request.businesses),
                error=str(e),
                exc_info=True
            )
            raise
    
    async def update_user_preferences(
        self,
        user_id: UUID,
        preferences: UserPreferences
    ) -> None:
        """Update user preferences for personalized ranking."""
        
        try:
            # In a real implementation, this would save to database
            # For now, we'll cache the preferences
            
            cache_key = f"user_preferences:{user_id}"
            preferences_data = preferences.dict()
            
            await set_cache(
                cache_key,
                json.dumps(preferences_data, default=str),
                ttl=self.preferences_cache_ttl
            )
            
            logger.info(
                "User preferences updated",
                user_id=user_id,
                category_preferences_count=len(preferences.category_preferences)
            )
            
        except Exception as e:
            logger.error(
                "Failed to update user preferences",
                user_id=user_id,
                error=str(e)
            )
    
    async def get_ranking_analytics(
        self,
        business_ids: List[UUID],
        algorithm: RankingAlgorithm = RankingAlgorithm.BALANCED
    ) -> Dict[str, Any]:
        """Get ranking analytics for businesses."""
        
        try:
            # Load business data
            business_data = await self._load_business_data(business_ids)
            
            # Get default config for algorithm
            config = self._get_algorithm_config(algorithm)
            
            # Perform ranking to get detailed scores
            results = await self.ranking_engine.rank_businesses(
                businesses=business_data,
                config=config
            )
            
            # Calculate analytics
            analytics = {
                "total_businesses": len(results),
                "algorithm_used": algorithm.value,
                "score_distribution": self._calculate_score_distribution(results),
                "factor_analysis": self._analyze_ranking_factors(results),
                "top_performers": [
                    {"business_id": str(r.business_id), "score": r.final_score}
                    for r in results[:10]
                ],
                "bottom_performers": [
                    {"business_id": str(r.business_id), "score": r.final_score}
                    for r in results[-5:]
                ],
                "boost_penalty_stats": self._analyze_boosts_penalties(results)
            }
            
            return analytics
            
        except Exception as e:
            logger.error(
                "Failed to generate ranking analytics",
                business_ids=business_ids,
                error=str(e)
            )
            return {}
    
    async def _load_business_data(
        self,
        business_ids: List[UUID],
        user_location: Optional[Dict[str, float]] = None
    ) -> List[BusinessRankingData]:
        """Load business data for ranking calculations."""
        
        try:
            # Build query to load business data
            query = select(Business).where(
                and_(
                    Business.id.in_(business_ids),
                    Business.status == BusinessStatus.VERIFIED
                )
            )
            
            result = await self.session.execute(query)
            businesses = result.scalars().all()
            
            # Convert to ranking data format
            business_data = []
            
            for business in businesses:
                # Calculate distance if user location provided
                distance_km = None
                if (user_location and 
                    business.latitude and business.longitude):
                    distance_km = self._calculate_distance(
                        user_location['latitude'],
                        user_location['longitude'],
                        float(business.latitude),
                        float(business.longitude)
                    )
                
                # Calculate profile completeness factors
                has_description = bool(business.description and business.description.strip())
                has_photos = bool(business.photos and len(business.photos) > 0)
                has_hours = bool(business.opening_hours)
                has_contact = bool(business.phone or business.email)
                has_website = bool(business.website)
                amenities_count = len(business.amenities or [])
                services_count = len(business.services or [])
                
                # Calculate recent reviews count (last 30 days)
                recent_reviews_count = 0
                if business.last_review_date:
                    days_since_review = (datetime.utcnow() - business.last_review_date).days
                    if days_since_review <= 30:
                        # Estimate based on review frequency
                        recent_reviews_count = max(1, business.review_count // 30)
                
                ranking_data = BusinessRankingData(
                    id=business.id,
                    name=business.name,
                    category=business.category,
                    latitude=business.latitude,
                    longitude=business.longitude,
                    distance_km=distance_km,
                    rating=business.rating,
                    review_count=business.review_count,
                    verified=business.verified,
                    premium=getattr(business, 'premium', False),  # If premium field exists
                    has_description=has_description,
                    has_photos=has_photos,
                    has_hours=has_hours,
                    has_contact=has_contact,
                    has_website=has_website,
                    amenities_count=amenities_count,
                    services_count=services_count,
                    popularity_score=business.popularity_score,
                    recent_reviews_count=recent_reviews_count,
                    created_at=business.created_at,
                    updated_at=business.updated_at,
                    last_review_date=business.last_review_date
                )
                
                business_data.append(ranking_data)
            
            logger.debug(
                "Business data loaded for ranking",
                requested_count=len(business_ids),
                loaded_count=len(business_data)
            )
            
            return business_data
            
        except Exception as e:
            logger.error(
                "Failed to load business data",
                business_ids=business_ids,
                error=str(e)
            )
            return []
    
    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two coordinates in kilometers."""
        
        import math
        
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    async def _load_user_preferences(self, user_id: UUID) -> Optional[UserPreferences]:
        """Load user preferences for personalization."""
        
        try:
            # Try cache first
            cache_key = f"user_preferences:{user_id}"
            cached_data = await get_cache(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return UserPreferences(**data)
            
            # In production, this would load from database
            # For now, return default preferences
            default_preferences = UserPreferences(
                user_id=user_id,
                category_preferences={},
                prefer_high_rated=True,
                min_preferred_rating=4.0,
                prefer_nearby=True,
                max_preferred_distance_km=10.0
            )
            
            # Cache the default preferences
            await set_cache(
                cache_key,
                json.dumps(default_preferences.dict(), default=str),
                ttl=self.preferences_cache_ttl
            )
            
            return default_preferences
            
        except Exception as e:
            logger.error(
                "Failed to load user preferences",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    def _get_algorithm_config(self, algorithm: RankingAlgorithm) -> RankingConfig:
        """Get configuration for the specified algorithm."""
        
        presets = self.ranking_engine.get_algorithm_presets()
        return presets.get(algorithm, RankingConfig(algorithm=algorithm))
    
    async def _cache_ranking_results(
        self,
        business_ids: List[UUID],
        results: List[RankingResult],
        config: RankingConfig,
        user_id: Optional[UUID]
    ) -> None:
        """Cache ranking results for performance."""
        
        try:
            # Create cache key based on inputs
            business_ids_str = ",".join(str(bid) for bid in sorted(business_ids))
            user_str = str(user_id) if user_id else "anonymous"
            algorithm_str = config.algorithm.value
            
            cache_key = f"ranking:{hash(business_ids_str)}:{user_str}:{algorithm_str}"
            
            # Serialize results
            results_data = [result.dict() for result in results]
            cached_data = json.dumps(results_data, default=str)
            
            await set_cache(cache_key, cached_data, ttl=self.cache_ttl)
            
            logger.debug(
                "Ranking results cached",
                cache_key=cache_key,
                results_count=len(results)
            )
            
        except Exception as e:
            logger.warning(
                "Failed to cache ranking results",
                error=str(e)
            )
    
    def _calculate_score_distribution(self, results: List[RankingResult]) -> Dict[str, float]:
        """Calculate score distribution statistics."""
        
        if not results:
            return {}
        
        scores = [result.final_score for result in results]
        scores.sort()
        
        return {
            "min": min(scores),
            "max": max(scores),
            "mean": sum(scores) / len(scores),
            "median": scores[len(scores) // 2],
            "std_dev": (
                sum((score - sum(scores) / len(scores)) ** 2 for score in scores) / len(scores)
            ) ** 0.5,
            "percentile_25": scores[len(scores) // 4],
            "percentile_75": scores[3 * len(scores) // 4]
        }
    
    def _analyze_ranking_factors(self, results: List[RankingResult]) -> Dict[str, Any]:
        """Analyze ranking factors contribution."""
        
        if not results:
            return {}
        
        factor_analysis = {}
        
        # Calculate average scores for each factor
        factors = [
            "distance_score", "rating_score", "review_score",
            "completeness_score", "popularity_score", "verification_score"
        ]
        
        for factor in factors:
            scores = [
                getattr(result, factor) for result in results 
                if getattr(result, factor) is not None
            ]
            
            if scores:
                factor_analysis[factor] = {
                    "average": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "count": len(scores)
                }
            else:
                factor_analysis[factor] = {
                    "average": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0
                }
        
        return factor_analysis
    
    def _analyze_boosts_penalties(self, results: List[RankingResult]) -> Dict[str, Any]:
        """Analyze applied boosts and penalties."""
        
        boost_counts = {}
        penalty_counts = {}
        
        for result in results:
            for boost in result.boosts_applied:
                boost_counts[boost] = boost_counts.get(boost, 0) + 1
            
            for penalty in result.penalties_applied:
                penalty_counts[penalty] = penalty_counts.get(penalty, 0) + 1
        
        return {
            "total_results": len(results),
            "boosts_applied": boost_counts,
            "penalties_applied": penalty_counts,
            "businesses_with_boosts": len([r for r in results if r.boosts_applied]),
            "businesses_with_penalties": len([r for r in results if r.penalties_applied])
        }
    
    async def get_algorithm_comparison(
        self,
        business_ids: List[UUID],
        user_location: Optional[Dict[str, float]] = None
    ) -> Dict[RankingAlgorithm, List[RankingResult]]:
        """Compare ranking results across different algorithms."""
        
        try:
            # Load business data once
            business_data = await self._load_business_data(business_ids, user_location)
            
            if not business_data:
                return {}
            
            comparison_results = {}
            
            # Test all algorithms
            algorithms = [
                RankingAlgorithm.BALANCED,
                RankingAlgorithm.DISTANCE_PRIORITY,
                RankingAlgorithm.QUALITY_PRIORITY,
                RankingAlgorithm.POPULARITY_PRIORITY
            ]
            
            for algorithm in algorithms:
                config = self._get_algorithm_config(algorithm)
                
                results = await self.ranking_engine.rank_businesses(
                    businesses=business_data,
                    config=config,
                    user_location=user_location
                )
                
                comparison_results[algorithm] = results
            
            logger.info(
                "Algorithm comparison completed",
                algorithms_tested=len(algorithms),
                businesses_count=len(business_data)
            )
            
            return comparison_results
            
        except Exception as e:
            logger.error(
                "Algorithm comparison failed",
                error=str(e)
            )
            return {}
    
    async def optimize_ranking_config(
        self,
        business_ids: List[UUID],
        target_metric: str = "score_variance",
        user_location: Optional[Dict[str, float]] = None
    ) -> RankingConfig:
        """
        Optimize ranking configuration based on target metric.
        
        This is a simplified optimization - in production you'd use
        more sophisticated techniques like grid search or genetic algorithms.
        """
        
        try:
            business_data = await self._load_business_data(business_ids, user_location)
            
            if not business_data:
                return RankingConfig()
            
            best_config = RankingConfig()
            best_score = float('-inf')
            
            # Test different weight combinations
            weight_combinations = [
                # Balanced
                [0.20, 0.25, 0.20, 0.15, 0.15, 0.05],
                # Distance focused
                [0.40, 0.20, 0.15, 0.10, 0.10, 0.05],
                # Quality focused
                [0.15, 0.35, 0.25, 0.10, 0.10, 0.05],
                # Popularity focused
                [0.15, 0.20, 0.20, 0.10, 0.30, 0.05]
            ]
            
            for weights in weight_combinations:
                # Create config with these weights
                from ranking.models import RankingFactors
                factors = RankingFactors(
                    distance_weight=weights[0],
                    rating_weight=weights[1],
                    review_weight=weights[2],
                    completeness_weight=weights[3],
                    popularity_weight=weights[4],
                    verification_weight=weights[5]
                )
                
                config = RankingConfig(factors=factors)
                
                # Test this configuration
                results = await self.ranking_engine.rank_businesses(
                    businesses=business_data,
                    config=config,
                    user_location=user_location
                )
                
                # Calculate optimization metric
                if target_metric == "score_variance":
                    scores = [r.final_score for r in results]
                    variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
                    metric_score = variance  # Higher variance = better differentiation
                elif target_metric == "top_quality_bias":
                    # Prefer configurations that put high-rated businesses on top
                    top_5_results = results[:5]
                    avg_top_rating = sum(
                        r.rating_score or 0 for r in top_5_results
                    ) / len(top_5_results)
                    metric_score = avg_top_rating
                else:
                    metric_score = 0
                
                if metric_score > best_score:
                    best_score = metric_score
                    best_config = config
            
            logger.info(
                "Ranking configuration optimized",
                target_metric=target_metric,
                best_score=best_score,
                businesses_tested=len(business_data)
            )
            
            return best_config
            
        except Exception as e:
            logger.error(
                "Ranking optimization failed",
                target_metric=target_metric,
                error=str(e)
            )
            return RankingConfig()  # Return default config