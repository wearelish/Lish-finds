"""
Intent extraction models for LishFind search queries.

Defines the structure of extracted intent data from natural language queries.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """Main categories for business searches."""
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    BAR = "bar"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    HEALTHCARE = "healthcare"
    FITNESS = "fitness"
    BEAUTY = "beauty"
    SERVICES = "services"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    EDUCATION = "education"
    OTHER = "other"


class PriceRange(str, Enum):
    """Price range categories."""
    BUDGET = "budget"        # Under ₹500
    MODERATE = "moderate"    # ₹500 - ₹1500  
    EXPENSIVE = "expensive"  # ₹1500 - ₹3000
    LUXURY = "luxury"        # Above ₹3000


class TimeOfDay(str, Enum):
    """Time of day preferences."""
    MORNING = "morning"      # 6 AM - 12 PM
    AFTERNOON = "afternoon"  # 12 PM - 6 PM
    EVENING = "evening"      # 6 PM - 10 PM
    NIGHT = "night"         # 10 PM - 6 AM
    LATE_NIGHT = "late_night" # After 11 PM


class Mood(str, Enum):
    """Mood and ambiance preferences."""
    QUIET = "quiet"
    LIVELY = "lively"
    ROMANTIC = "romantic"
    CASUAL = "casual"
    FORMAL = "formal"
    FAMILY_FRIENDLY = "family_friendly"
    DATE_SPOT = "date_spot"
    WORK_FRIENDLY = "work_friendly"
    PARTY = "party"
    RELAXED = "relaxed"


class LocationPreference(BaseModel):
    """Location-related preferences."""
    
    city: Optional[str] = Field(None, description="Preferred city")
    area: Optional[str] = Field(None, description="Specific area or neighborhood")
    landmark: Optional[str] = Field(None, description="Near specific landmark")
    max_distance_km: Optional[float] = Field(None, description="Maximum distance in kilometers")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Lat/lng if specified")


class TimePreference(BaseModel):
    """Time-related preferences."""
    
    open_now: bool = Field(False, description="Must be open right now")
    time_of_day: Optional[TimeOfDay] = Field(None, description="Preferred time of day")
    specific_time: Optional[str] = Field(None, description="Specific time (HH:MM format)")
    day_of_week: Optional[str] = Field(None, description="Specific day preference")


class BudgetPreference(BaseModel):
    """Budget-related preferences."""
    
    price_range: Optional[PriceRange] = Field(None, description="General price range")
    max_budget: Optional[int] = Field(None, description="Maximum budget in rupees")
    min_budget: Optional[int] = Field(None, description="Minimum budget in rupees")
    budget_per_person: Optional[int] = Field(None, description="Budget per person")


class SearchIntent(BaseModel):
    """Complete search intent extracted from natural language query."""
    
    # Core intent
    original_query: str = Field(..., description="Original search query")
    primary_category: Optional[IntentCategory] = Field(None, description="Primary business category")
    secondary_categories: List[IntentCategory] = Field(default_factory=list, description="Additional categories")
    
    # Specific requirements
    keywords: List[str] = Field(default_factory=list, description="Important keywords from query")
    required_amenities: List[str] = Field(default_factory=list, description="Must-have amenities")
    preferred_amenities: List[str] = Field(default_factory=list, description="Nice-to-have amenities")
    
    # Context and preferences
    location: Optional[LocationPreference] = Field(None, description="Location preferences")
    time: Optional[TimePreference] = Field(None, description="Time preferences")
    budget: Optional[BudgetPreference] = Field(None, description="Budget preferences")
    
    # Ambiance and mood
    mood: Optional[Mood] = Field(None, description="Desired mood/ambiance")
    group_size: Optional[int] = Field(None, description="Number of people")
    occasion: Optional[str] = Field(None, description="Special occasion (birthday, date, etc.)")
    
    # Dietary and special requirements
    dietary_preferences: List[str] = Field(default_factory=list, description="Dietary restrictions/preferences")
    accessibility_needs: List[str] = Field(default_factory=list, description="Accessibility requirements")
    
    # Quality preferences
    min_rating: Optional[float] = Field(None, description="Minimum required rating", ge=1.0, le=5.0)
    verified_only: bool = Field(False, description="Only show verified businesses")
    
    # AI confidence and metadata
    confidence_score: Optional[float] = Field(None, description="AI confidence in extraction", ge=0.0, le=1.0)
    extraction_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional extraction metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class IntentExtractionResult(BaseModel):
    """Result of intent extraction process."""
    
    intent: SearchIntent = Field(..., description="Extracted search intent")
    success: bool = Field(..., description="Whether extraction was successful")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")
    processing_time_ms: Optional[int] = Field(None, description="Time taken for extraction")
    
    # Extracted entities for debugging
    entities: Optional[Dict[str, Any]] = Field(None, description="Raw entities extracted by AI")
    
    
class CommonQueries(BaseModel):
    """Common query patterns for intent training."""
    
    pattern: str = Field(..., description="Query pattern")
    expected_intent: SearchIntent = Field(..., description="Expected intent for this pattern")
    examples: List[str] = Field(..., description="Example queries matching this pattern")