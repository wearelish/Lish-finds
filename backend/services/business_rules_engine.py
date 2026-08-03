"""
Business Rules Engine

Validates and enforces location-specific business constraints including:
- Pricing validation (e.g., no movie tickets under ₹70)
- Operating hours validation
- Cultural and legal restrictions
- Location-based availability
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, time
import json
from enum import Enum
import logging

from ..models.business_constraints import (
    BusinessType, PricingTier, MovieTheaterConstraints,
    RestaurantConstraints, get_movie_theater_pricing_rules,
    get_restaurant_pricing_rules
)
from ..services.location_service import Location, LocationService

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of business rule validation"""
    
    def __init__(self, valid: bool, message: str = "", 
                 corrected_value: Any = None, warnings: List[str] = None):
        self.valid = valid
        self.message = message
        self.corrected_value = corrected_value
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "message": self.message,
            "corrected_value": self.corrected_value,
            "warnings": self.warnings
        }


class BusinessRulesEngine:
    """Enforces location-specific business rules and constraints"""
    
    def __init__(self):
        self.location_service = LocationService()
        
        # Load static pricing rules
        self.movie_pricing_rules = get_movie_theater_pricing_rules()
        self.restaurant_pricing_rules = get_restaurant_pricing_rules()
        
        # Define location tiers
        self.location_tiers = {
            "premium_metro": {
                "cities": [
                    "mumbai_bkc", "mumbai_lower_parel", "mumbai_worli",
                    "delhi_cp", "delhi_gurgaon_cyber_city", "delhi_nehru_place",
                    "bangalore_ub_city", "bangalore_koramangala", "bangalore_indiranagar"
                ],
                "rent_multiplier": 3.0
            },
            "metro": {
                "cities": [
                    "mumbai", "delhi", "bangalore", "hyderabad", "pune", 
                    "chennai", "kolkata", "ahmedabad"
                ],
                "rent_multiplier": 2.0
            },
            "tier1": {
                "cities": [
                    "jaipur", "lucknow", "kanpur", "nagpur", "indore", 
                    "bhopal", "visakhapatnam", "kochi", "coimbatore"
                ],
                "rent_multiplier": 1.5
            },
            "tier2": {
                "cities": [
                    "patna", "vadodara", "ludhiana", "agra", "nashik",
                    "rajkot", "varanasi", "meerut", "faridabad"
                ],
                "rent_multiplier": 1.2
            },
            "tier3": {
                "cities": [],  # All other cities
                "rent_multiplier": 1.0
            }
        }
    
    def validate_movie_ticket_price(self, price: float, location: Location,
                                  screen_type: str = "regular", 
                                  show_time: Optional[datetime] = None,
                                  is_weekend: bool = False,
                                  is_holiday: bool = False) -> ValidationResult:
        """
        Validate movie ticket price - ABSOLUTE MINIMUM ₹70 ANYWHERE
        """
        
        # HARD RULE: NO TICKET UNDER ₹70 ANYWHERE IN INDIA
        if price < 70.0:
            return ValidationResult(
                valid=False,
                message=f"Movie ticket price ₹{price} is invalid. No theater in India sells tickets under ₹70.",
                corrected_value=70.0,
                warnings=["This is a hard constraint - no exceptions allowed"]
            )
        
        # Determine location tier
        tier = self._get_location_tier(location)
        pricing_info = self.movie_pricing_rules["tier_pricing"][tier]
        
        # Get base price range for screen type
        if screen_type == "regular":
            price_range = pricing_info["base_range"]
        elif screen_type in ["gold", "premium", "platinum"]:
            price_range = pricing_info["premium_range"]
        elif screen_type in ["imax", "4dx"]:
            price_range = pricing_info["imax_range"]
        else:
            price_range = pricing_info["base_range"]
        
        min_price, max_price = price_range
        
        # Apply surcharges
        expected_price = min_price
        surcharge_details = []
        
        if is_weekend:
            weekend_surcharge = self.movie_pricing_rules["surcharges"]["weekend"]
            expected_price *= (1 + weekend_surcharge / 100)
            surcharge_details.append(f"Weekend surcharge: +{weekend_surcharge}%")
        
        if is_holiday:
            holiday_surcharge = self.movie_pricing_rules["surcharges"]["holiday"]
            expected_price *= (1 + holiday_surcharge / 100)
            surcharge_details.append(f"Holiday surcharge: +{holiday_surcharge}%")
        
        if show_time:
            if self._is_prime_time(show_time):
                prime_surcharge = self.movie_pricing_rules["surcharges"]["prime_time"]
                expected_price *= (1 + prime_surcharge / 100)
                surcharge_details.append(f"Prime time surcharge: +{prime_surcharge}%")
        
        # Validate against expected range
        warnings = []
        
        if price < expected_price * 0.8:  # 20% below expected minimum
            warnings.append(f"Price seems too low for {tier} location. Expected minimum: ₹{expected_price:.0f}")
        
        if price > max_price * 1.5:  # 50% above maximum
            warnings.append(f"Price seems too high for {tier} location. Expected maximum: ₹{max_price:.0f}")
        
        # Always valid if above ₹70
        return ValidationResult(
            valid=True,
            message=f"Valid price for {screen_type} screen in {tier} location ({location.city})",
            warnings=warnings
        )
    
    def validate_restaurant_pricing(self, price_per_person: float, location: Location,
                                  restaurant_type: str = "casual_dining") -> ValidationResult:
        """Validate restaurant pricing per person"""
        
        tier = self._get_location_tier(location)
        
        if restaurant_type not in self.restaurant_pricing_rules:
            return ValidationResult(
                valid=False,
                message=f"Unknown restaurant type: {restaurant_type}"
            )
        
        price_range = self.restaurant_pricing_rules[restaurant_type][tier]
        min_price, max_price = price_range
        
        if price_per_person < min_price * 0.5:  # Significantly below minimum
            return ValidationResult(
                valid=False,
                message=f"Price ₹{price_per_person} too low for {restaurant_type} in {tier} location. Minimum expected: ₹{min_price}",
                corrected_value=min_price
            )
        
        if price_per_person > max_price * 2:  # Significantly above maximum
            return ValidationResult(
                valid=False,
                message=f"Price ₹{price_per_person} too high for {restaurant_type} in {tier} location. Maximum expected: ₹{max_price}",
                corrected_value=max_price
            )
        
        warnings = []
        if price_per_person < min_price:
            warnings.append(f"Price below typical range for {restaurant_type} in {location.city}")
        if price_per_person > max_price:
            warnings.append(f"Price above typical range for {restaurant_type} in {location.city}")
        
        return ValidationResult(
            valid=True,
            message=f"Valid pricing for {restaurant_type} in {tier} location",
            warnings=warnings
        )
    
    def validate_business_hours(self, business_type: str, location: Location,
                              hours: Dict[str, Any]) -> ValidationResult:
        """Validate business operating hours against local constraints"""
        
        # Default constraints for different business types
        hour_constraints = {
            "movie_theater": {"earliest": "06:00", "latest": "02:00"},
            "restaurant": {"earliest": "05:00", "latest": "02:00"},
            "shopping_mall": {"earliest": "09:00", "latest": "23:00"},
            "bar": {"earliest": "11:00", "latest": "01:30"},  # Most states close bars at 1:30 AM
            "liquor_shop": {"earliest": "10:00", "latest": "22:00"},  # Strict timings
            "pharmacy": {"earliest": "06:00", "latest": "24:00"},
            "bank": {"earliest": "09:00", "latest": "17:00"},
        }
        
        # State-specific restrictions
        state_restrictions = self._get_state_restrictions(location.state)
        
        constraints = hour_constraints.get(business_type, {"earliest": "06:00", "latest": "23:00"})
        warnings = []
        
        # Validate opening and closing times
        try:
            opening_time = datetime.strptime(hours.get("opening", "09:00"), "%H:%M").time()
            closing_time = datetime.strptime(hours.get("closing", "21:00"), "%H:%M").time()
            earliest_allowed = datetime.strptime(constraints["earliest"], "%H:%M").time()
            latest_allowed = datetime.strptime(constraints["latest"], "%H:%M").time()
            
            if opening_time < earliest_allowed:
                warnings.append(f"Opening time {hours['opening']} is earlier than typically allowed for {business_type}")
            
            if closing_time > latest_allowed:
                return ValidationResult(
                    valid=False,
                    message=f"Closing time {hours['closing']} violates regulations for {business_type} in {location.state}"
                )
            
            # Check state-specific restrictions
            if business_type == "bar" and location.state in ["Gujarat", "Bihar"]:
                return ValidationResult(
                    valid=False,
                    message=f"Bars are not permitted in {location.state} (dry state)"
                )
            
            return ValidationResult(
                valid=True,
                message=f"Valid operating hours for {business_type}",
                warnings=warnings
            )
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                message=f"Invalid time format in hours: {e}"
            )
    
    def validate_business_availability(self, business_type: str, location: Location,
                                     date: datetime) -> ValidationResult:
        """Validate if business can operate on given date"""
        
        # Check for dry days (alcohol sales banned)
        if business_type in ["bar", "liquor_shop", "restaurant_with_bar"]:
            if self._is_dry_day(date, location.state):
                return ValidationResult(
                    valid=False,
                    message=f"Alcohol sales not permitted on {date.strftime('%Y-%m-%d')} in {location.state}"
                )
        
        # Check for festival closures
        festival_closures = self._get_festival_closures(date, location.state)
        if festival_closures:
            warnings = [f"May be closed due to {festival_closures}"]
            return ValidationResult(
                valid=True,
                message="Business may be closed for festival",
                warnings=warnings
            )
        
        return ValidationResult(
            valid=True,
            message="Business can operate on this date"
        )
    
    def get_dynamic_pricing_factors(self, business_type: str, location: Location,
                                  datetime_obj: datetime) -> Dict[str, float]:
        """Get dynamic pricing factors based on location and time"""
        
        factors = {
            "base_multiplier": 1.0,
            "location_multiplier": 1.0,
            "time_multiplier": 1.0,
            "demand_multiplier": 1.0,
            "seasonal_multiplier": 1.0
        }
        
        # Location-based multiplier
        tier = self._get_location_tier(location)
        tier_multipliers = {
            "premium_metro": 1.8,
            "metro": 1.4,
            "tier1": 1.2,
            "tier2": 1.0,
            "tier3": 0.85
        }
        factors["location_multiplier"] = tier_multipliers.get(tier, 1.0)
        
        # Time-based factors
        if datetime_obj.weekday() >= 5:  # Weekend
            factors["time_multiplier"] *= 1.15
        
        if datetime_obj.hour >= 18 and datetime_obj.hour <= 22:  # Prime time
            factors["time_multiplier"] *= 1.10
        
        # Seasonal factors (monsoon, festival seasons)
        month = datetime_obj.month
        if month in [6, 7, 8, 9]:  # Monsoon season
            if business_type in ["movie_theater", "shopping_mall"]:
                factors["seasonal_multiplier"] *= 1.05  # Indoor activities increase
            elif business_type in ["outdoor_restaurant", "park"]:
                factors["seasonal_multiplier"] *= 0.9   # Outdoor activities decrease
        
        if month in [10, 11, 12]:  # Festival season
            factors["seasonal_multiplier"] *= 1.15
        
        return factors
    
    def _get_location_tier(self, location: Location) -> str:
        """Determine pricing tier based on location"""
        if not location.city:
            return "tier3"
        
        city_key = location.city.lower().replace(" ", "_")
        
        # Check for premium metro areas
        for tier, data in self.location_tiers.items():
            if tier == "tier3":
                continue
                
            if city_key in data["cities"]:
                return tier
            
            # Check if city name contains any of the tier cities
            for tier_city in data["cities"]:
                if tier_city.replace("_", " ") in city_key:
                    return tier
        
        # Check metro cities
        metro_cities = [
            "mumbai", "delhi", "bangalore", "hyderabad", "pune", 
            "chennai", "kolkata", "ahmedabad"
        ]
        
        for metro in metro_cities:
            if metro in city_key:
                return "metro"
        
        # Check tier 1 cities
        tier1_cities = [
            "jaipur", "lucknow", "kanpur", "nagpur", "indore", 
            "bhopal", "visakhapatnam", "kochi", "coimbatore",
            "surat", "vadodara", "rajkot", "ludhiana"
        ]
        
        for t1_city in tier1_cities:
            if t1_city in city_key:
                return "tier1"
        
        # Default to tier2 for known cities, tier3 for unknown
        return "tier2"
    
    def _is_prime_time(self, show_time: datetime) -> bool:
        """Check if show time is during prime hours (6-10 PM)"""
        hour = show_time.hour
        return 18 <= hour <= 22
    
    def _get_state_restrictions(self, state: Optional[str]) -> Dict[str, Any]:
        """Get state-specific business restrictions"""
        restrictions = {
            "Gujarat": {
                "dry_state": True,
                "alcohol_banned": True,
                "sunday_restrictions": False
            },
            "Bihar": {
                "dry_state": True,
                "alcohol_banned": True,
                "sunday_restrictions": False
            },
            "Nagaland": {
                "dry_state": True,
                "alcohol_banned": True,
                "sunday_restrictions": True  # Christian majority state
            },
            "Mizoram": {
                "dry_state": True,
                "alcohol_banned": True,
                "sunday_restrictions": True
            },
            "Manipur": {
                "dry_state": False,
                "alcohol_banned": False,
                "sunday_restrictions": True
            }
        }
        
        return restrictions.get(state, {
            "dry_state": False,
            "alcohol_banned": False,
            "sunday_restrictions": False
        })
    
    def _is_dry_day(self, date: datetime, state: Optional[str]) -> bool:
        """Check if it's a dry day (no alcohol sales)"""
        
        # National dry days
        dry_days_2024 = [
            "2024-01-26",  # Republic Day
            "2024-03-08",  # Holi
            "2024-03-29",  # Good Friday
            "2024-08-15",  # Independence Day
            "2024-10-02",  # Gandhi Jayanti
            "2024-11-01",  # Diwali (varies by state)
        ]
        
        date_str = date.strftime("%Y-%m-%d")
        
        # Check national dry days
        if date_str in dry_days_2024:
            return True
        
        # Check state-specific dry days
        state_restrictions = self._get_state_restrictions(state)
        if state_restrictions.get("dry_state", False):
            return True
        
        # Some states have additional monthly dry days
        if state in ["Maharashtra", "Karnataka"]:
            # First and third Saturdays in some regions
            if date.weekday() == 5:  # Saturday
                day = date.day
                if 1 <= day <= 7 or 15 <= day <= 21:
                    return True
        
        return False
    
    def _get_festival_closures(self, date: datetime, state: Optional[str]) -> Optional[str]:
        """Check for major festival closures"""
        
        # Major festivals that typically close businesses
        festivals_2024 = {
            "2024-03-08": "Holi",
            "2024-04-17": "Ram Navami",
            "2024-08-19": "Raksha Bandhan",
            "2024-08-26": "Janmashtami",
            "2024-09-07": "Ganesh Chaturthi",
            "2024-10-31": "Diwali",
            "2024-11-01": "Govardhan Puja",
            "2024-11-02": "Bhai Dooj",
            "2024-12-25": "Christmas"
        }
        
        date_str = date.strftime("%Y-%m-%d")
        return festivals_2024.get(date_str)
    
    def get_location_specific_constraints(self, business_type: str, 
                                        location: Location) -> Dict[str, Any]:
        """Get all location-specific constraints for a business type"""
        
        tier = self._get_location_tier(location)
        state_restrictions = self._get_state_restrictions(location.state)
        
        constraints = {
            "location_tier": tier,
            "pricing_tier": tier,
            "state_restrictions": state_restrictions,
            "business_specific": {}
        }
        
        # Add business-specific constraints
        if business_type == "movie_theater":
            constraints["business_specific"] = {
                "minimum_price": 70.0,  # ABSOLUTE MINIMUM
                "pricing_range": self.movie_pricing_rules["tier_pricing"][tier],
                "surcharges": self.movie_pricing_rules["surcharges"],
                "screen_multipliers": self.movie_pricing_rules["screen_multipliers"]
            }
        
        elif business_type in ["restaurant", "cafe"]:
            constraints["business_specific"] = {
                "pricing_ranges": {
                    rt: self.restaurant_pricing_rules[rt][tier] 
                    for rt in self.restaurant_pricing_rules.keys()
                },
                "gst_rates": self.restaurant_pricing_rules["additional_charges"]
            }
        
        return constraints