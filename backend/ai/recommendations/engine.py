"""
Core recommendation engine implementing multiple recommendation strategies.

Provides collaborative filtering, content-based filtering, and AI-powered recommendations.
"""

import json
import math
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from uuid import UUID

import structlog
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ai.providers.factory import get_ai_provider
from ai.recommendations.models import (
    RecommendationStrategy,
    RecommendationType,
    UserProfile,
    BusinessRecommendation,
    RecommendationRequest,
    RecommendationResult,
    UserInteraction,
    UserInteractionType
)
from models.business import Business, BusinessStatus
from models.user import User

logger = structlog.get_logger(__name__)


class RecommendationEngine:
    """Core recommendation engine with multiple strategies."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ai_provider = None
        
        # Strategy weights for hybrid recommendations
        self.strategy_weights = {
            RecommendationStrategy.COLLABORATIVE_FILTERING: 0.3,
            RecommendationStrategy.CONTENT_BASED: 0.25,
            RecommendationStrategy.AI_POWERED: 0.2,
            RecommendationStrategy.TRENDING: 0.15,
            RecommendationStrategy.LOCATION_BASED: 0.1
        }
    
    async def generate_recommendations(
        self,
        request: RecommendationRequest,
        user_profile: Optional[UserProfile] = None
    ) -> RecommendationResult:
        """
        Generate recommendations based on the request and strategy.
        
        Args:
            request: Recommendation request with parameters
            user_profile: Optional user profile for personalization
            
        Returns:
            RecommendationResult with recommended businesses
        """
        
        start_time = time.time()
        
        try:
            # Load candidate businesses
            candidates = await self._load_candidate_businesses(request)
            
            if not candidates:
                return self._create_empty_result(request, "No candidate businesses found")
            
            logger.debug(
                "Loaded candidate businesses",
                count=len(candidates),
                user_id=request.user_id,
                strategy=request.strategy.value
            )
            
            # Apply the specified strategy
            if request.strategy == RecommendationStrategy.COLLABORATIVE_FILTERING:
                recommendations = await self._collaborative_filtering(request, candidates, user_profile)
            elif request.strategy == RecommendationStrategy.CONTENT_BASED:
                recommendations = await self._content_based_filtering(request, candidates, user_profile)
            elif request.strategy == RecommendationStrategy.AI_POWERED:
                recommendations = await self._ai_powered_recommendations(request, candidates, user_profile)
            elif request.strategy == RecommendationStrategy.TRENDING:
                recommendations = await self._trending_recommendations(request, candidates)
            elif request.strategy == RecommendationStrategy.LOCATION_BASED:
                recommendations = await self._location_based_recommendations(request, candidates)
            elif request.strategy == RecommendationStrategy.HYBRID:
                recommendations = await self._hybrid_recommendations(request, candidates, user_profile)
            else:
                recommendations = await self._personalized_recommendations(request, candidates, user_profile)
            
            # Apply diversity and ranking
            final_recommendations = await self._apply_diversity_and_ranking(
                recommendations, request.diversity_factor, request.limit
            )
            
            # Calculate quality metrics
            avg_confidence = sum(r.confidence_score for r in final_recommendations) / len(final_recommendations) if final_recommendations else 0.0
            diversity_score = await self._calculate_diversity_score(final_recommendations)
            novelty_score = await self._calculate_novelty_score(final_recommendations, user_profile)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = RecommendationResult(
                recommendations=final_recommendations,
                request_type=request.recommendation_type,
                strategy_used=request.strategy,
                total_candidates=len(candidates),
                processing_time_ms=processing_time,
                user_id=request.user_id,
                average_confidence=avg_confidence,
                diversity_score=diversity_score,
                novelty_score=novelty_score,
                strategy_explanation=self._get_strategy_explanation(request.strategy),
                personalization_applied=user_profile is not None
            )
            
            logger.info(
                "Recommendations generated successfully",
                user_id=request.user_id,
                strategy=request.strategy.value,
                recommendations_count=len(final_recommendations),
                avg_confidence=avg_confidence,
                processing_time_ms=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Recommendation generation failed",
                user_id=request.user_id,
                strategy=request.strategy.value,
                error=str(e),
                processing_time_ms=processing_time,
                exc_info=True
            )
            
            # Return fallback recommendations
            return await self._fallback_recommendations(request, str(e))
    
    async def _load_candidate_businesses(self, request: RecommendationRequest) -> List[Business]:
        """Load candidate businesses for recommendations."""
        
        try:
            query = select(Business).where(
                and_(
                    Business.status == BusinessStatus.VERIFIED,
                    Business.verified == True
                )
            )
            
            # Apply filters
            conditions = []
            
            if request.categories:
                conditions.append(Business.category.in_(request.categories))
            
            if request.min_rating:
                conditions.append(Business.rating >= request.min_rating)
            
            # Location-based filtering
            if request.current_location and request.max_distance_km:
                # This would use PostGIS for distance filtering
                # For now, we'll load all and filter later
                pass
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Limit candidates to reasonable number for performance
            query = query.limit(500)
            
            result = await self.session.execute(query)
            candidates = result.scalars().all()
            
            # Apply distance filtering if location provided
            if request.current_location and request.max_distance_km:
                filtered_candidates = []
                user_lat = request.current_location['latitude']
                user_lon = request.current_location['longitude']
                
                for business in candidates:
                    if business.latitude and business.longitude:
                        distance = self._calculate_distance(
                            user_lat, user_lon,
                            float(business.latitude), float(business.longitude)
                        )
                        if distance <= request.max_distance_km:
                            filtered_candidates.append(business)
                
                candidates = filtered_candidates
            
            return candidates
            
        except Exception as e:
            logger.error("Failed to load candidate businesses", error=str(e))
            return []
    
    async def _collaborative_filtering(
        self,
        request: RecommendationRequest,
        candidates: List[Business],
        user_profile: Optional[UserProfile]
    ) -> List[BusinessRecommendation]:
        """Generate recommendations using collaborative filtering."""
        
        if not request.user_id:
            # Can't do collaborative filtering without user ID
            return await self._content_based_filtering(request, candidates, user_profile)
        
        try:
            # Find similar users based on interaction patterns
            similar_users = await self._find_similar_users(request.user_id, limit=20)
            
            if not similar_users:
                logger.warning("No similar users found for collaborative filtering")
                return await self._content_based_filtering(request, candidates, user_profile)
            
            # Get businesses liked by similar users
            similar_user_ids = [user_id for user_id, _ in similar_users]
            recommended_businesses = await self._get_businesses_liked_by_users(similar_user_ids)
            
            # Score businesses based on similarity weights
            business_scores = defaultdict(float)
            business_recommenders = defaultdict(list)
            
            for user_id, similarity in similar_users:
                user_businesses = recommended_businesses.get(user_id, [])
                for business_id, interaction_score in user_businesses:
                    if any(b.id == business_id for b in candidates):
                        business_scores[business_id] += similarity * interaction_score
                        business_recommenders[business_id].append(user_id)
            
            # Create recommendations
            recommendations = []
            candidate_lookup = {b.id: b for b in candidates}
            
            for business_id, score in sorted(business_scores.items(), key=lambda x: x[1], reverse=True):
                if business_id in candidate_lookup:
                    business = candidate_lookup[business_id]
                    
                    recommendation = BusinessRecommendation(
                        business_id=business.id,
                        business_name=business.name,
                        category=business.category,
                        recommendation_score=min(1.0, score / 5.0),  # Normalize score
                        confidence_score=min(1.0, len(business_recommenders[business_id]) / 10.0),
                        strategy_used=RecommendationStrategy.COLLABORATIVE_FILTERING,
                        reason=f"Users with similar tastes also liked this {business.category}",
                        explanation_factors=[
                            f"Recommended by {len(business_recommenders[business_id])} similar users",
                            f"High similarity score: {score:.2f}"
                        ],
                        rating=business.rating,
                        review_count=business.review_count,
                        price_range=business.price_range
                    )
                    
                    # Add distance if location available
                    if request.current_location and business.latitude and business.longitude:
                        recommendation.distance_km = self._calculate_distance(
                            request.current_location['latitude'],
                            request.current_location['longitude'],
                            float(business.latitude),
                            float(business.longitude)
                        )
                    
                    recommendations.append(recommendation)
            
            return recommendations[:request.limit * 2]  # Return more for diversity filtering
            
        except Exception as e:
            logger.error("Collaborative filtering failed", error=str(e))
            return []
    
    async def _content_based_filtering(
        self,
        request: RecommendationRequest,
        candidates: List[Business],
        user_profile: Optional[UserProfile]
    ) -> List[BusinessRecommendation]:
        """Generate recommendations using content-based filtering."""
        
        try:
            # If we have a context business, find similar businesses
            if request.context_business_id:
                return await self._find_similar_businesses(
                    request.context_business_id, candidates, request
                )
            
            # Use user profile preferences if available
            if user_profile:
                return await self._profile_based_recommendations(
                    user_profile, candidates, request
                )
            
            # Fallback to popular businesses in preferred categories
            recommendations = []
            
            for business in candidates:
                # Calculate content-based score
                score = 0.0
                confidence = 0.5
                factors = []
                
                # Rating and popularity
                if business.rating:
                    score += float(business.rating) / 5.0 * 0.4
                    factors.append(f"High rating: {business.rating}")
                
                if business.review_count > 10:
                    review_score = min(1.0, business.review_count / 100.0)
                    score += review_score * 0.3
                    factors.append(f"Popular with {business.review_count} reviews")
                
                # Verification and completeness
                if business.verified:
                    score += 0.2
                    factors.append("Verified business")
                    confidence += 0.2
                
                if business.photos and len(business.photos) > 0:
                    score += 0.1
                    factors.append("Has photos")
                
                # Distance bonus if location available
                distance_km = None
                if request.current_location and business.latitude and business.longitude:
                    distance_km = self._calculate_distance(
                        request.current_location['latitude'],
                        request.current_location['longitude'],
                        float(business.latitude),
                        float(business.longitude)
                    )
                    
                    if distance_km <= 5.0:  # Within 5km gets bonus
                        score += 0.1 * (1.0 - distance_km / 5.0)
                        factors.append("Nearby location")
                
                recommendation = BusinessRecommendation(
                    business_id=business.id,
                    business_name=business.name,
                    category=business.category,
                    recommendation_score=min(1.0, score),
                    confidence_score=min(1.0, confidence),
                    strategy_used=RecommendationStrategy.CONTENT_BASED,
                    reason=f"High-quality {business.category} matching your preferences",
                    explanation_factors=factors,
                    rating=business.rating,
                    review_count=business.review_count,
                    distance_km=distance_km,
                    price_range=business.price_range
                )
                
                recommendations.append(recommendation)
            
            # Sort by score
            recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
            return recommendations[:request.limit * 2]
            
        except Exception as e:
            logger.error("Content-based filtering failed", error=str(e))
            return []
    
    async def _ai_powered_recommendations(
        self,
        request: RecommendationRequest,
        candidates: List[Business],
        user_profile: Optional[UserProfile]
    ) -> List[BusinessRecommendation]:
        """Generate recommendations using AI analysis."""
        
        try:
            if not self.ai_provider:
                self.ai_provider = get_ai_provider()
            
            # Prepare context for AI
            context = {
                "user_preferences": user_profile.dict() if user_profile else {},
                "search_intent": request.search_intent.dict() if request.search_intent else {},
                "current_location": request.current_location,
                "recommendation_type": request.recommendation_type.value,
                "time_context": {
                    "current_time": datetime.now().isoformat(),
                    "day_of_week": request.day_of_week,
                    "for_time": request.for_time.isoformat() if request.for_time else None
                }
            }
            
            # Prepare business data for AI analysis
            business_data = []
            for business in candidates[:50]:  # Limit for AI processing
                business_info = {
                    "id": str(business.id),
                    "name": business.name,
                    "category": business.category,
                    "rating": float(business.rating) if business.rating else None,
                    "review_count": business.review_count,
                    "price_range": business.price_range,
                    "amenities": business.amenities or [],
                    "services": business.services or [],
                    "verified": business.verified,
                    "description": business.description
                }
                
                # Add distance if available
                if request.current_location and business.latitude and business.longitude:
                    business_info["distance_km"] = self._calculate_distance(
                        request.current_location['latitude'],
                        request.current_location['longitude'],
                        float(business.latitude),
                        float(business.longitude)
                    )
                
                business_data.append(business_info)
            
            # Create AI prompt
            prompt = f"""
            Analyze the following businesses and recommend the top {request.limit} for this user context:
            
            User Context: {json.dumps(context, indent=2)}
            
            Businesses: {json.dumps(business_data, indent=2)}
            
            Please provide recommendations in JSON format with the following structure:
            {{
                "recommendations": [
                    {{
                        "business_id": "uuid",
                        "recommendation_score": 0.85,
                        "confidence_score": 0.90,
                        "reason": "Brief explanation",
                        "explanation_factors": ["factor1", "factor2"],
                        "matches_user_preferences": ["preference1", "preference2"]
                    }}
                ]
            }}
            
            Consider factors like user preferences, location, time context, business quality, and relevance.
            """
            
            # Get AI recommendations
            ai_response = await self.ai_provider.generate_structured_response(
                prompt=prompt,
                response_format={
                    "type": "object",
                    "properties": {
                        "recommendations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "business_id": {"type": "string"},
                                    "recommendation_score": {"type": "number"},
                                    "confidence_score": {"type": "number"},
                                    "reason": {"type": "string"},
                                    "explanation_factors": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "matches_user_preferences": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["business_id", "recommendation_score", "confidence_score", "reason"]
                            }
                        }
                    }
                }
            )
            
            if not ai_response.success or not ai_response.data:
                logger.warning("AI recommendation generation failed, using fallback")
                return await self._content_based_filtering(request, candidates, user_profile)
            
            # Convert AI response to recommendations
            recommendations = []
            business_lookup = {str(b.id): b for b in candidates}
            
            for ai_rec in ai_response.data.get("recommendations", []):
                business_id = ai_rec["business_id"]
                if business_id in business_lookup:
                    business = business_lookup[business_id]
                    
                    recommendation = BusinessRecommendation(
                        business_id=business.id,
                        business_name=business.name,
                        category=business.category,
                        recommendation_score=ai_rec["recommendation_score"],
                        confidence_score=ai_rec["confidence_score"],
                        strategy_used=RecommendationStrategy.AI_POWERED,
                        reason=ai_rec["reason"],
                        explanation_factors=ai_rec.get("explanation_factors", []),
                        rating=business.rating,
                        review_count=business.review_count,
                        price_range=business.price_range,
                        matches_user_preferences=ai_rec.get("matches_user_preferences", [])
                    )
                    
                    # Add distance if location available
                    if request.current_location and business.latitude and business.longitude:
                        recommendation.distance_km = self._calculate_distance(
                            request.current_location['latitude'],
                            request.current_location['longitude'],
                            float(business.latitude),
                            float(business.longitude)
                        )
                    
                    recommendations.append(recommendation)
            
            logger.info(
                "AI-powered recommendations generated",
                recommendations_count=len(recommendations),
                user_id=request.user_id
            )
            
            return recommendations
            
        except Exception as e:
            logger.error("AI-powered recommendations failed", error=str(e))
            return await self._content_based_filtering(request, candidates, user_profile)
    
    async def _trending_recommendations(
        self,
        request: RecommendationRequest,
        candidates: List[Business]
    ) -> List[BusinessRecommendation]:
        """Generate trending business recommendations."""
        
        try:
            # Calculate trending score based on recent activity
            trending_businesses = []
            
            for business in candidates:
                trending_score = 0.0
                factors = []
                
                # Recent reviews boost
                if business.last_review_date:
                    days_since_review = (datetime.utcnow() - business.last_review_date).days
                    if days_since_review <= 30:
                        trending_score += 0.4 * (1.0 - days_since_review / 30.0)
                        factors.append("Recently reviewed")
                
                # High rating with decent review count
                if business.rating and business.rating >= 4.0 and business.review_count >= 10:
                    trending_score += 0.3
                    factors.append(f"High rated ({business.rating}★)")
                
                # Popularity score if available
                if business.popularity_score:
                    trending_score += float(business.popularity_score) / 100.0 * 0.2
                    factors.append("Popular venue")
                
                # Newer businesses get a boost
                if business.created_at:
                    days_since_creation = (datetime.utcnow() - business.created_at).days
                    if days_since_creation <= 365:  # Less than a year old
                        trending_score += 0.1 * (1.0 - days_since_creation / 365.0)
                        factors.append("New business")
                
                # Distance factor if location available
                distance_km = None
                if request.current_location and business.latitude and business.longitude:
                    distance_km = self._calculate_distance(
                        request.current_location['latitude'],
                        request.current_location['longitude'],
                        float(business.latitude),
                        float(business.longitude)
                    )
                
                if trending_score > 0.2:  # Only include businesses with decent trending score
                    recommendation = BusinessRecommendation(
                        business_id=business.id,
                        business_name=business.name,
                        category=business.category,
                        recommendation_score=min(1.0, trending_score),
                        confidence_score=0.7,  # Trending is reasonably reliable
                        strategy_used=RecommendationStrategy.TRENDING,
                        reason=f"Trending {business.category} in your area",
                        explanation_factors=factors,
                        rating=business.rating,
                        review_count=business.review_count,
                        distance_km=distance_km,
                        price_range=business.price_range
                    )
                    
                    trending_businesses.append(recommendation)
            
            # Sort by trending score
            trending_businesses.sort(key=lambda x: x.recommendation_score, reverse=True)
            
            return trending_businesses[:request.limit * 2]
            
        except Exception as e:
            logger.error("Trending recommendations failed", error=str(e))
            return []
    
    async def _location_based_recommendations(
        self,
        request: RecommendationRequest,
        candidates: List[Business]
    ) -> List[BusinessRecommendation]:
        """Generate location-based recommendations."""
        
        if not request.current_location:
            return await self._content_based_filtering(request, candidates, None)
        
        try:
            location_recommendations = []
            user_lat = request.current_location['latitude']
            user_lon = request.current_location['longitude']
            
            for business in candidates:
                if not (business.latitude and business.longitude):
                    continue
                
                distance_km = self._calculate_distance(
                    user_lat, user_lon,
                    float(business.latitude), float(business.longitude)
                )
                
                # Calculate location-based score
                location_score = 0.0
                factors = []
                
                # Distance score (closer is better)
                if distance_km <= 1.0:
                    location_score += 0.5
                    factors.append("Very close (within 1km)")
                elif distance_km <= 3.0:
                    location_score += 0.3
                    factors.append("Nearby (within 3km)")
                elif distance_km <= 5.0:
                    location_score += 0.2
                    factors.append("Accessible (within 5km)")
                
                # Quality boost for nearby places
                if business.rating and distance_km <= 5.0:
                    location_score += float(business.rating) / 5.0 * 0.3
                    factors.append(f"High quality nearby ({business.rating}★)")
                
                # Popular places nearby
                if business.review_count > 20 and distance_km <= 3.0:
                    location_score += 0.2
                    factors.append("Popular nearby spot")
                
                if location_score > 0.1:
                    recommendation = BusinessRecommendation(
                        business_id=business.id,
                        business_name=business.name,
                        category=business.category,
                        recommendation_score=min(1.0, location_score),
                        confidence_score=0.8,  # Location-based is reliable
                        strategy_used=RecommendationStrategy.LOCATION_BASED,
                        reason=f"Quality {business.category} near your location",
                        explanation_factors=factors,
                        rating=business.rating,
                        review_count=business.review_count,
                        distance_km=distance_km,
                        price_range=business.price_range
                    )
                    
                    location_recommendations.append(recommendation)
            
            # Sort by score and distance
            location_recommendations.sort(
                key=lambda x: (x.recommendation_score, -x.distance_km if x.distance_km else 0),
                reverse=True
            )
            
            return location_recommendations[:request.limit * 2]
            
        except Exception as e:
            logger.error("Location-based recommendations failed", error=str(e))
            return []
    
    async def _hybrid_recommendations(
        self,
        request: RecommendationRequest,
        candidates: List[Business],
        user_profile: Optional[UserProfile]
    ) -> List[BusinessRecommendation]:
        """Generate recommendations using hybrid approach combining multiple strategies."""
        
        try:
            # Generate recommendations from different strategies
            strategies_results = {}
            
            # Collaborative filtering (if user available)
            if request.user_id:
                cf_results = await self._collaborative_filtering(request, candidates, user_profile)
                strategies_results[RecommendationStrategy.COLLABORATIVE_FILTERING] = cf_results
            
            # Content-based filtering
            cb_results = await self._content_based_filtering(request, candidates, user_profile)
            strategies_results[RecommendationStrategy.CONTENT_BASED] = cb_results
            
            # Trending
            trending_results = await self._trending_recommendations(request, candidates)
            strategies_results[RecommendationStrategy.TRENDING] = trending_results
            
            # Location-based (if location available)
            if request.current_location:
                location_results = await self._location_based_recommendations(request, candidates)
                strategies_results[RecommendationStrategy.LOCATION_BASED] = location_results
            
            # Combine results using weighted scores
            combined_scores = defaultdict(lambda: {
                'total_score': 0.0,
                'strategy_scores': {},
                'business': None,
                'explanations': [],
                'factors': []
            })
            
            for strategy, results in strategies_results.items():
                weight = self.strategy_weights.get(strategy, 0.1)
                
                for recommendation in results:
                    business_id = recommendation.business_id
                    weighted_score = recommendation.recommendation_score * weight
                    
                    combined_scores[business_id]['total_score'] += weighted_score
                    combined_scores[business_id]['strategy_scores'][strategy.value] = recommendation.recommendation_score
                    combined_scores[business_id]['business'] = recommendation
                    combined_scores[business_id]['explanations'].append(recommendation.reason)
                    combined_scores[business_id]['factors'].extend(recommendation.explanation_factors)
            
            # Create hybrid recommendations
            hybrid_recommendations = []
            
            for business_id, data in combined_scores.items():
                if data['total_score'] > 0.1:  # Minimum threshold
                    base_rec = data['business']
                    
                    # Create combined explanation
                    strategies_used = list(data['strategy_scores'].keys())
                    combined_reason = f"Recommended by multiple factors: {', '.join(strategies_used)}"
                    
                    # Unique factors
                    unique_factors = list(set(data['factors']))[:5]  # Top 5 factors
                    
                    hybrid_rec = BusinessRecommendation(
                        business_id=base_rec.business_id,
                        business_name=base_rec.business_name,
                        category=base_rec.category,
                        recommendation_score=min(1.0, data['total_score']),
                        confidence_score=min(1.0, len(strategies_used) / 4.0 + 0.5),
                        strategy_used=RecommendationStrategy.HYBRID,
                        strategy_scores=data['strategy_scores'],
                        reason=combined_reason,
                        explanation_factors=unique_factors,
                        rating=base_rec.rating,
                        review_count=base_rec.review_count,
                        distance_km=base_rec.distance_km,
                        price_range=base_rec.price_range,
                        matches_user_preferences=base_rec.matches_user_preferences
                    )
                    
                    hybrid_recommendations.append(hybrid_rec)
            
            # Sort by combined score
            hybrid_recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
            
            logger.info(
                "Hybrid recommendations generated",
                strategies_used=len(strategies_results),
                combined_recommendations=len(hybrid_recommendations),
                user_id=request.user_id
            )
            
            return hybrid_recommendations[:request.limit * 2]
            
        except Exception as e:
            logger.error("Hybrid recommendations failed", error=str(e))
            return await self._content_based_filtering(request, candidates, user_profile)
    
    async def _personalized_recommendations(
        self,
        request: RecommendationRequest,
        candidates: List[Business],
        user_profile: Optional[UserProfile]
    ) -> List[BusinessRecommendation]:
        """Generate fully personalized recommendations."""
        
        if not user_profile:
            return await self._hybrid_recommendations(request, candidates, None)
        
        # Use hybrid approach but with stronger personalization weights
        return await self._hybrid_recommendations(request, candidates, user_profile)
    
    async def _apply_diversity_and_ranking(
        self,
        recommendations: List[BusinessRecommendation],
        diversity_factor: float,
        limit: int
    ) -> List[BusinessRecommendation]:
        """Apply diversity filtering and final ranking."""
        
        if not recommendations:
            return []
        
        if diversity_factor <= 0.0:
            # No diversity needed, just return top recommendations
            return recommendations[:limit]
        
        try:
            # Implement diversity using category and location spread
            selected_recommendations = []
            used_categories = set()
            location_clusters = []
            
            # Sort by recommendation score initially
            sorted_recommendations = sorted(recommendations, key=lambda x: x.recommendation_score, reverse=True)
            
            for recommendation in sorted_recommendations:
                if len(selected_recommendations) >= limit:
                    break
                
                # Check category diversity
                category_penalty = 0.0
                if recommendation.category in used_categories:
                    category_count = sum(1 for r in selected_recommendations if r.category == recommendation.category)
                    category_penalty = category_count * diversity_factor * 0.1
                
                # Check location diversity (if distance available)
                location_penalty = 0.0
                if recommendation.distance_km is not None:
                    for selected in selected_recommendations:
                        if selected.distance_km is not None:
                            distance_diff = abs(recommendation.distance_km - selected.distance_km)
                            if distance_diff < 1.0:  # Very close locations
                                location_penalty += diversity_factor * 0.05
                
                # Calculate final score with diversity penalties
                final_score = recommendation.recommendation_score - category_penalty - location_penalty
                
                # Only add if score is still reasonable
                if final_score > 0.3 or len(selected_recommendations) < limit // 2:
                    # Update the recommendation score
                    recommendation.recommendation_score = max(0.1, final_score)
                    selected_recommendations.append(recommendation)
                    used_categories.add(recommendation.category)
            
            # If we don't have enough diverse recommendations, fill with top-scoring ones
            if len(selected_recommendations) < limit:
                remaining_slots = limit - len(selected_recommendations)
                selected_ids = {r.business_id for r in selected_recommendations}
                
                for recommendation in sorted_recommendations:
                    if recommendation.business_id not in selected_ids:
                        selected_recommendations.append(recommendation)
                        remaining_slots -= 1
                        if remaining_slots <= 0:
                            break
            
            return selected_recommendations[:limit]
            
        except Exception as e:
            logger.error("Diversity filtering failed", error=str(e))
            return recommendations[:limit]
    
    async def _calculate_diversity_score(self, recommendations: List[BusinessRecommendation]) -> float:
        """Calculate diversity score of recommendations."""
        
        if not recommendations:
            return 0.0
        
        # Category diversity
        categories = set(r.category for r in recommendations)
        category_diversity = len(categories) / len(recommendations)
        
        # Distance diversity (if available)
        distances = [r.distance_km for r in recommendations if r.distance_km is not None]
        distance_diversity = 0.5  # Default
        
        if len(distances) > 1:
            avg_distance = sum(distances) / len(distances)
            distance_variance = sum((d - avg_distance) ** 2 for d in distances) / len(distances)
            distance_diversity = min(1.0, distance_variance / 10.0)  # Normalize
        
        # Score diversity
        scores = [r.recommendation_score for r in recommendations]
        score_variance = 0.0
        if len(scores) > 1:
            avg_score = sum(scores) / len(scores)
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
        
        score_diversity = min(1.0, score_variance * 10.0)  # Normalize
        
        # Weighted combination
        diversity_score = (category_diversity * 0.5 + 
                          distance_diversity * 0.3 + 
                          score_diversity * 0.2)
        
        return min(1.0, diversity_score)
    
    async def _calculate_novelty_score(
        self,
        recommendations: List[BusinessRecommendation],
        user_profile: Optional[UserProfile]
    ) -> float:
        """Calculate novelty/surprise score of recommendations."""
        
        if not recommendations or not user_profile:
            return 0.5  # Default novelty
        
        novelty_factors = []
        
        for recommendation in recommendations:
            novelty = 0.5  # Base novelty
            
            # Category novelty (new categories are more novel)
            if recommendation.category not in user_profile.favorite_categories:
                novelty += 0.3
            
            if recommendation.category in user_profile.avoided_categories:
                novelty -= 0.2
            
            # Distance novelty (different from usual patterns)
            if (user_profile.preferred_distance_km and 
                recommendation.distance_km and
                abs(recommendation.distance_km - user_profile.preferred_distance_km) > 2.0):
                novelty += 0.2
            
            novelty_factors.append(max(0.0, min(1.0, novelty)))
        
        return sum(novelty_factors) / len(novelty_factors) if novelty_factors else 0.5
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        
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
    
    async def _find_similar_users(self, user_id: UUID, limit: int = 20) -> List[Tuple[UUID, float]]:
        """Find users similar to the given user based on interaction patterns."""
        
        try:
            # This is a simplified implementation
            # In production, you'd use more sophisticated similarity algorithms
            
            # For now, return random similar users as placeholder
            # This would be replaced with actual collaborative filtering logic
            
            similar_users = []
            
            # Query for users who interacted with similar businesses
            # This is placeholder logic - implement based on your user interaction data
            
            return similar_users
            
        except Exception as e:
            logger.error("Failed to find similar users", user_id=user_id, error=str(e))
            return []
    
    async def _get_businesses_liked_by_users(self, user_ids: List[UUID]) -> Dict[UUID, List[Tuple[UUID, float]]]:
        """Get businesses liked by the given users."""
        
        try:
            # This would query user interaction/review data
            # Placeholder implementation
            
            businesses_by_user = {}
            
            # In production, this would query interaction data like:
            # - Reviews with rating >= 4
            # - Businesses marked as favorites
            # - Businesses with multiple visits
            # - Businesses shared by users
            
            return businesses_by_user
            
        except Exception as e:
            logger.error("Failed to get businesses liked by users", error=str(e))
            return {}
    
    async def _find_similar_businesses(
        self,
        business_id: UUID,
        candidates: List[Business],
        request: RecommendationRequest
    ) -> List[BusinessRecommendation]:
        """Find businesses similar to the given business."""
        
        try:
            # Find the context business
            context_business = None
            for business in candidates:
                if business.id == business_id:
                    context_business = business
                    break
            
            if not context_business:
                return []
            
            similar_businesses = []
            
            for business in candidates:
                if business.id == business_id:
                    continue
                
                similarity_score = 0.0
                factors = []
                
                # Category similarity
                if business.category == context_business.category:
                    similarity_score += 0.4
                    factors.append(f"Same category: {business.category}")
                
                # Price range similarity
                if (business.price_range and context_business.price_range and 
                    business.price_range == context_business.price_range):
                    similarity_score += 0.2
                    factors.append(f"Similar price range: {business.price_range}")
                
                # Rating similarity
                if business.rating and context_business.rating:
                    rating_diff = abs(float(business.rating) - float(context_business.rating))
                    if rating_diff <= 0.5:
                        similarity_score += 0.2
                        factors.append("Similar rating")
                
                # Amenities similarity
                if business.amenities and context_business.amenities:
                    common_amenities = set(business.amenities) & set(context_business.amenities)
                    if common_amenities:
                        amenity_score = len(common_amenities) / len(set(business.amenities) | set(context_business.amenities))
                        similarity_score += amenity_score * 0.2
                        factors.append(f"Similar amenities: {', '.join(list(common_amenities)[:3])}")
                
                if similarity_score > 0.3:
                    recommendation = BusinessRecommendation(
                        business_id=business.id,
                        business_name=business.name,
                        category=business.category,
                        recommendation_score=min(1.0, similarity_score),
                        confidence_score=0.8,
                        strategy_used=RecommendationStrategy.CONTENT_BASED,
                        reason=f"Similar to {context_business.name}",
                        explanation_factors=factors,
                        rating=business.rating,
                        review_count=business.review_count,
                        price_range=business.price_range,
                        similar_to_liked=context_business.id
                    )
                    
                    # Add distance if location available
                    if request.current_location and business.latitude and business.longitude:
                        recommendation.distance_km = self._calculate_distance(
                            request.current_location['latitude'],
                            request.current_location['longitude'],
                            float(business.latitude),
                            float(business.longitude)
                        )
                    
                    similar_businesses.append(recommendation)
            
            # Sort by similarity score
            similar_businesses.sort(key=lambda x: x.recommendation_score, reverse=True)
            return similar_businesses[:request.limit * 2]
            
        except Exception as e:
            logger.error("Failed to find similar businesses", error=str(e))
            return []
    
    async def _profile_based_recommendations(
        self,
        user_profile: UserProfile,
        candidates: List[Business],
        request: RecommendationRequest
    ) -> List[BusinessRecommendation]:
        """Generate recommendations based on user profile preferences."""
        
        try:
            profile_recommendations = []
            
            for business in candidates:
                profile_score = 0.0
                factors = []
                matches = []
                
                # Category preferences
                category_pref = user_profile.category_preferences.get(business.category, 0.5)
                profile_score += category_pref * 0.3
                if category_pref > 0.7:
                    factors.append(f"Matches your preference for {business.category}")
                    matches.append(f"Preferred category: {business.category}")
                
                # Quality preferences
                if business.rating and user_profile.rating_sensitivity > 0.5:
                    rating_score = float(business.rating) / 5.0
                    profile_score += rating_score * user_profile.rating_sensitivity * 0.3
                    if business.rating >= 4.5:
                        factors.append(f"High quality ({business.rating}★)")
                        matches.append("High rating preference")
                
                # Review count importance
                if business.review_count > 10:
                    review_score = min(1.0, business.review_count / 100.0)
                    profile_score += review_score * user_profile.review_count_importance * 0.2
                    if business.review_count > 50:
                        factors.append("Well-reviewed business")
                        matches.append("Popular place preference")
                
                # Distance preference
                if (request.current_location and business.latitude and business.longitude and 
                    user_profile.preferred_distance_km):
                    
                    distance_km = self._calculate_distance(
                        request.current_location['latitude'],
                        request.current_location['longitude'],
                        float(business.latitude),
                        float(business.longitude)
                    )
                    
                    if distance_km <= user_profile.preferred_distance_km:
                        distance_score = 1.0 - (distance_km / user_profile.preferred_distance_km)
                        profile_score += distance_score * 0.2
                        factors.append("Within preferred distance")
                        matches.append("Location preference")
                
                # Trending preference
                if user_profile.follows_trends and business.popularity_score:
                    trending_score = float(business.popularity_score) / 100.0
                    profile_score += trending_score * 0.1
                    if business.popularity_score > 70:
                        factors.append("Trending venue")
                        matches.append("Trending places preference")
                
                if profile_score > 0.4:
                    recommendation = BusinessRecommendation(
                        business_id=business.id,
                        business_name=business.name,
                        category=business.category,
                        recommendation_score=min(1.0, profile_score),
                        confidence_score=0.8,
                        strategy_used=RecommendationStrategy.PERSONALIZED,
                        reason=f"Matches your preferences for {business.category}",
                        explanation_factors=factors,
                        matches_user_preferences=matches,
                        rating=business.rating,
                        review_count=business.review_count,
                        price_range=business.price_range
                    )
                    
                    profile_recommendations.append(recommendation)
            
            # Sort by profile match score
            profile_recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
            return profile_recommendations[:request.limit * 2]
            
        except Exception as e:
            logger.error("Profile-based recommendations failed", error=str(e))
            return []
    
    def _get_strategy_explanation(self, strategy: RecommendationStrategy) -> str:
        """Get human-readable explanation for the strategy used."""
        
        explanations = {
            RecommendationStrategy.COLLABORATIVE_FILTERING: 
                "Based on preferences of users with similar tastes",
            RecommendationStrategy.CONTENT_BASED:
                "Based on business characteristics and quality factors",
            RecommendationStrategy.AI_POWERED:
                "Generated using AI analysis of your preferences and context",
            RecommendationStrategy.TRENDING:
                "Based on currently popular and trending businesses",
            RecommendationStrategy.LOCATION_BASED:
                "Based on proximity and local popularity",
            RecommendationStrategy.HYBRID:
                "Combines multiple recommendation approaches for best results",
            RecommendationStrategy.PERSONALIZED:
                "Tailored specifically to your preferences and behavior"
        }
        
        return explanations.get(strategy, "Personalized recommendations for you")
    
    def _create_empty_result(self, request: RecommendationRequest, reason: str) -> RecommendationResult:
        """Create empty recommendation result with explanation."""
        
        return RecommendationResult(
            recommendations=[],
            request_type=request.recommendation_type,
            strategy_used=request.strategy,
            total_candidates=0,
            processing_time_ms=0,
            user_id=request.user_id,
            average_confidence=0.0,
            diversity_score=0.0,
            novelty_score=0.0,
            strategy_explanation=f"No recommendations available: {reason}",
            personalization_applied=False,
            used_fallback=False
        )
    
    async def _fallback_recommendations(self, request: RecommendationRequest, error_reason: str) -> RecommendationResult:
        """Generate fallback recommendations when main strategy fails."""
        
        try:
            # Load a few popular businesses as fallback
            popular_query = select(Business).where(
                and_(
                    Business.status == BusinessStatus.VERIFIED,
                    Business.verified == True,
                    Business.rating >= 4.0
                )
            ).order_by(desc(Business.review_count)).limit(20)
            
            result = await self.session.execute(popular_query)
            popular_businesses = result.scalars().all()
            
            fallback_recommendations = []
            
            for business in popular_businesses[:request.limit]:
                recommendation = BusinessRecommendation(
                    business_id=business.id,
                    business_name=business.name,
                    category=business.category,
                    recommendation_score=0.7,
                    confidence_score=0.5,
                    strategy_used=RecommendationStrategy.CONTENT_BASED,
                    reason=f"Popular {business.category} with high ratings",
                    explanation_factors=["High rating", "Popular venue"],
                    rating=business.rating,
                    review_count=business.review_count,
                    price_range=business.price_range
                )
                
                fallback_recommendations.append(recommendation)
            
            return RecommendationResult(
                recommendations=fallback_recommendations,
                request_type=request.recommendation_type,
                strategy_used=RecommendationStrategy.CONTENT_BASED,
                total_candidates=len(popular_businesses),
                processing_time_ms=0,
                user_id=request.user_id,
                average_confidence=0.5,
                diversity_score=0.5,
                novelty_score=0.3,
                strategy_explanation="Showing popular businesses due to recommendation system error",
                personalization_applied=False,
                used_fallback=True,
                fallback_reason=error_reason
            )
            
        except Exception as e:
            logger.error("Fallback recommendations also failed", error=str(e))
            return self._create_empty_result(request, f"System error: {error_reason}")