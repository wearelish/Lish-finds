"""
Core ranking engine for LishFind businesses.

Implements multiple ranking algorithms with configurable scoring factors.
"""

import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

import structlog

from ranking.models import (
    RankingAlgorithm,
    RankingConfig, 
    RankingFactors,
    BusinessRankingData,
    RankingResult,
    UserPreferences,
    RankingBatch,
    RankingBatchResult
)

logger = structlog.get_logger(__name__)


class RankingEngine:
    """Core ranking engine with multiple algorithms."""
    
    def __init__(self, config: Optional[RankingConfig] = None):
        self.config = config or RankingConfig()
        
        # Precomputed values for performance
        self._rating_normalizer = 5.0  # Max rating
        self._review_count_normalizers = {}  # Cached per-category
        
    async def rank_businesses(
        self,
        businesses: List[BusinessRankingData],
        config: Optional[RankingConfig] = None,
        user_preferences: Optional[UserPreferences] = None,
        user_location: Optional[Dict[str, float]] = None
    ) -> List[RankingResult]:
        """
        Rank a list of businesses according to the specified algorithm.
        
        Args:
            businesses: List of businesses to rank
            config: Ranking configuration (uses default if None)
            user_preferences: User preferences for personalization
            user_location: User location for distance calculations
            
        Returns:
            List of ranking results sorted by score (highest first)
        """
        
        start_time = time.time()
        ranking_config = config or self.config
        
        try:
            # Calculate individual factor scores for all businesses
            ranking_results = []
            
            for business in businesses:
                # Calculate base scores
                factors = await self._calculate_ranking_factors(
                    business, ranking_config, user_location
                )
                
                # Apply algorithm-specific scoring
                final_score = await self._apply_ranking_algorithm(
                    factors, ranking_config.algorithm
                )
                
                # Apply boosts and penalties
                final_score, boosts, penalties = await self._apply_boosts_and_penalties(
                    final_score, business, ranking_config
                )
                
                # Apply personalization if enabled
                personalization_adjustment = None
                if ranking_config.enable_personalization and user_preferences:
                    adjustment = await self._apply_personalization(
                        business, user_preferences, ranking_config
                    )
                    final_score *= (1.0 + adjustment)
                    personalization_adjustment = adjustment
                
                # Create ranking result
                result = RankingResult(
                    business_id=business.id,
                    final_score=max(0.0, final_score),  # Ensure non-negative
                    distance_score=factors.distance_score,
                    rating_score=factors.rating_score,
                    review_score=factors.review_count_score,
                    completeness_score=factors.completeness_score,
                    popularity_score=factors.popularity_score,
                    verification_score=factors.verification_score,
                    boosts_applied=boosts,
                    penalties_applied=penalties,
                    personalization_adjustment=personalization_adjustment,
                    algorithm_used=ranking_config.algorithm
                )
                
                ranking_results.append(result)
            
            # Sort by final score (descending)
            ranking_results.sort(key=lambda x: x.final_score, reverse=True)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Business ranking completed",
                total_businesses=len(businesses),
                algorithm=ranking_config.algorithm.value,
                processing_time_ms=processing_time
            )
            
            return ranking_results
            
        except Exception as e:
            logger.error(
                "Business ranking failed",
                total_businesses=len(businesses),
                algorithm=ranking_config.algorithm.value,
                error=str(e),
                exc_info=True
            )
            
            # Return unranked results as fallback
            return [
                RankingResult(
                    business_id=business.id,
                    final_score=0.5,  # Default score
                    algorithm_used=ranking_config.algorithm
                )
                for business in businesses
            ]
    
    async def _calculate_ranking_factors(
        self,
        business: BusinessRankingData,
        config: RankingConfig,
        user_location: Optional[Dict[str, float]]
    ) -> RankingFactors:
        """Calculate individual ranking factors for a business."""
        
        factors = RankingFactors()
        
        # Distance score
        if business.distance_km is not None and user_location:
            factors.distance_score = await self._calculate_distance_score(
                business.distance_km, config
            )
        
        # Rating score
        if business.rating is not None:
            factors.rating_score = await self._calculate_rating_score(
                float(business.rating), config
            )
        
        # Review count score
        factors.review_count_score = await self._calculate_review_score(
            business.review_count, business.category, config
        )
        
        # Completeness score
        factors.completeness_score = await self._calculate_completeness_score(business)
        
        # Popularity score
        if business.popularity_score is not None:
            factors.popularity_score = min(1.0, float(business.popularity_score) / 100.0)
        
        # Verification score
        factors.verification_score = await self._calculate_verification_score(business)
        
        return factors
    
    async def _calculate_distance_score(
        self,
        distance_km: float,
        config: RankingConfig
    ) -> float:
        """Calculate distance score (1.0 = very close, 0.0 = very far)."""
        
        if distance_km <= 0:
            return 1.0
        
        max_distance = config.max_distance_km or 50.0  # Default 50km
        
        if distance_km >= max_distance:
            return 0.0
        
        # Apply decay function
        normalized_distance = distance_km / max_distance
        
        if config.distance_decay_function == "linear":
            return 1.0 - normalized_distance
        elif config.distance_decay_function == "exponential":
            return math.exp(-3 * normalized_distance)  # Exponential decay
        elif config.distance_decay_function == "logarithmic":
            return 1.0 - math.log(1 + normalized_distance) / math.log(2)
        else:
            # Default to exponential
            return math.exp(-3 * normalized_distance)
    
    async def _calculate_rating_score(
        self,
        rating: float,
        config: RankingConfig
    ) -> float:
        """Calculate rating score with threshold bonus."""
        
        if rating <= 0:
            return 0.0
        
        # Base score (normalize to 0-1)
        base_score = rating / self._rating_normalizer
        
        # Apply threshold bonus
        if rating >= config.min_rating_threshold:
            bonus_factor = 1.0 + (rating - config.min_rating_threshold) * 0.1
            base_score *= bonus_factor
        
        return min(1.0, base_score)
    
    async def _calculate_review_score(
        self,
        review_count: int,
        category: str,
        config: RankingConfig
    ) -> float:
        """Calculate review count score with category-specific normalization."""
        
        if review_count < config.min_reviews_threshold:
            return 0.1  # Minimum score for businesses with few reviews
        
        # Get category-specific normalizer (cached)
        if category not in self._review_count_normalizers:
            # These would ideally come from database statistics
            category_normalizers = {
                "restaurant": 200,
                "cafe": 100,
                "hotel": 150,
                "retail": 80,
                "service": 50,
                "entertainment": 120,
            }
            self._review_count_normalizers[category] = category_normalizers.get(category, 100)
        
        normalizer = self._review_count_normalizers[category]
        
        # Logarithmic scaling to prevent domination by very high review counts
        normalized_score = math.log(1 + review_count) / math.log(1 + normalizer)
        
        return min(1.0, normalized_score)
    
    async def _calculate_completeness_score(self, business: BusinessRankingData) -> float:
        """Calculate profile completeness score."""
        
        # Define completeness factors with weights
        completeness_factors = {
            'has_description': 0.20,
            'has_photos': 0.25,
            'has_hours': 0.15,
            'has_contact': 0.15,
            'has_website': 0.10,
            'amenities_count': 0.10,  # Normalized by count
            'services_count': 0.05    # Normalized by count
        }
        
        total_score = 0.0
        
        # Boolean factors
        for factor, weight in completeness_factors.items():
            if factor in ['amenities_count', 'services_count']:
                continue
                
            if getattr(business, factor, False):
                total_score += weight
        
        # Count-based factors
        amenities_score = min(1.0, business.amenities_count / 10.0)  # Max at 10 amenities
        services_score = min(1.0, business.services_count / 8.0)     # Max at 8 services
        
        total_score += amenities_score * completeness_factors['amenities_count']
        total_score += services_score * completeness_factors['services_count']
        
        return min(1.0, total_score)
    
    async def _calculate_verification_score(self, business: BusinessRankingData) -> float:
        """Calculate verification and trust score."""
        
        score = 0.0
        
        # Base verification
        if business.verified:
            score += 0.8
        
        # Premium status
        if business.premium:
            score += 0.2
        
        # Recent activity (businesses updated recently score higher)
        if business.updated_at:
            days_since_update = (datetime.utcnow() - business.updated_at).days
            if days_since_update < 30:
                score += 0.1 * (1.0 - days_since_update / 30.0)
        
        # Recent reviews indicate active engagement
        if business.recent_reviews_count > 0:
            score += min(0.2, business.recent_reviews_count / 10.0)
        
        return min(1.0, score)
    
    async def _apply_ranking_algorithm(
        self,
        factors: RankingFactors,
        algorithm: RankingAlgorithm
    ) -> float:
        """Apply the specified ranking algorithm to calculate final score."""
        
        if algorithm == RankingAlgorithm.WEIGHTED_SCORE:
            return await self._weighted_score_algorithm(factors)
        elif algorithm == RankingAlgorithm.DISTANCE_PRIORITY:
            return await self._distance_priority_algorithm(factors)
        elif algorithm == RankingAlgorithm.QUALITY_PRIORITY:
            return await self._quality_priority_algorithm(factors)
        elif algorithm == RankingAlgorithm.POPULARITY_PRIORITY:
            return await self._popularity_priority_algorithm(factors)
        elif algorithm == RankingAlgorithm.BALANCED:
            return await self._balanced_algorithm(factors)
        else:
            # Default to weighted score
            return await self._weighted_score_algorithm(factors)
    
    async def _weighted_score_algorithm(self, factors: RankingFactors) -> float:
        """Standard weighted scoring algorithm."""
        
        score = 0.0
        
        if factors.distance_score is not None:
            score += factors.distance_score * factors.distance_weight
        
        if factors.rating_score is not None:
            score += factors.rating_score * factors.rating_weight
        
        if factors.review_count_score is not None:
            score += factors.review_count_score * factors.review_weight
        
        if factors.completeness_score is not None:
            score += factors.completeness_score * factors.completeness_weight
        
        if factors.popularity_score is not None:
            score += factors.popularity_score * factors.popularity_weight
        
        if factors.verification_score is not None:
            score += factors.verification_score * factors.verification_weight
        
        return score
    
    async def _distance_priority_algorithm(self, factors: RankingFactors) -> float:
        """Algorithm that prioritizes nearby businesses."""
        
        # Distance gets 50% weight, others share remaining 50%
        distance_weight = 0.5
        other_weights = 0.5 / 5  # Distribute among other factors
        
        score = 0.0
        
        if factors.distance_score is not None:
            score += factors.distance_score * distance_weight
        
        # Other factors get equal smaller weights
        for factor_score in [
            factors.rating_score,
            factors.review_count_score,
            factors.completeness_score,
            factors.popularity_score,
            factors.verification_score
        ]:
            if factor_score is not None:
                score += factor_score * other_weights
        
        return score
    
    async def _quality_priority_algorithm(self, factors: RankingFactors) -> float:
        """Algorithm that prioritizes high-quality businesses."""
        
        score = 0.0
        
        # Rating and reviews get higher weights
        if factors.rating_score is not None:
            score += factors.rating_score * 0.4
        
        if factors.review_count_score is not None:
            score += factors.review_count_score * 0.25
        
        if factors.verification_score is not None:
            score += factors.verification_score * 0.15
        
        # Other factors get smaller weights
        if factors.distance_score is not None:
            score += factors.distance_score * 0.1
        
        if factors.completeness_score is not None:
            score += factors.completeness_score * 0.05
        
        if factors.popularity_score is not None:
            score += factors.popularity_score * 0.05
        
        return score
    
    async def _popularity_priority_algorithm(self, factors: RankingFactors) -> float:
        """Algorithm that prioritizes popular and trending businesses."""
        
        score = 0.0
        
        # Popularity and engagement get higher weights
        if factors.popularity_score is not None:
            score += factors.popularity_score * 0.35
        
        if factors.review_count_score is not None:
            score += factors.review_count_score * 0.25
        
        if factors.rating_score is not None:
            score += factors.rating_score * 0.20
        
        # Other factors
        if factors.distance_score is not None:
            score += factors.distance_score * 0.1
        
        if factors.verification_score is not None:
            score += factors.verification_score * 0.05
        
        if factors.completeness_score is not None:
            score += factors.completeness_score * 0.05
        
        return score
    
    async def _balanced_algorithm(self, factors: RankingFactors) -> float:
        """Balanced algorithm with equal consideration for all factors."""
        
        # Equal weights for all factors
        weight = 1.0 / 6
        score = 0.0
        
        for factor_score in [
            factors.distance_score,
            factors.rating_score,
            factors.review_count_score,
            factors.completeness_score,
            factors.popularity_score,
            factors.verification_score
        ]:
            if factor_score is not None:
                score += factor_score * weight
        
        return score
    
    async def _apply_boosts_and_penalties(
        self,
        base_score: float,
        business: BusinessRankingData,
        config: RankingConfig
    ) -> Tuple[float, List[str], List[str]]:
        """Apply boosts and penalties to the base score."""
        
        score = base_score
        boosts_applied = []
        penalties_applied = []
        
        # Verification boost
        if business.verified and config.verified_boost > 1.0:
            score *= config.verified_boost
            boosts_applied.append("verified_business")
        
        # Premium boost
        if business.premium and config.premium_boost > 1.0:
            score *= config.premium_boost
            boosts_applied.append("premium_business")
        
        # Low rating penalty
        if (business.rating is not None and 
            float(business.rating) < config.min_rating_threshold and 
            config.low_rating_penalty < 1.0):
            score *= config.low_rating_penalty
            penalties_applied.append("low_rating")
        
        # Incomplete profile penalty
        completeness_score = await self._calculate_completeness_score(business)
        if completeness_score < 0.5 and config.incomplete_profile_penalty < 1.0:
            score *= config.incomplete_profile_penalty
            penalties_applied.append("incomplete_profile")
        
        # New business boost (encouraging new listings)
        if business.created_at:
            days_since_creation = (datetime.utcnow() - business.created_at).days
            if days_since_creation < 30:  # New business (less than 30 days)
                new_business_boost = 1.05
                score *= new_business_boost
                boosts_applied.append("new_business")
        
        # Trending business boost (based on recent reviews)
        if business.recent_reviews_count > 10:  # Lots of recent activity
            trending_boost = 1.1
            score *= trending_boost
            boosts_applied.append("trending_business")
        
        # Stale business penalty (not updated recently)
        if business.updated_at:
            days_since_update = (datetime.utcnow() - business.updated_at).days
            if days_since_update > 365:  # Not updated in over a year
                stale_penalty = 0.95
                score *= stale_penalty
                penalties_applied.append("stale_profile")
        
        return score, boosts_applied, penalties_applied
    
    async def _apply_personalization(
        self,
        business: BusinessRankingData,
        user_preferences: UserPreferences,
        config: RankingConfig
    ) -> float:
        """Apply personalization adjustments based on user preferences."""
        
        adjustment = 0.0
        max_adjustment = config.user_preference_weight
        
        # Category preference adjustment
        category_preference = user_preferences.category_preferences.get(
            business.category, 0.5  # Default neutral preference
        )
        
        # Adjust based on how much the user likes this category
        category_adjustment = (category_preference - 0.5) * max_adjustment * 2
        adjustment += category_adjustment
        
        # Rating preference
        if (user_preferences.prefer_high_rated and 
            business.rating is not None and 
            float(business.rating) >= user_preferences.min_preferred_rating):
            adjustment += max_adjustment * 0.3
        
        # Distance preference
        if (user_preferences.prefer_nearby and
            business.distance_km is not None and
            user_preferences.max_preferred_distance_km is not None and
            business.distance_km <= user_preferences.max_preferred_distance_km):
            adjustment += max_adjustment * 0.2
        
        # Price preference (if we have price data)
        # This would require price range data in business model
        
        # Amenities preference
        if hasattr(business, 'amenities') and user_preferences.preferred_amenities:
            # This would require amenities data in business model
            pass
        
        # Ensure adjustment is within reasonable bounds
        return max(-max_adjustment, min(max_adjustment, adjustment))
    
    async def rank_batch(self, batch: RankingBatch) -> RankingBatchResult:
        """Process a batch ranking request."""
        
        start_time = time.time()
        
        try:
            # Extract user location from batch context
            user_location = None
            if batch.user_location:
                user_location = batch.user_location
            elif batch.search_context and 'user_location' in batch.search_context:
                user_location = batch.search_context['user_location']
            
            # Perform ranking
            results = await self.rank_businesses(
                businesses=batch.businesses,
                config=batch.config,
                user_preferences=batch.user_preferences,
                user_location=user_location
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Calculate statistics
            scores = [result.final_score for result in results]
            score_distribution = {
                'min': min(scores) if scores else 0.0,
                'max': max(scores) if scores else 0.0,
                'mean': sum(scores) / len(scores) if scores else 0.0,
                'median': sorted(scores)[len(scores) // 2] if scores else 0.0
            }
            
            # Generate optimization suggestions
            optimization_suggestions = await self._generate_optimization_suggestions(
                results, batch.config
            )
            
            return RankingBatchResult(
                results=results,
                config_used=batch.config,
                total_businesses=len(batch.businesses),
                processing_time_ms=processing_time,
                algorithm_used=batch.config.algorithm,
                score_distribution=score_distribution,
                optimization_suggestions=optimization_suggestions
            )
            
        except Exception as e:
            logger.error(
                "Batch ranking failed",
                total_businesses=len(batch.businesses),
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _generate_optimization_suggestions(
        self,
        results: List[RankingResult],
        config: RankingConfig
    ) -> List[str]:
        """Generate suggestions for ranking optimization."""
        
        suggestions = []
        
        if not results:
            return suggestions
        
        scores = [result.final_score for result in results]
        
        # Check score distribution
        if len(set(scores)) == 1:
            suggestions.append("All businesses have the same score - consider adjusting weights")
        
        # Check if top results are all very similar
        top_5_scores = scores[:5]
        if len(top_5_scores) > 1:
            score_variance = sum((s - sum(top_5_scores)/len(top_5_scores))**2 for s in top_5_scores)
            if score_variance < 0.01:
                suggestions.append("Top results have very similar scores - consider increasing factor weights")
        
        # Check boost/penalty distribution
        total_boosts = sum(len(result.boosts_applied) for result in results)
        total_penalties = sum(len(result.penalties_applied) for result in results)
        
        if total_boosts == 0:
            suggestions.append("No boosts applied - consider lowering boost thresholds")
        
        if total_penalties == 0:
            suggestions.append("No penalties applied - consider adjusting penalty criteria")
        
        # Algorithm-specific suggestions
        if config.algorithm == RankingAlgorithm.DISTANCE_PRIORITY:
            distance_scores = [r.distance_score for r in results if r.distance_score is not None]
            if not distance_scores or max(distance_scores) < 0.5:
                suggestions.append("Distance priority algorithm but low distance scores - check max_distance_km setting")
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    def get_algorithm_presets(self) -> Dict[RankingAlgorithm, RankingConfig]:
        """Get preset configurations for different ranking algorithms."""
        
        presets = {}
        
        # Distance Priority preset
        distance_factors = RankingFactors(
            distance_weight=0.50,
            rating_weight=0.25,
            review_weight=0.10,
            completeness_weight=0.05,
            popularity_weight=0.05,
            verification_weight=0.05
        )
        
        presets[RankingAlgorithm.DISTANCE_PRIORITY] = RankingConfig(
            algorithm=RankingAlgorithm.DISTANCE_PRIORITY,
            factors=distance_factors,
            max_distance_km=25.0,
            distance_decay_function="exponential"
        )
        
        # Quality Priority preset
        quality_factors = RankingFactors(
            distance_weight=0.10,
            rating_weight=0.40,
            review_weight=0.25,
            completeness_weight=0.10,
            popularity_weight=0.10,
            verification_weight=0.05
        )
        
        presets[RankingAlgorithm.QUALITY_PRIORITY] = RankingConfig(
            algorithm=RankingAlgorithm.QUALITY_PRIORITY,
            factors=quality_factors,
            min_rating_threshold=4.0,
            verified_boost=1.3
        )
        
        # Popularity Priority preset
        popularity_factors = RankingFactors(
            distance_weight=0.15,
            rating_weight=0.20,
            review_weight=0.20,
            completeness_weight=0.05,
            popularity_weight=0.35,
            verification_weight=0.05
        )
        
        presets[RankingAlgorithm.POPULARITY_PRIORITY] = RankingConfig(
            algorithm=RankingAlgorithm.POPULARITY_PRIORITY,
            factors=popularity_factors
        )
        
        # Balanced preset (default)
        balanced_factors = RankingFactors()  # Uses default balanced weights
        
        presets[RankingAlgorithm.BALANCED] = RankingConfig(
            algorithm=RankingAlgorithm.BALANCED,
            factors=balanced_factors
        )
        
        return presets