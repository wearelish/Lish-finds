"""
Ranking models and configurations for LishFind ranking engine.

Defines ranking configurations, factors, and result structures.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class RankingAlgorithm(str, Enum):
    """Available ranking algorithms."""
    WEIGHTED_SCORE = "weighted_score"
    DISTANCE_PRIORITY = "distance_priority"
    QUALITY_PRIORITY = "quality_priority"
    POPULARITY_PRIORITY = "popularity_priority"
    BALANCED = "balanced"
    CUSTOM = "custom"


class RankingFactors(BaseModel):
    """Individual ranking factors with weights."""
    
    # Distance factor (0.0 to 1.0, higher is closer)
    distance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Distance score")
    distance_weight: float = Field(0.25, ge=0.0, le=1.0, description="Distance weight")
    
    # Quality factors
    rating_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Normalized rating score")
    rating_weight: float = Field(0.30, ge=0.0, le=1.0, description="Rating weight")
    
    review_count_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Normalized review count")
    review_weight: float = Field(0.15, ge=0.0, le=1.0, description="Review count weight")
    
    # Business completeness
    completeness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Profile completeness score")
    completeness_weight: float = Field(0.10, ge=0.0, le=1.0, description="Completeness weight")
    
    # Popularity and engagement
    popularity_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Popularity score")
    popularity_weight: float = Field(0.15, ge=0.0, le=1.0, description="Popularity weight")
    
    # Verification and trust
    verification_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Verification score")
    verification_weight: float = Field(0.05, ge=0.0, le=1.0, description="Verification weight")
    
    @validator('verification_weight')
    def validate_weights_sum(cls, v, values):
        """Ensure all weights sum to 1.0."""
        weight_fields = [
            'distance_weight', 'rating_weight', 'review_weight',
            'completeness_weight', 'popularity_weight', 'verification_weight'
        ]
        
        # Only validate when we have all weight fields
        if all(field in values for field in weight_fields[:-1]):  # Last field being validated
            total_weight = sum(values.get(field, 0) for field in weight_fields[:-1]) + v
            if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
                raise ValueError(f"Total weights must sum to 1.0, got {total_weight}")
        
        return v


class RankingConfig(BaseModel):
    """Configuration for business ranking."""
    
    algorithm: RankingAlgorithm = Field(
        RankingAlgorithm.BALANCED,
        description="Ranking algorithm to use"
    )
    
    factors: RankingFactors = Field(
        default_factory=RankingFactors,
        description="Ranking factors and weights"
    )
    
    # Distance configuration
    max_distance_km: Optional[float] = Field(
        None,
        ge=0.1,
        le=1000,
        description="Maximum distance for distance scoring"
    )
    distance_decay_function: str = Field(
        "exponential",
        description="Distance decay function: linear, exponential, logarithmic"
    )
    
    # Quality thresholds
    min_rating_threshold: float = Field(
        2.0,
        ge=1.0,
        le=5.0,
        description="Minimum rating for quality bonus"
    )
    min_reviews_threshold: int = Field(
        5,
        ge=0,
        description="Minimum reviews for review count scoring"
    )
    
    # Boost factors
    verified_boost: float = Field(
        1.2,
        ge=1.0,
        le=2.0,
        description="Score multiplier for verified businesses"
    )
    premium_boost: float = Field(
        1.1,
        ge=1.0,
        le=2.0,
        description="Score multiplier for premium businesses"
    )
    
    # Penalty factors
    low_rating_penalty: float = Field(
        0.8,
        ge=0.1,
        le=1.0,
        description="Score multiplier for low-rated businesses"
    )
    incomplete_profile_penalty: float = Field(
        0.9,
        ge=0.1,
        le=1.0,
        description="Score multiplier for incomplete profiles"
    )
    
    # Personalization
    enable_personalization: bool = Field(
        True,
        description="Enable user preference personalization"
    )
    user_preference_weight: float = Field(
        0.1,
        ge=0.0,
        le=0.5,
        description="Weight for user preference adjustments"
    )


class BusinessRankingData(BaseModel):
    """Business data used for ranking calculations."""
    
    id: UUID = Field(..., description="Business ID")
    name: str = Field(..., description="Business name")
    category: str = Field(..., description="Business category")
    
    # Location data
    latitude: Optional[Decimal] = Field(None, description="Business latitude")
    longitude: Optional[Decimal] = Field(None, description="Business longitude")
    distance_km: Optional[float] = Field(None, description="Distance from user")
    
    # Quality metrics
    rating: Optional[Decimal] = Field(None, description="Average rating")
    review_count: int = Field(0, description="Number of reviews")
    
    # Business status
    verified: bool = Field(False, description="Is business verified")
    premium: bool = Field(False, description="Is premium business")
    
    # Profile completeness factors
    has_description: bool = Field(False, description="Has business description")
    has_photos: bool = Field(False, description="Has business photos")
    has_hours: bool = Field(False, description="Has opening hours")
    has_contact: bool = Field(False, description="Has contact information")
    has_website: bool = Field(False, description="Has website URL")
    amenities_count: int = Field(0, description="Number of amenities listed")
    services_count: int = Field(0, description="Number of services listed")
    
    # Engagement metrics
    popularity_score: Optional[Decimal] = Field(None, description="Popularity score")
    recent_reviews_count: int = Field(0, description="Recent reviews count")
    click_through_rate: Optional[float] = Field(None, description="CTR from search results")
    
    # Temporal factors
    created_at: datetime = Field(..., description="Business creation date")
    updated_at: datetime = Field(..., description="Last update time")
    last_review_date: Optional[datetime] = Field(None, description="Date of last review")


class RankingResult(BaseModel):
    """Result of business ranking calculation."""
    
    business_id: UUID = Field(..., description="Business ID")
    final_score: float = Field(..., ge=0.0, description="Final ranking score")
    
    # Individual factor scores
    distance_score: Optional[float] = Field(None, description="Distance component score")
    rating_score: Optional[float] = Field(None, description="Rating component score")
    review_score: Optional[float] = Field(None, description="Review count component score")
    completeness_score: Optional[float] = Field(None, description="Completeness component score")
    popularity_score: Optional[float] = Field(None, description="Popularity component score")
    verification_score: Optional[float] = Field(None, description="Verification component score")
    
    # Boost and penalty factors applied
    boosts_applied: List[str] = Field(default_factory=list, description="List of boosts applied")
    penalties_applied: List[str] = Field(default_factory=list, description="List of penalties applied")
    
    # Personalization adjustment
    personalization_adjustment: Optional[float] = Field(None, description="Personalization score adjustment")
    
    # Ranking metadata
    algorithm_used: RankingAlgorithm = Field(..., description="Algorithm used for ranking")
    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="When ranking was calculated")
    
    # Debug information
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Debug information for ranking")


class UserPreferences(BaseModel):
    """User preferences for personalized ranking."""
    
    user_id: UUID = Field(..., description="User ID")
    
    # Category preferences (category -> preference score 0.0 to 1.0)
    category_preferences: Dict[str, float] = Field(
        default_factory=dict,
        description="User category preferences"
    )
    
    # Quality preferences
    prefer_high_rated: bool = Field(True, description="Prefer highly rated businesses")
    min_preferred_rating: float = Field(4.0, ge=1.0, le=5.0, description="Minimum preferred rating")
    
    # Distance preferences
    prefer_nearby: bool = Field(True, description="Prefer nearby businesses")
    max_preferred_distance_km: Optional[float] = Field(None, description="Max preferred distance")
    
    # Price preferences
    preferred_price_ranges: List[str] = Field(
        default_factory=list,
        description="Preferred price ranges"
    )
    
    # Feature preferences
    preferred_amenities: List[str] = Field(
        default_factory=list,
        description="Preferred amenities"
    )
    
    # Historical behavior weights
    click_history_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight for click history")
    search_history_weight: float = Field(0.2, ge=0.0, le=1.0, description="Weight for search history")
    
    # Last updated
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When preferences were last updated")


class RankingBatch(BaseModel):
    """Batch ranking request for multiple businesses."""
    
    businesses: List[BusinessRankingData] = Field(..., description="Businesses to rank")
    config: RankingConfig = Field(..., description="Ranking configuration")
    user_preferences: Optional[UserPreferences] = Field(None, description="User preferences for personalization")
    
    # Context for ranking
    search_query: Optional[str] = Field(None, description="Original search query")
    user_location: Optional[Dict[str, float]] = Field(None, description="User location")
    search_context: Optional[Dict[str, Any]] = Field(None, description="Additional search context")


class RankingBatchResult(BaseModel):
    """Result of batch ranking operation."""
    
    results: List[RankingResult] = Field(..., description="Ranking results")
    config_used: RankingConfig = Field(..., description="Configuration used")
    
    # Batch metadata
    total_businesses: int = Field(..., description="Total businesses ranked")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    algorithm_used: RankingAlgorithm = Field(..., description="Algorithm used")
    
    # Statistics
    score_distribution: Optional[Dict[str, float]] = Field(None, description="Score distribution statistics")
    factor_correlations: Optional[Dict[str, float]] = Field(None, description="Factor correlation analysis")
    
    # Recommendations for optimization
    optimization_suggestions: Optional[List[str]] = Field(None, description="Suggestions for ranking optimization")