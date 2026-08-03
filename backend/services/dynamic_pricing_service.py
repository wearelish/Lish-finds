"""
Dynamic Pricing Service

Implements real-time pricing adjustments based on:
- Location-specific factors (rent, competition, affluence)
- Time-based factors (peak hours, weekends, holidays)
- Demand fluctuations and event-driven pricing
- Weather conditions affecting business
- Supply and availability constraints
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, time
from enum import Enum
import math
import logging

from .location_service import Location, LocationService
from .business_rules_engine import BusinessRulesEngine

logger = logging.getLogger(__name__)


class DemandLevel(Enum):
    """Demand intensity levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    SURGE = "surge"


class WeatherCondition(Enum):
    """Weather conditions affecting business"""
    CLEAR = "clear"
    RAINY = "rainy"
    HEAVY_RAIN = "heavy_rain"
    HOT = "hot"
    PLEASANT = "pleasant"
    POLLUTION_HIGH = "pollution_high"


class EventType(Enum):
    """Types of events affecting pricing"""
    MOVIE_RELEASE = "movie_release"
    FESTIVAL = "festival"
    CONCERT = "concert"
    SPORTS_EVENT = "sports_event"
    CONFERENCE = "conference"
    STRIKE = "strike"
    BANDH = "bandh"


class DynamicPricingService:
    """Handles dynamic pricing calculations based on multiple factors"""
    
    def __init__(self):
        self.location_service = LocationService()
        self.business_rules = BusinessRulesEngine()
        
        # Base pricing factors
        self.time_multipliers = self._load_time_multipliers()
        self.demand_multipliers = self._load_demand_multipliers()
        self.weather_multipliers = self._load_weather_multipliers()
        self.event_multipliers = self._load_event_multipliers()
        
    def _load_time_multipliers(self) -> Dict[str, Dict[str, float]]:
        """Load time-based pricing multipliers"""
        return {
            "movie_theater": {
                "early_morning": 0.8,   # 9 AM - 12 PM
                "afternoon": 0.9,       # 12 PM - 6 PM
                "prime_time": 1.2,      # 6 PM - 10 PM
                "late_night": 1.0,      # 10 PM onwards
                "weekend_multiplier": 1.15,
                "holiday_multiplier": 1.25,
                "first_day_first_show": 1.5,  # Popular movie releases
                "last_show_discount": 0.9
            },
            "restaurant": {
                "breakfast": 1.0,       # 7 AM - 11 AM
                "lunch": 1.1,           # 12 PM - 3 PM
                "tea_time": 0.9,        # 3 PM - 6 PM
                "dinner": 1.2,          # 7 PM - 11 PM
                "late_night": 1.3,      # 11 PM onwards (limited places)
                "weekend_brunch": 1.25,
                "valentine_day": 1.5,
                "new_year_eve": 2.0
            },
            "shopping_mall": {
                "weekday_morning": 1.0,
                "weekday_evening": 1.1,
                "weekend": 1.2,
                "sale_season": 0.7,     # Discount seasons
                "festival_shopping": 1.3
            }
        }
    
    def _load_demand_multipliers(self) -> Dict[DemandLevel, float]:
        """Load demand-based multipliers"""
        return {
            DemandLevel.VERY_LOW: 0.8,
            DemandLevel.LOW: 0.9,
            DemandLevel.MEDIUM: 1.0,
            DemandLevel.HIGH: 1.2,
            DemandLevel.VERY_HIGH: 1.4,
            DemandLevel.SURGE: 1.8
        }
    
    def _load_weather_multipliers(self) -> Dict[str, Dict[WeatherCondition, float]]:
        """Load weather-based multipliers by business type"""
        return {
            "movie_theater": {
                WeatherCondition.CLEAR: 1.0,
                WeatherCondition.RAINY: 1.15,      # People prefer indoor activities
                WeatherCondition.HEAVY_RAIN: 1.25,
                WeatherCondition.HOT: 1.1,         # AC comfort
                WeatherCondition.PLEASANT: 0.95,   # People prefer outdoors
                WeatherCondition.POLLUTION_HIGH: 1.2
            },
            "restaurant": {
                WeatherCondition.CLEAR: 1.0,
                WeatherCondition.RAINY: 0.9,       # Delivery issues, less footfall
                WeatherCondition.HEAVY_RAIN: 0.8,
                WeatherCondition.HOT: 1.05,        # Cold drinks, AC dining
                WeatherCondition.PLEASANT: 1.1,    # More dining out
                WeatherCondition.POLLUTION_HIGH: 0.95
            },
            "shopping_mall": {
                WeatherCondition.CLEAR: 1.0,
                WeatherCondition.RAINY: 1.2,       # People flock to malls
                WeatherCondition.HEAVY_RAIN: 1.3,
                WeatherCondition.HOT: 1.15,        # AC comfort
                WeatherCondition.PLEASANT: 0.9,    # Prefer outdoor activities
                WeatherCondition.POLLUTION_HIGH: 1.1
            }
        }
    
    def _load_event_multipliers(self) -> Dict[str, Dict[EventType, float]]:
        """Load event-based multipliers"""
        return {
            "movie_theater": {
                EventType.MOVIE_RELEASE: 1.5,      # Big movie releases
                EventType.FESTIVAL: 1.3,
                EventType.CONCERT: 0.9,            # Competition from concerts
                EventType.SPORTS_EVENT: 0.8,       # People watching at home/venues
                EventType.STRIKE: 0.7,
                EventType.BANDH: 0.6
            },
            "restaurant": {
                EventType.FESTIVAL: 1.4,
                EventType.CONCERT: 1.2,            # Pre/post event dining
                EventType.SPORTS_EVENT: 1.1,       # Watch parties
                EventType.CONFERENCE: 1.15,        # Business dining
                EventType.STRIKE: 0.8,
                EventType.BANDH: 0.5
            },
            "shopping_mall": {
                EventType.FESTIVAL: 1.5,           # Festival shopping
                EventType.CONCERT: 0.9,
                EventType.SPORTS_EVENT: 0.85,
                EventType.CONFERENCE: 1.0,
                EventType.STRIKE: 0.6,
                EventType.BANDH: 0.3
            }
        }
    
    def calculate_dynamic_price(self, base_price: float, business_type: str,
                              location: Location, datetime_obj: datetime,
                              demand_level: DemandLevel = DemandLevel.MEDIUM,
                              weather: WeatherCondition = WeatherCondition.CLEAR,
                              events: List[EventType] = None,
                              availability_percent: float = 100.0) -> Dict[str, Any]:
        """Calculate dynamic price based on all factors"""
        
        if events is None:
            events = []
        
        pricing_breakdown = {
            "base_price": base_price,
            "location_factor": 1.0,
            "time_factor": 1.0,
            "demand_factor": 1.0,
            "weather_factor": 1.0,
            "event_factor": 1.0,
            "availability_factor": 1.0,
            "final_price": base_price,
            "price_change_percent": 0.0,
            "factors_applied": []
        }
        
        # Apply location-based factor
        location_multiplier = self._calculate_location_multiplier(business_type, location)
        pricing_breakdown["location_factor"] = location_multiplier
        pricing_breakdown["factors_applied"].append(f"Location ({location.city}): {location_multiplier:.2f}x")
        
        # Apply time-based factor
        time_multiplier = self._calculate_time_multiplier(business_type, datetime_obj, location)
        pricing_breakdown["time_factor"] = time_multiplier
        pricing_breakdown["factors_applied"].append(f"Time factor: {time_multiplier:.2f}x")
        
        # Apply demand-based factor
        demand_multiplier = self.demand_multipliers.get(demand_level, 1.0)
        pricing_breakdown["demand_factor"] = demand_multiplier
        pricing_breakdown["factors_applied"].append(f"Demand ({demand_level.value}): {demand_multiplier:.2f}x")
        
        # Apply weather factor
        weather_multipliers = self.weather_multipliers.get(business_type, {})
        weather_multiplier = weather_multipliers.get(weather, 1.0)
        pricing_breakdown["weather_factor"] = weather_multiplier
        if weather_multiplier != 1.0:
            pricing_breakdown["factors_applied"].append(f"Weather ({weather.value}): {weather_multiplier:.2f}x")
        
        # Apply event factors
        event_multiplier = 1.0
        event_multipliers = self.event_multipliers.get(business_type, {})
        for event in events:
            event_mult = event_multipliers.get(event, 1.0)
            event_multiplier *= event_mult
            if event_mult != 1.0:
                pricing_breakdown["factors_applied"].append(f"Event ({event.value}): {event_mult:.2f}x")
        pricing_breakdown["event_factor"] = event_multiplier
        
        # Apply availability factor (scarcity pricing)
        availability_multiplier = self._calculate_availability_multiplier(
            availability_percent, business_type
        )
        pricing_breakdown["availability_factor"] = availability_multiplier
        if availability_multiplier != 1.0:
            pricing_breakdown["factors_applied"].append(f"Availability ({availability_percent:.0f}%): {availability_multiplier:.2f}x")
        
        # Calculate final price
        total_multiplier = (
            location_multiplier * time_multiplier * demand_multiplier * 
            weather_multiplier * event_multiplier * availability_multiplier
        )
        
        final_price = base_price * total_multiplier
        
        # Apply business-specific constraints
        final_price = self._apply_price_constraints(final_price, business_type, location)
        
        pricing_breakdown["final_price"] = round(final_price, 2)
        pricing_breakdown["price_change_percent"] = round(((final_price - base_price) / base_price) * 100, 1)
        
        return pricing_breakdown
    
    def _calculate_location_multiplier(self, business_type: str, location: Location) -> float:
        """Calculate location-based pricing multiplier"""
        
        tier = self.business_rules._get_location_tier(location)
        
        # Base location multipliers
        tier_multipliers = {
            "premium_metro": 1.6,   # High-end areas like BKC, CP, UB City
            "metro": 1.3,           # Metro cities
            "tier1": 1.1,           # Major cities
            "tier2": 1.0,           # Medium cities
            "tier3": 0.9            # Smaller cities
        }
        
        base_multiplier = tier_multipliers.get(tier, 1.0)
        
        # Business-type specific adjustments
        if business_type == "movie_theater":
            # Theaters in malls have higher overhead
            if "mall" in (location.area or "").lower():
                base_multiplier *= 1.1
        
        elif business_type == "restaurant":
            # Fine dining areas command premium
            if tier == "premium_metro":
                base_multiplier *= 1.2
        
        return base_multiplier
    
    def _calculate_time_multiplier(self, business_type: str, datetime_obj: datetime, 
                                 location: Location) -> float:
        """Calculate time-based multiplier"""
        
        multipliers = self.time_multipliers.get(business_type, {})
        hour = datetime_obj.hour
        weekday = datetime_obj.weekday()  # 0=Monday, 6=Sunday
        
        base_multiplier = 1.0
        
        if business_type == "movie_theater":
            # Time of day multipliers
            if 9 <= hour < 12:
                base_multiplier = multipliers.get("early_morning", 1.0)
            elif 12 <= hour < 18:
                base_multiplier = multipliers.get("afternoon", 1.0)
            elif 18 <= hour < 22:
                base_multiplier = multipliers.get("prime_time", 1.0)
            else:
                base_multiplier = multipliers.get("late_night", 1.0)
            
            # Weekend premium
            if weekday >= 5:  # Saturday, Sunday
                base_multiplier *= multipliers.get("weekend_multiplier", 1.0)
            
        elif business_type == "restaurant":
            # Meal time multipliers
            if 7 <= hour < 11:
                base_multiplier = multipliers.get("breakfast", 1.0)
            elif 12 <= hour < 15:
                base_multiplier = multipliers.get("lunch", 1.0)
            elif 15 <= hour < 18:
                base_multiplier = multipliers.get("tea_time", 1.0)
            elif 19 <= hour < 23:
                base_multiplier = multipliers.get("dinner", 1.0)
            elif hour >= 23 or hour < 2:
                base_multiplier = multipliers.get("late_night", 1.0)
            
        return base_multiplier
    
    def _calculate_availability_multiplier(self, availability_percent: float, 
                                         business_type: str) -> float:
        """Calculate scarcity-based pricing multiplier"""
        
        if availability_percent >= 80:
            return 1.0  # Normal pricing
        elif availability_percent >= 60:
            return 1.05  # Slight premium
        elif availability_percent >= 40:
            return 1.1   # Moderate premium
        elif availability_percent >= 20:
            return 1.2   # High premium
        elif availability_percent >= 10:
            return 1.35  # Very high premium
        else:
            return 1.5   # Surge pricing
    
    def _apply_price_constraints(self, calculated_price: float, business_type: str, 
                               location: Location) -> float:
        """Apply business-specific price constraints"""
        
        if business_type == "movie_theater":
            # ABSOLUTE MINIMUM: No movie ticket below ₹70
            if calculated_price < 70:
                logger.warning(f"Movie ticket price {calculated_price} adjusted to ₹70 minimum")
                return 70.0
            
            # Maximum reasonable limit (to prevent extreme surge)
            tier = self.business_rules._get_location_tier(location)
            max_limits = {
                "premium_metro": 800,
                "metro": 600,
                "tier1": 450,
                "tier2": 350,
                "tier3": 250
            }
            max_limit = max_limits.get(tier, 400)
            
            if calculated_price > max_limit:
                logger.info(f"Movie ticket price capped at ₹{max_limit} for {tier}")
                return max_limit
        
        elif business_type == "restaurant":
            # Minimum viable pricing
            if calculated_price < 50:
                return 50.0
        
        return calculated_price
    
    def get_demand_level(self, business_type: str, location: Location, 
                        datetime_obj: datetime) -> DemandLevel:
        """Estimate current demand level based on various factors"""
        
        hour = datetime_obj.hour
        weekday = datetime_obj.weekday()
        
        # Base demand by time and day
        if business_type == "movie_theater":
            if weekday >= 5:  # Weekend
                if 18 <= hour <= 22:
                    return DemandLevel.VERY_HIGH
                elif 12 <= hour <= 18:
                    return DemandLevel.HIGH
                else:
                    return DemandLevel.MEDIUM
            else:  # Weekday
                if 19 <= hour <= 22:
                    return DemandLevel.HIGH
                elif 12 <= hour <= 18:
                    return DemandLevel.MEDIUM
                else:
                    return DemandLevel.LOW
        
        elif business_type == "restaurant":
            if 12 <= hour <= 14 or 19 <= hour <= 21:  # Meal times
                if weekday >= 5:
                    return DemandLevel.HIGH
                else:
                    return DemandLevel.MEDIUM
            else:
                return DemandLevel.LOW
        
        return DemandLevel.MEDIUM
    
    def get_weather_condition(self, location: Location, 
                            datetime_obj: Optional[datetime] = None) -> WeatherCondition:
        """Get current weather condition (mock implementation)"""
        
        if datetime_obj is None:
            datetime_obj = datetime.now()
        
        # Mock weather based on season and location
        month = datetime_obj.month
        
        # Monsoon season
        if 6 <= month <= 9:
            if location.city and location.city.lower() in ["mumbai", "bangalore", "kochi"]:
                return WeatherCondition.RAINY
        
        # Summer months
        if 3 <= month <= 6:
            if location.city and location.city.lower() in ["delhi", "ahmedabad", "nagpur"]:
                return WeatherCondition.HOT
        
        # Pollution season in North India
        if 10 <= month <= 2:
            if location.city and location.city.lower() in ["delhi", "gurgaon", "noida"]:
                return WeatherCondition.POLLUTION_HIGH
        
        return WeatherCondition.CLEAR
    
    def get_active_events(self, location: Location, 
                         datetime_obj: datetime) -> List[EventType]:
        """Get active events affecting pricing (mock implementation)"""
        
        events = []
        
        # Festival seasons
        month = datetime_obj.month
        day = datetime_obj.day
        
        # Diwali season (October-November)
        if month == 10 or (month == 11 and day <= 15):
            events.append(EventType.FESTIVAL)
        
        # Christmas/New Year season
        if month == 12 and day >= 20:
            events.append(EventType.FESTIVAL)
        
        # Check for movie releases (Fridays)
        if datetime_obj.weekday() == 4:  # Friday
            events.append(EventType.MOVIE_RELEASE)
        
        # Weekend events in metro cities
        if datetime_obj.weekday() >= 5:  # Weekend
            tier = self.business_rules._get_location_tier(location)
            if tier in ["premium_metro", "metro"]:
                # Assume some events in metro areas on weekends
                if datetime_obj.hour >= 19:
                    events.append(EventType.CONCERT)
        
        return events
    
    def get_availability_estimate(self, business_type: str, location: Location,
                                datetime_obj: datetime) -> float:
        """Estimate current availability percentage"""
        
        # Base availability by business type and time
        hour = datetime_obj.hour
        weekday = datetime_obj.weekday()
        
        if business_type == "movie_theater":
            if weekday >= 5 and 18 <= hour <= 22:  # Weekend prime time
                return 30.0  # High demand, low availability
            elif 19 <= hour <= 22:  # Weekday prime time
                return 60.0
            else:
                return 85.0
        
        elif business_type == "restaurant":
            if (12 <= hour <= 14) or (19 <= hour <= 21):  # Meal times
                if weekday >= 5:
                    return 40.0  # Weekend meal times
                else:
                    return 70.0  # Weekday meal times
            else:
                return 90.0
        
        elif business_type == "shopping_mall":
            if weekday >= 5:  # Weekend
                return 60.0
            else:
                return 80.0
        
        return 75.0  # Default
    
    def calculate_real_time_pricing(self, business_id: str, base_price: float,
                                  business_type: str, location: Location) -> Dict[str, Any]:
        """Calculate real-time pricing with all current factors"""
        
        current_time = datetime.now()
        
        # Get current conditions
        demand_level = self.get_demand_level(business_type, location, current_time)
        weather = self.get_weather_condition(location, current_time)
        events = self.get_active_events(location, current_time)
        availability = self.get_availability_estimate(business_type, location, current_time)
        
        # Calculate dynamic pricing
        pricing_result = self.calculate_dynamic_price(
            base_price=base_price,
            business_type=business_type,
            location=location,
            datetime_obj=current_time,
            demand_level=demand_level,
            weather=weather,
            events=events,
            availability_percent=availability
        )
        
        # Add real-time context
        pricing_result.update({
            "business_id": business_id,
            "timestamp": current_time.isoformat(),
            "current_conditions": {
                "demand_level": demand_level.value,
                "weather": weather.value,
                "active_events": [e.value for e in events],
                "availability_percent": availability
            },
            "next_price_update": (current_time + timedelta(minutes=15)).isoformat(),
            "price_trend": self._calculate_price_trend(business_type, location, current_time)
        })
        
        return pricing_result
    
    def _calculate_price_trend(self, business_type: str, location: Location,
                             current_time: datetime) -> Dict[str, Any]:
        """Calculate expected price trend for next few hours"""
        
        trends = {
            "next_hour": "stable",
            "next_2_hours": "stable", 
            "next_4_hours": "stable",
            "reasoning": []
        }
        
        hour = current_time.hour
        
        if business_type == "movie_theater":
            if hour < 18:
                trends["next_4_hours"] = "increasing"
                trends["reasoning"].append("Approaching prime time (6-10 PM)")
            elif hour >= 20:
                trends["next_2_hours"] = "decreasing"
                trends["reasoning"].append("Past peak hours")
        
        elif business_type == "restaurant":
            if hour < 12:
                trends["next_2_hours"] = "increasing"
                trends["reasoning"].append("Approaching lunch time")
            elif hour < 19:
                trends["next_2_hours"] = "increasing"
                trends["reasoning"].append("Approaching dinner time")
            elif hour >= 21:
                trends["next_hour"] = "decreasing"
                trends["reasoning"].append("Past dinner peak")
        
        return trends
    
    def get_pricing_history(self, business_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get pricing history for analysis (mock implementation)"""
        
        history = []
        current_time = datetime.now()
        
        for i in range(days):
            date = current_time - timedelta(days=i)
            
            # Mock historical pricing data
            history.append({
                "date": date.date().isoformat(),
                "average_price": 150 + (i * 5),  # Mock varying prices
                "peak_price": 200 + (i * 8),
                "lowest_price": 100 + (i * 3),
                "demand_level": "medium",
                "major_events": []
            })
        
        return history
    
    def optimize_pricing_strategy(self, business_type: str, location: Location,
                                target_occupancy: float = 80.0) -> Dict[str, Any]:
        """Suggest optimal pricing strategy to achieve target occupancy"""
        
        current_time = datetime.now()
        current_availability = self.get_availability_estimate(business_type, location, current_time)
        current_occupancy = 100 - current_availability
        
        strategy = {
            "current_occupancy": current_occupancy,
            "target_occupancy": target_occupancy,
            "recommendation": "maintain",
            "price_adjustment": 0.0,
            "reasoning": []
        }
        
        if current_occupancy < target_occupancy - 10:
            strategy["recommendation"] = "decrease_price"
            strategy["price_adjustment"] = -0.15  # 15% decrease
            strategy["reasoning"].append("Low occupancy - reduce prices to attract customers")
        
        elif current_occupancy > target_occupancy + 10:
            strategy["recommendation"] = "increase_price"
            strategy["price_adjustment"] = 0.10  # 10% increase
            strategy["reasoning"].append("High demand - increase prices to optimize revenue")
        
        else:
            strategy["reasoning"].append("Occupancy within target range - maintain current pricing")
        
        return strategy