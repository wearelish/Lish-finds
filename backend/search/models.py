"""
Search models and data structures for LishFind search engine.

Defines search queries, results, and filtering options.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from ai.intent.models import SearchIntent


class SortOrder(str, Enum):
    """Sort order options for search results."""
    RELEVANCE = "relevance"
    DISTANCE = "distance" 
    RATING = "rating"
    PRICE_LOW_TO_HIGH = "price_low_to_high"
    PRICE_HIGH_TO_LOW = "price_high_to_low"
    NEWEST = "newest"
    POPULARITY = "popularity"


class SearchFilters(BaseModel):
    """Filters for business search."""
    
    # Geographic filters
    latitude: Optional[float] = Field(None, description="User latitude")
    longitude: Optional[float] = Field(None, description="User longitude")
    radius_km: Optional[float] = Field(None, description="Search radius in kilometers")
    city: Optional[str] = Field(None, description="City filter")
    area: Optional[str] = Field(None, description="Area/neighborhood filter")
    
    # Category and business type
    categories: Optional[List[str]] = Field(None, description="Business categories to include")
    exclude_categories: Optional[List[str]] = Field(None, description="Categories to exclude")
    
    # Quality filters
    min_rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="Minimum rating")
    min_review_count: Optional[int] = Field(None, ge=0, description="Minimum number of reviews")
    verified_only: bool = Field(False, description="Only show verified businesses")
    
    # Operational filters
    open_now: bool = Field(False, description="Only show businesses open now")
    open_at_time: Optional[str] = Field(None, description="Open at specific time (HH:MM)")
    day_of_week: Optional[str] = Field(None, description="Day of week for hours check")
    
    # Amenities and features
    required_amenities: Optional[List[str]] = Field(None, description="Must-have amenities")
    preferred_amenities: Optional[List[str]] = Field(None, description="Nice-to-have amenities")
    
    # Budget filters
    price_range: Optional[List[str]] = Field(None, description="Accepted price ranges")
    max_budget: Optional[int] = Field(None, description="Maximum budget per person")
    
    # Dietary and accessibility
    dietary_preferences: Optional[List[str]] = Field(None, description="Dietary requirements")
    accessibility_needs: Optional[List[str]] = Field(None, description="Accessibility requirements")


class SearchQuery(BaseModel):
    """Complete search query with intent and filters."""
    
    # Core query
    text_query: str = Field(..., description="Text search query")
    intent: Optional[SearchIntent] = Field(None, description="Extracted search intent")
    
    # Filters and sorting
    filters: SearchFilters = Field(default_factory=SearchFilters, description="Search filters")
    sort_by: SortOrder = Field(SortOrder.RELEVANCE, description="Sort order")
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Results per page")
    
    # User context
    user_id: Optional[UUID] = Field(None, description="User ID for personalization")
    session_id: Optional[str] = Field(None, description="Session ID for anonymous users")


class BusinessSearchResult(BaseModel):
    """Individual business in search results."""
    
    # Business data
    id: UUID = Field(..., description="Business ID")
    name: str = Field(..., description="Business name")
    category: str = Field(..., description="Primary category")
    description: Optional[str] = Field(None, description="Business description")
    
    # Location
    latitude: Optional[Decimal] = Field(None, description="Business latitude")
    longitude: Optional[Decimal] = Field(None, description="Business longitude")
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, description="City")
    
    # Distance (if location-based search)
    distance_km: Optional[float] = Field(None, description="Distance from user location")
    
    # Quality metrics
    rating: Optional[Decimal] = Field(None, description="Average rating")
    review_count: int = Field(0, description="Number of reviews")
    verified: bool = Field(False, description="Whether business is verified")
    
    # Operational status
    is_open_now: Optional[bool] = Field(None, description="Whether open right now")
    price_range: Optional[str] = Field(None, description="Price range category")
    
    # Contact and media
    phone: Optional[str] = Field(None, description="Phone number")
    website: Optional[str] = Field(None, description="Website URL")
    photos: Optional[List[str]] = Field(None, description="Photo URLs")
    
    # Amenities and features
    amenities: Optional[List[str]] = Field(None, description="Available amenities")
    services: Optional[List[str]] = Field(None, description="Services offered")
    
    # Search relevance
    relevance_score: Optional[float] = Field(None, description="Search relevance score")
    popularity_score: Optional[Decimal] = Field(None, description="Business popularity score")
    
    # Opening hours (simplified)
    opening_hours: Optional[Dict[str, Any]] = Field(None, description="Opening hours")


class SearchResult(BaseModel):
    """Complete search result with businesses and metadata."""
    
    # Results
    businesses: List[BusinessSearchResult] = Field(..., description="List of matching businesses")
    
    # Pagination info
    total_count: int = Field(..., description="Total number of matching businesses")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Results per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    # Search metadata
    query_used: str = Field(..., description="The search query that was executed")
    filters_applied: SearchFilters = Field(..., description="Filters that were applied")
    sort_order: SortOrder = Field(..., description="Sort order used")
    
    # Performance metrics
    search_time_ms: int = Field(..., description="Time taken for search")
    
    # Search insights
    suggestions: Optional[List[str]] = Field(None, description="Alternative query suggestions")
    did_you_mean: Optional[str] = Field(None, description="Spell correction suggestion")
    
    # Geographic bounds (for map display)
    bounds: Optional[Dict[str, float]] = Field(None, description="Geographic bounds of results")


class SearchAggregations(BaseModel):
    """Search result aggregations and facets."""
    
    categories: Dict[str, int] = Field(default_factory=dict, description="Business categories with counts")
    price_ranges: Dict[str, int] = Field(default_factory=dict, description="Price ranges with counts")
    ratings: Dict[str, int] = Field(default_factory=dict, description="Rating ranges with counts")
    amenities: Dict[str, int] = Field(default_factory=dict, description="Popular amenities with counts")
    areas: Dict[str, int] = Field(default_factory=dict, description="Areas with counts")
    
    
class SearchAnalytics(BaseModel):
    """Search analytics and metrics."""
    
    # Query analytics
    query: str = Field(..., description="Search query")
    user_id: Optional[UUID] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    
    # Results metrics
    results_count: int = Field(..., description="Number of results returned")
    search_time_ms: int = Field(..., description="Search execution time")
    
    # User interaction
    clicked_businesses: Optional[List[UUID]] = Field(None, description="Businesses clicked by user")
    click_through_rate: Optional[float] = Field(None, description="CTR for this search")
    
    # Geographic context
    user_location: Optional[Dict[str, float]] = Field(None, description="User location")
    search_radius_km: Optional[float] = Field(None, description="Search radius used")
    
    # Timestamp
    searched_at: datetime = Field(default_factory=datetime.utcnow, description="When search was performed")