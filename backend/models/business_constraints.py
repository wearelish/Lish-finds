"""
Business Constraints Models

Defines real-world business rules and constraints including:
- Location-specific pricing rules
- Operating hours and seasonal availability
- Business type constraints
- Regulatory and legal requirements
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime, time
from typing import Dict, Any, List, Optional
import json

Base = declarative_base()


class BusinessType(Enum):
    """Types of businesses with specific constraints"""
    MOVIE_THEATER = "movie_theater"
    RESTAURANT = "restaurant"
    SHOPPING_MALL = "shopping_mall"
    GROCERY_STORE = "grocery_store"
    PHARMACY = "pharmacy"
    BANK = "bank"
    ATM = "atm"
    HOSPITAL = "hospital"
    GAS_STATION = "gas_station"
    HOTEL = "hotel"
    CAFE = "cafe"
    BAR = "bar"
    GYM = "gym"
    SALON = "salon"
    ELECTRONICS_STORE = "electronics_store"
    CLOTHING_STORE = "clothing_store"
    BOOKSTORE = "bookstore"
    TEMPLE = "temple"
    MOSQUE = "mosque"
    CHURCH = "church"
    PARK = "park"
    MUSEUM = "museum"


class PricingTier(Enum):
    """Pricing tiers based on location premium"""
    PREMIUM_METRO = "premium_metro"  # Mumbai, Delhi NCR, Bangalore CBD
    METRO = "metro"  # Other metro cities
    TIER1 = "tier1"  # Major cities
    TIER2 = "tier2"  # Smaller cities
    TIER3 = "tier3"  # Towns


class BusinessConstraint(Base):
    """Base business constraint model"""
    __tablename__ = "business_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    business_type = Column(String(50), nullable=False)
    constraint_type = Column(String(50), nullable=False)  # pricing, hours, availability, legal
    
    # Location constraints
    city = Column(String(100))
    state = Column(String(50))
    area_type = Column(String(50))  # commercial, residential, industrial
    pricing_tier = Column(String(20))
    
    # Constraint data (JSON for flexibility)
    constraint_data = Column(JSON)
    
    # Metadata
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Validation rules
    validation_rules = Column(JSON)
    
    def __repr__(self):
        return f"<BusinessConstraint {self.business_type}:{self.constraint_type}>"


class MovieTheaterConstraints(Base):
    """Movie theater specific constraints"""
    __tablename__ = "movie_theater_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location details
    city = Column(String(100), nullable=False)
    area = Column(String(100))
    pricing_tier = Column(String(20), nullable=False)
    
    # Pricing constraints - NO TICKET UNDER ₹70
    minimum_ticket_price = Column(Float, nullable=False, default=70.0)
    maximum_ticket_price = Column(Float, nullable=False)
    
    # Show time constraints
    earliest_show_time = Column(String(8), default="09:00")  # Format: HH:MM
    latest_show_time = Column(String(8), default="23:30")
    
    # Premium pricing rules
    weekend_surcharge_percent = Column(Float, default=20.0)
    holiday_surcharge_percent = Column(Float, default=30.0)
    prime_time_surcharge_percent = Column(Float, default=15.0)  # 6-10 PM
    
    # Screen type pricing multipliers
    regular_screen_multiplier = Column(Float, default=1.0)
    premium_screen_multiplier = Column(Float, default=1.5)  # Gold, Platinum
    imax_multiplier = Column(Float, default=2.0)
    d4_multiplier = Column(Float, default=1.8)
    recliner_multiplier = Column(Float, default=2.2)
    
    # Booking constraints
    advance_booking_days = Column(Integer, default=7)
    cancellation_hours = Column(Integer, default=2)  # Hours before show
    
    # Legal constraints
    intermission_required = Column(Boolean, default=True)  # Indian cinema rule
    max_decibel_level = Column(Float, default=85.0)  # Legal sound limit
    
    # Business rules
    food_pricing_markup = Column(Float, default=300.0)  # 300% markup on outside price
    parking_available = Column(Boolean, default=True)
    
    def get_base_price_range(self) -> Dict[str, float]:
        """Get base price range for this location"""
        tier_multipliers = {
            "premium_metro": 1.8,  # Mumbai Lower Parel, Delhi CP, Bangalore UB City
            "metro": 1.4,  # Other metro locations
            "tier1": 1.2,  # Major cities
            "tier2": 1.0,  # Base tier
            "tier3": 0.8   # Small towns (but still min ₹70)
        }
        
        multiplier = tier_multipliers.get(self.pricing_tier, 1.0)
        base_min = max(self.minimum_ticket_price, 70.0)  # NEVER below ₹70
        
        return {
            "minimum": base_min,
            "maximum": self.maximum_ticket_price * multiplier,
            "regular": base_min * multiplier,
            "premium": base_min * multiplier * self.premium_screen_multiplier
        }


class RestaurantConstraints(Base):
    """Restaurant specific constraints"""
    __tablename__ = "restaurant_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location and type
    city = Column(String(100), nullable=False)
    area = Column(String(100))
    pricing_tier = Column(String(20), nullable=False)
    restaurant_type = Column(String(50))  # fine_dining, casual, fast_food, street_food
    
    # Operating constraints
    earliest_opening = Column(String(8), default="06:00")
    latest_closing = Column(String(8), default="23:00")
    
    # Pricing constraints per person
    minimum_order_value = Column(Float, default=0.0)
    maximum_price_per_person = Column(Float)
    
    # Legal requirements
    fssai_required = Column(Boolean, default=True)
    liquor_license_area = Column(Boolean, default=False)  # Some areas don't allow
    smoking_allowed = Column(Boolean, default=False)  # Most places ban indoor smoking
    
    # Business constraints
    service_charge_percent = Column(Float, default=10.0)
    gst_percent = Column(Float, default=5.0)  # Food GST in India
    delivery_radius_km = Column(Float, default=5.0)
    
    # Cultural constraints
    veg_only_areas = Column(Boolean, default=False)  # Some areas are vegetarian only
    halal_required_areas = Column(Boolean, default=False)
    alcohol_restricted_areas = Column(Boolean, default=False)
    
    def get_price_range_per_person(self) -> Dict[str, float]:
        """Get typical price range per person"""
        base_prices = {
            "street_food": {"min": 50, "max": 200},
            "fast_food": {"min": 150, "max": 400},
            "casual": {"min": 300, "max": 800},
            "fine_dining": {"min": 800, "max": 3000}
        }
        
        tier_multipliers = {
            "premium_metro": 1.6,
            "metro": 1.3,
            "tier1": 1.1,
            "tier2": 1.0,
            "tier3": 0.8
        }
        
        base = base_prices.get(self.restaurant_type, {"min": 200, "max": 600})
        multiplier = tier_multipliers.get(self.pricing_tier, 1.0)
        
        return {
            "minimum": int(base["min"] * multiplier),
            "maximum": int(base["max"] * multiplier)
        }


class ShoppingConstraints(Base):
    """Shopping mall/store constraints"""
    __tablename__ = "shopping_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location details
    city = Column(String(100), nullable=False)
    area = Column(String(100))
    pricing_tier = Column(String(20), nullable=False)
    store_type = Column(String(50))
    
    # Operating hours
    weekday_opening = Column(String(8), default="10:00")
    weekday_closing = Column(String(8), default="22:00")
    weekend_opening = Column(String(8), default="10:00")
    weekend_closing = Column(String(8), default="23:00")
    
    # Pricing constraints
    discount_season_months = Column(JSON)  # [6, 7, 12] for June, July, December
    max_discount_percent = Column(Float, default=50.0)
    
    # Business rules
    gst_percent = Column(Float, default=18.0)  # Standard GST for most goods
    return_policy_days = Column(Integer, default=7)
    exchange_policy_days = Column(Integer, default=15)
    
    # Payment constraints
    minimum_card_amount = Column(Float, default=0.0)  # Most places accept any amount now
    cash_on_delivery = Column(Boolean, default=True)
    
    # Location specific rules
    luxury_brand_area = Column(Boolean, default=False)  # High-end malls only
    international_brands = Column(Boolean, default=False)


class ServiceConstraints(Base):
    """Service business constraints (salons, gyms, etc.)"""
    __tablename__ = "service_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location and service type
    city = Column(String(100), nullable=False)
    service_type = Column(String(50), nullable=False)
    pricing_tier = Column(String(20), nullable=False)
    
    # Operating constraints
    appointment_required = Column(Boolean, default=False)
    advance_booking_days = Column(Integer, default=7)
    
    # Pricing rules
    base_service_price = Column(Float)
    premium_service_multiplier = Column(Float, default=1.5)
    
    # Business constraints
    membership_required = Column(Boolean, default=False)
    trial_period_days = Column(Integer, default=0)
    
    # Legal requirements
    license_required = Column(Boolean, default=True)
    certified_staff_required = Column(Boolean, default=False)


class LocationBasedPricing(Base):
    """Location-based pricing rules"""
    __tablename__ = "location_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location identifiers
    city = Column(String(100), nullable=False)
    area = Column(String(100))
    pincode = Column(String(10))
    pricing_tier = Column(String(20), nullable=False)
    
    # Business type
    business_type = Column(String(50), nullable=False)
    
    # Price multipliers
    base_price_multiplier = Column(Float, default=1.0)
    rent_factor = Column(Float, default=1.0)  # High rent = higher prices
    competition_factor = Column(Float, default=1.0)  # More competition = lower prices
    affluence_factor = Column(Float, default=1.0)  # Affluent area = higher prices
    
    # Time-based multipliers
    peak_hour_multiplier = Column(Float, default=1.0)
    weekend_multiplier = Column(Float, default=1.0)
    holiday_multiplier = Column(Float, default=1.0)
    
    # Seasonal factors
    summer_factor = Column(Float, default=1.0)
    monsoon_factor = Column(Float, default=1.0)
    winter_factor = Column(Float, default=1.0)
    festival_factor = Column(Float, default=1.0)


class BusinessHours(Base):
    """Location and culture specific business hours"""
    __tablename__ = "business_hours"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location
    city = Column(String(100), nullable=False)
    business_type = Column(String(50), nullable=False)
    
    # Standard hours (JSON format for each day)
    monday_hours = Column(JSON)  # {"open": "09:00", "close": "21:00", "closed": false}
    tuesday_hours = Column(JSON)
    wednesday_hours = Column(JSON)
    thursday_hours = Column(JSON)
    friday_hours = Column(JSON)
    saturday_hours = Column(JSON)
    sunday_hours = Column(JSON)
    
    # Special considerations
    ramadan_hours = Column(JSON)  # Modified hours during Ramadan
    festival_closures = Column(JSON)  # List of festivals when closed
    
    # Regional variations
    lunch_break_hours = Column(JSON)  # Some regions have lunch breaks
    afternoon_closure = Column(JSON)  # Hot regions may close in afternoon


class RegionalConstraints(Base):
    """Regional and cultural constraints"""
    __tablename__ = "regional_constraints"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Location
    state = Column(String(50), nullable=False)
    city = Column(String(100))
    
    # Alcohol restrictions
    dry_state = Column(Boolean, default=False)  # Gujarat, Bihar are dry states
    dry_days = Column(JSON)  # Days when alcohol sales banned
    
    # Food restrictions
    beef_banned = Column(Boolean, default=False)  # Some states ban beef
    pork_restrictions = Column(Boolean, default=False)
    
    # Business restrictions
    sunday_trading_banned = Column(Boolean, default=False)
    late_night_restrictions = Column(Boolean, default=False)
    
    # Cultural considerations
    festival_business_impact = Column(JSON)  # How festivals affect business
    local_language_required = Column(String(20))
    
    # Legal requirements
    state_gst_code = Column(String(10))
    local_taxes = Column(JSON)


def get_movie_theater_pricing_rules() -> Dict[str, Any]:
    """Get comprehensive movie theater pricing rules"""
    return {
        "absolute_minimum": 70.0,  # NO TICKET UNDER ₹70 ANYWHERE
        "tier_pricing": {
            "premium_metro": {
                "base_range": [120, 500],
                "premium_range": [200, 800],
                "imax_range": [300, 1200],
                "examples": ["Mumbai BKC", "Delhi CP", "Bangalore UB City"]
            },
            "metro": {
                "base_range": [90, 350],
                "premium_range": [150, 600],
                "imax_range": [220, 900],
                "examples": ["Mumbai suburbs", "Delhi NCR", "Bangalore IT parks"]
            },
            "tier1": {
                "base_range": [75, 250],
                "premium_range": [120, 400],
                "imax_range": [180, 600],
                "examples": ["Pune", "Hyderabad", "Chennai", "Kolkata"]
            },
            "tier2": {
                "base_range": [70, 200],
                "premium_range": [100, 300],
                "imax_range": [150, 450],
                "examples": ["Indore", "Bhopal", "Coimbatore", "Kochi"]
            },
            "tier3": {
                "base_range": [70, 150],  # Still minimum ₹70
                "premium_range": [90, 220],
                "imax_range": [120, 300],
                "examples": ["Smaller cities", "District headquarters"]
            }
        },
        "surcharges": {
            "weekend": 15,  # 15% extra on Sat-Sun
            "holiday": 25,  # 25% extra on public holidays
            "prime_time": 10,  # 6 PM - 10 PM shows
            "first_day_first_show": 50,  # Popular movie releases
            "last_show": -10   # 10% discount for late shows
        },
        "screen_multipliers": {
            "regular": 1.0,
            "gold_class": 1.8,
            "platinum": 2.2,
            "recliner": 2.0,
            "imax": 2.5,
            "4dx": 2.8,
            "dolby_atmos": 1.3
        },
        "booking_constraints": {
            "advance_booking_days": 7,
            "cancellation_deadline_hours": 2,
            "convenience_fee_percent": 8,
            "processing_fee": 15
        }
    }


def get_restaurant_pricing_rules() -> Dict[str, Any]:
    """Get restaurant pricing rules by type and location"""
    return {
        "street_food": {
            "premium_metro": [80, 300],
            "metro": [60, 250],
            "tier1": [50, 200],
            "tier2": [40, 150],
            "tier3": [30, 100]
        },
        "fast_food": {
            "premium_metro": [200, 600],
            "metro": [150, 500],
            "tier1": [120, 400],
            "tier2": [100, 350],
            "tier3": [80, 250]
        },
        "casual_dining": {
            "premium_metro": [500, 1200],
            "metro": [400, 1000],
            "tier1": [350, 800],
            "tier2": [300, 650],
            "tier3": [250, 500]
        },
        "fine_dining": {
            "premium_metro": [1500, 5000],
            "metro": [1200, 3500],
            "tier1": [1000, 2500],
            "tier2": [800, 1800],
            "tier3": [600, 1200]
        },
        "additional_charges": {
            "service_charge_percent": 10,
            "cgst_percent": 2.5,
            "sgst_percent": 2.5,
            "luxury_tax_threshold": 1000,  # Above ₹1000 per person
            "delivery_fee": [20, 60],
            "packaging_fee": [15, 40]
        }
    }