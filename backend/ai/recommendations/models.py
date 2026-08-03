"""
Recommendation models and data structures.

Defines recommendation requests, results, user profiles, and business recommendations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field

from ai.intent.models import SearchIntent


class RecommendationStrategy(str, Enum):
    """Recommendation strategies available."""
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"
    AI_POWERED = "ai_powered"
    TRENDING = "trending"
    SIMILAR_USERS = "similar_users"
    LOCATION_BASED = "location_based"
    PERSONALIZED = "personalized"


class RecommendationType(str, Enum):
    """Types of recommendations."""
    SIMILAR_BUSINESSES = "similar_businesses"
    RECOMMENDED_FOR_YOU = "recommended_for_you"
    TRENDING_NOW = "trending_now"
    NEARBY_POPULAR = "nearby_popular"
    BASED_ON_HISTORY = "based_on_history"
    BECAUSE_YOU_LIKED = "because_you_liked"
    USERS_ALSO_LIKED = "users_also_liked"
    PERFECT_FOR_MOOD = "perfect_for_mood"


class UserInteractionType(str, Enum):
    """Types of user interactions for recommendation learning."""
    VIEW = "view"
    CLICK = "click"
    VISIT = "visit"
    REVIEW = "review"
    FAVORITE = "favorite"
    SHARE = "share"
    SEARCH = "search"
    CALL = "call"
    WEBSITE_CLICK = "website_click"


class UserProfile(BaseModel):
    """User profile for personalized recommendations."""
    
    user_id: UUID = Field(..., description="User ID")
    
    # Demographic info
    age_range: Optional[str] = Field(None, description="Age range category")
    location_city: Optional[str] = Field(None, description="Primary city")
    
    # Preference scores (0.0 to 1.0)
    category_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Business category preferences"
    )
    price_range_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Price range preferences"
    )
    cuisine_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="Cuisine type preferences (for restaurants)"
    )
    
    # Behavioral patterns
    preferred_distance_km: Optional[float] = Field(None, description="Preferred search distance")
    preferred_times: List[str] = Field(default_factory=list, description="Preferred visit times")
    weekend_vs_weekday_preference: Optional[float] = Field(None, description="Weekend preference (-1 to 1)")
    
    # Quality preferences
    rating_sensitivity: float = Field(0.5, description="How much ratings matter (0-1)")
    review_count_importance: float = Field(0.3, description="How much review count matters (0-1)")
    
    # Interaction history aggregates
    total_interactions: int = Field(0, description="Total recorded interactions")
    favorite_categories: List[str] = Field(default_factory=list, description="Top liked categories")
    avoided_categories: List[str] = Field(default_factory=list, description="Disliked categories")
    
    # Temporal patterns
    most_active_hours: List[int] = Field(default_factory=list, description="Hours when most active")
    seasonal_preferences: Dict[str, float] = Field(default_factory=dict, description="Seasonal activity patterns")
    
    # Social influence
    follows_trends: bool = Field(True, description="Whether user likes trending places")
    prefers_popular_places: bool = Field(True, description="Preference for popular venues")
    
    # Last updated
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When profile was last updated")
    profile_completeness: float = Field(0.0, description="Profile completeness score (0-1)")


class BusinessRecommendation(BaseModel):
    """Individual business recommendation."""
    
    business_id: UUID = Field(..., description="Business ID")
    business_name: str = Field(..., description="Business name")
    category: str = Field(..., description="Business category")
    
    # Recommendation scoring
    recommendation_score: float = Field(..., ge=0.0, le=1.0, description="Overall recommendation score")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in recommendation")
    
    # Strategy breakdown
    strategy_used: RecommendationStrategy = Field(..., description="Primary strategy used")
    strategy_scores: Dict[str, float] = Field(default_factory=dict, description="Scores from different strategies")
    
    # Reasoning
    reason: str = Field(..., description="Human-readable reason for recommendation")
    explanation_factors: List[str] = Field(default_factory=list, description="Factors contributing to recommendation")
    
    # Business details for display
    rating: Optional[Decimal] = Field(None, description="Business rating")
    review_count: int = Field(0, description="Number of reviews")
    distance_km: Optional[float] = Field(None, description="Distance from user")
    price_range: Optional[str] = Field(None, description="Price range")
    
    # Personalization details
    matches_user_preferences: List[str] = Field(default_factory=list, description="How it matches user preferences")
    similar_to_liked: Optional[UUID] = Field(None, description="Similar to previously liked business")
    
    # Metadata
    recommended_at: datetime = Field(default_factory=datetime.utcnow, description="When recommendation was generated")
    expires_at: Optional[datetime] = Field(None, description="When recommendation expires")


class RecommendationRequest(BaseModel):
    """Request for business recommendations."""
    
    user_id: Optional[UUID] = Field(None, description="User ID for personalized recommendations")
    session_id: Optional[str] = Field(None, description="Session ID for anonymous users")
    
    # Context
    current_location: Optional[Dict[str, float]] = Field(None, description="User's current location")
    search_intent: Optional[SearchIntent] = Field(None, description="Current search intent")
    context_business_id: Optional[UUID] = Field(None, description="Business for context-based recommendations")
    
    # Request parameters
    recommendation_type: RecommendationType = Field(
        RecommendationType.RECOMMENDED_FOR_YOU,
        description="Type of recommendations requested"
    )
    strategy: RecommendationStrategy = Field(
        RecommendationStrategy.HYBRID,
        description="Recommendation strategy to use"
    )
    
    # Filters
    max_distance_km: Optional[float] = Field(None, description="Maximum distance for recommendations")
    categories: Optional[List[str]] = Field(None, description="Restrict to specific categories")
    price_ranges: Optional[List[str]] = Field(None, description="Acceptable price ranges")
    min_rating: Optional[float] = Field(None, description="Minimum rating filter")
    
    # Response configuration
    limit: int = Field(10, ge=1, le=50, description="Number of recommendations to return")
    include_reasoning: bool = Field(True, description="Include recommendation reasoning")
    diversity_factor: float = Field(0.3, ge=0.0, le=1.0, description="How diverse recommendations should be")
    
    # Temporal context
    for_time: Optional[datetime] = Field(None, description="Time for which recommendations are made")
    day_of_week: Optional[str] = Field(None, description="Day of week context")


class RecommendationResult(BaseModel):
    """Result containing multiple business recommendations."""
    
    recommendations: List[BusinessRecommendation] = Field(..., description="List of recommended businesses")
    
    # Request context
    request_type: RecommendationType = Field(..., description="Type of recommendations provided")
    strategy_used: RecommendationStrategy = Field(..., description="Primary strategy used")
    
    # Metadata
    total_candidates: int = Field(0, description="Total businesses considered")
    processing_time_ms: int = Field(0, description="Processing time in milliseconds")
    user_id: Optional[UUID] = Field(None, description="User ID if personalized")
    
    # Quality metrics
    average_confidence: float = Field(0.0, description="Average confidence score")
    diversity_score: float = Field(0.0, description="Diversity of recommendations")
    novelty_score: float = Field(0.0, description="How novel/surprising recommendations are")
    
    # Explanation
    strategy_explanation: str = Field("", description="Explanation of strategy used")
    personalization_applied: bool = Field(False, description="Whether personalization was applied")
    
    # Fallback information
    used_fallback: bool = Field(False, description="Whether fallback strategy was used")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback if used")
    
    # Caching and freshness
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When recommendations were generated")
    cache_key: Optional[str] = Field(None, description="Cache key for these recommendations")


class UserInteraction(BaseModel):
    """User interaction record for learning."""
    
    user_id: UUID = Field(..., description="User ID")
    business_id: UUID = Field(..., description="Business ID")
    interaction_type: UserInteractionType = Field(..., description="Type of interaction")
    
    # Context
    session_id: Optional[str] = Field(None, description="Session ID")
    search_query: Optional[str] = Field(None, description="Search query that led to interaction")
    recommendation_id: Optional[str] = Field(None, description="ID of recommendation that led to this")
    
    # Interaction details
    duration_seconds: Optional[int] = Field(None, description="Duration of interaction")
    rating_given: Optional[float] = Field(None, description="Rating given by user")
    review_text: Optional[str] = Field(None, description="Review text if applicable")
    
    # Temporal context
    interaction_time: datetime = Field(default_factory=datetime.utcnow, description="When interaction occurred")
    day_of_week: str = Field("", description="Day of week")
    hour_of_day: int = Field(0, description="Hour of day (0-23)")
    
    # Location context
    user_location: Optional[Dict[str, float]] = Field(None, description="User location during interaction")
    
    # Implicit feedback
    clicked_after_view: bool = Field(False, description="Whether user clicked after viewing")
    time_spent_on_page: Optional[int] = Field(None, description="Time spent viewing business page")
    shared_or_saved: bool = Field(False, description="Whether user shared or saved")


class RecommendationFeedback(BaseModel):
    """Feedback on recommendations for learning."""
    
    recommendation_id: str = Field(..., description="ID of the recommendation")
    user_id: UUID = Field(..., description="User who provided feedback")
    business_id: UUID = Field(..., description="Recommended business")
    
    # Explicit feedback
    helpful: Optional[bool] = Field(None, description="Whether recommendation was helpful")
    relevant: Optional[bool] = Field(None, description="Whether recommendation was relevant")
    surprising: Optional[bool] = Field(None, description="Whether recommendation was surprising")
    
    # Action taken
    clicked: bool = Field(False, description="Whether user clicked on recommendation")
    visited: bool = Field(False, description="Whether user visited the business")
    dismissed: bool = Field(False, description="Whether user dismissed recommendation")
    
    # Feedback text
    feedback_text: Optional[str] = Field(None, description="Free-form feedback")
    
    # Timestamp
    feedback_time: datetime = Field(default_factory=datetime.utcnow, description="When feedback was provided")


class RecommendationAnalytics(BaseModel):
    """Analytics data for recommendation performance."""
    
    # Performance metrics
    click_through_rate: float = Field(0.0, description="Overall CTR for recommendations")
    conversion_rate: float = Field(0.0, description="Rate of users who visited recommended businesses")
    user_satisfaction: float = Field(0.0, description="Average user satisfaction score")
    
    # Strategy performance
    strategy_performance: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Performance metrics by strategy"
    )
    
    # Diversity and novelty
    average_diversity: float = Field(0.0, description="Average diversity score")
    average_novelty: float = Field(0.0, description="Average novelty score")
    
    # Coverage
    business_coverage: float = Field(0.0, description="Percentage of businesses being recommended")
    user_coverage: float = Field(0.0, description="Percentage of users receiving recommendations")
    
    # Temporal patterns
    peak_hours: List[int] = Field(default_factory=list, description="Hours with most recommendation requests")
    daily_patterns: Dict[str, float] = Field(default_factory=dict, description="Daily usage patterns")
    
    # Category distribution
    category_distribution: Dict[str, float] = Field(
        default_factory=dict,
        description="Distribution of recommended categories"
    )
    
    # Time period
    period_start: datetime = Field(..., description="Start of analytics period")
    period_end: datetime = Field(..., description="End of analytics period")
    total_recommendations: int = Field(0, description="Total recommendations in period")